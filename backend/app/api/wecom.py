from time import time

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.orm import Session

from app.core.crypto import encrypt_text
from app.core.dependencies import get_current_user
from app.db.session import SessionLocal, get_db
from app.integrations.wecom.callback import (
    DatabaseCallbackProcessor,
    build_mock_signature,
    verify_mock_signature,
)
from app.integrations.wecom.config import WeComConfig
from app.integrations.wecom.message_processor import process_mock_chat_message
from app.integrations.wecom.user_sync import sync_mock_user
from app.models.user import User
from app.schemas.wecom import WeComMockCallback
from app.services.audit_log_service import append_system_audit_log
from app.services.customer_service import get_customer_or_404


SUPPORTED_MOCK_EVENT_TYPES = {"user_auth", "chat_message"}


def _write_callback_audit(event_id: str, event_type: str, result: str) -> None:
    audit_result = {
        "processed": "success",
        "duplicate": "duplicate",
        "retry": "failure",
        "in_progress": "in_progress",
    }[result]
    with SessionLocal() as db:
        append_system_audit_log(
            db,
            "wecom_callback",
            f"wecom.{event_type}.sync",
            "integration_event",
            event_id,
            audit_result,
            {"event_type": event_type, "processor_status": result},
        )
        db.commit()


def _write_callback_security_audit(event_id: str, reason: str) -> None:
    with SessionLocal() as db:
        append_system_audit_log(
            db,
            "wecom_callback",
            "wecom.callback.verify",
            "wecom_callback",
            event_id or "unknown",
            "failure",
            {"reason": reason},
        )
        db.commit()


router = APIRouter(prefix="/wecom", tags=["wecom"])


async def _process_mock_callback(
    payload: WeComMockCallback,
    body: str,
    timestamp: str | None,
    nonce: str | None,
    signature: str | None,
) -> dict[str, str]:
    """Shared signature, idempotency, and message processing pipeline."""

    config = WeComConfig.from_env()
    if config.mode != "mock":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mock callback is disabled")
    if not config.callback_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mock callback token is not configured")
    if not timestamp or not nonce or not signature:
        _write_callback_security_audit(payload.event_id, "missing_signature_headers")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Missing callback signature headers")
    if not verify_mock_signature(config.callback_token, timestamp, nonce, body, signature):
        _write_callback_security_audit(payload.event_id, "invalid_signature")
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid callback signature")

    if payload.event_type not in SUPPORTED_MOCK_EVENT_TYPES:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Unsupported Mock event type")
    if payload.event_type == "user_auth" and not payload.username:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="username is required for user_auth")
    if payload.event_type == "chat_message":
        required = (payload.customer_id, payload.wecom_message_id, payload.direction, payload.message_type)
        if any(value is None for value in required):
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Required chat_message fields are missing")

    try:
        encrypted_payload = encrypt_text(body)
    except RuntimeError as exc:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="APP_ENCRYPTION_KEY is not configured") from exc

    def process_event() -> None:
        if payload.event_type == "user_auth":
            with SessionLocal() as db:
                sync_mock_user(db, payload)
            return
        process_mock_chat_message(payload)

    result = DatabaseCallbackProcessor(SessionLocal).process(
        provider="wecom",
        external_event_id=payload.event_id,
        event_type=payload.event_type,
        payload_encrypted=encrypted_payload,
        handler=process_event,
    )
    _write_callback_audit(payload.event_id, payload.event_type, result)
    if result == "retry":
        raise HTTPException(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, detail="Callback processing failed; retry later")
    return {"event_id": payload.event_id, "status": result}


@router.post("/mock/callback")
async def receive_mock_callback(request: Request, payload: WeComMockCallback = Body(...)):
    """Receive a signed local callback, matching the future external adapter boundary."""

    body = (await request.body()).decode("utf-8")
    return await _process_mock_callback(
        payload,
        body,
        request.headers.get("X-Mock-Timestamp"),
        request.headers.get("X-Mock-Nonce"),
        request.headers.get("X-Mock-Signature"),
    )


@router.post("/mock/emit")
async def emit_mock_callback(
    payload: WeComMockCallback,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Emit a signed local callback without exposing the callback token to the browser."""

    if payload.event_type != "chat_message":
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Local emitter only supports chat_message")
    if payload.customer_id is None:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="customer_id is required")

    # Reuse the normal customer scope check; the local emitter must not bypass permissions.
    get_customer_or_404(db, payload.customer_id, current_user, "update")

    # Keep a stable local WeCom identity for demo users that do not have one yet.
    if current_user.wecom_userid is None:
        current_user.wecom_userid = f"mock-{current_user.username}"
        db.commit()

    effective_payload = payload.model_copy(
        update={"userid": current_user.wecom_userid or f"mock-{current_user.username}"}
    )
    config = WeComConfig.from_env()
    if not config.callback_token:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Mock callback token is not configured")

    timestamp = str(int(time()))
    nonce = f"local-{effective_payload.event_id}"
    body = effective_payload.model_dump_json()
    signature = build_mock_signature(config.callback_token, timestamp, nonce, body)
    return await _process_mock_callback(effective_payload, body, timestamp, nonce, signature)
