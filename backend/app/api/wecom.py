from fastapi import APIRouter, Body, HTTPException, Request, status

from app.core.crypto import encrypt_text
from app.db.session import SessionLocal
from app.integrations.wecom.callback import (
    DatabaseCallbackProcessor,
    verify_mock_signature,
)
from app.integrations.wecom.config import WeComConfig
from app.integrations.wecom.message_processor import process_mock_chat_message
from app.integrations.wecom.user_sync import sync_mock_user
from app.schemas.wecom import WeComMockCallback
from app.services.audit_log_service import append_system_audit_log


SUPPORTED_MOCK_EVENT_TYPES = {"user_auth", "chat_message"}


def _write_callback_audit(
    event_id: str,
    event_type: str,
    result: str,
) -> None:
    """记录回调处理结果，不保存密钥或完整请求明文。"""

    audit_result = {
        "processed": "success",
        "duplicate": "duplicate",
        "retry": "failure",
        "in_progress": "in_progress",
    }[result]

    with SessionLocal() as db:
        append_system_audit_log(db, "wecom_callback", f"wecom.{event_type}.sync", "integration_event", event_id, audit_result, {"event_type": event_type, "processor_status": result})
        db.commit()


def _write_callback_security_audit(
    event_id: str,
    reason: str,
) -> None:
    """记录验签拒绝原因，不保存签名值或密钥。"""

    with SessionLocal() as db:
        append_system_audit_log(db, "wecom_callback", "wecom.callback.verify", "wecom_callback", event_id or "unknown", "failure", {"reason": reason})
        db.commit()


router = APIRouter(
    prefix="/wecom",
    tags=["wecom"],
)


@router.post("/mock/callback")
async def receive_mock_callback(
    request: Request,
    payload: WeComMockCallback = Body(...),
):
    """接收本地 Mock 企业微信回调并进入持久化幂等处理。"""

    config = WeComConfig.from_env()

    if config.mode != "mock":
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mock 回调未启用",
        )

    if not config.callback_token:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 Mock 回调密钥",
        )

    timestamp = request.headers.get("X-Mock-Timestamp")
    nonce = request.headers.get("X-Mock-Nonce")
    signature = request.headers.get("X-Mock-Signature")

    if not timestamp or not nonce or not signature:
        _write_callback_security_audit(
            event_id=payload.event_id,
            reason="missing_signature_headers",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="缺少回调签名请求头",
        )

    # 必须使用原始请求体验签，避免 JSON 重排导致签名不一致。
    body = (await request.body()).decode("utf-8")

    if not verify_mock_signature(
        config.callback_token,
        timestamp,
        nonce,
        body,
        signature,
    ):
        _write_callback_security_audit(
            event_id=payload.event_id,
            reason="invalid_signature",
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="回调签名无效",
        )

    if payload.event_type not in SUPPORTED_MOCK_EVENT_TYPES:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="不支持的 Mock 回调事件类型",
        )

    if payload.event_type == "user_auth" and not payload.username:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="user_auth 回调缺少 username",
        )

    if payload.event_type == "chat_message":
        chat_fields = (
            payload.customer_id,
            payload.wecom_message_id,
            payload.direction,
            payload.message_type,
        )
        if any(value is None for value in chat_fields):
            raise HTTPException(
                status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
                detail="chat_message 回调缺少必要字段",
            )

    try:
        encrypted_payload = encrypt_text(body)
    except RuntimeError as exc:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="未配置 APP_ENCRYPTION_KEY，无法保存回调原文",
        ) from exc

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

    _write_callback_audit(
        event_id=payload.event_id,
        event_type=payload.event_type,
        result=result,
    )

    if result == "retry":
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="回调处理失败，请稍后重试",
        )

    return {
        "event_id": payload.event_id,
        "status": result,
    }
