import csv
import io
import json
from datetime import datetime
from decimal import Decimal

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.dao.admin_data_export_dao import AdminDataExportDAO
from app.models.user import User
from app.services.audit_log_service import append_audit_log
from app.services.data_retention_service import deletion_enabled, get_policy


admin_data_export_dao = AdminDataExportDAO()
DATASETS = ("customers", "chat_messages", "audit_logs", "ai_feedback")


def get_retention_policy() -> dict[str, object]:
    """导出页面的兼容策略摘要；详细预览/清理使用 /admin/data-retention。"""
    detailed = get_policy()
    return {
        "automatic_deletion_enabled": deletion_enabled(),
        "default_export_redacted": True,
        "requires_admin": True,
        "review_before_delete": True,
        "datasets": list(DATASETS),
        "note": "当前只提供管理员脱敏导出；保留策略和清理预览见数据保留管理接口。",
        "retention_days": {item["dataset"]: item["retention_days"] for item in detailed["datasets"]},
    }


def _mask_text(value: str | None) -> str | None:
    if not value:
        return value
    return value[:1] + "*" * max(1, min(len(value) - 1, 8))


def _mask_phone(value: str | None) -> str | None:
    if not value:
        return value
    if len(value) <= 7:
        return "***"
    return f"{value[:3]}****{value[-4:]}"


def _mask_ip(value: str | None) -> str | None:
    if not value:
        return value
    if "." in value:
        parts = value.split(".")
        return ".".join(parts[:-1] + ["***"])
    return "***"


def _serialize(value: object) -> object:
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _sanitize_detail(value: object) -> object:
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if any(token in lowered for token in ("password", "authorization", "jwt", "secret", "api_key", "token", "content_encrypted")):
                result[key] = "[REDACTED]"
            else:
                result[key] = _sanitize_detail(item)
        return result
    if isinstance(value, list):
        return [_sanitize_detail(item) for item in value]
    return _serialize(value)


def _build_rows(db: Session, dataset: str, start: datetime | None, end: datetime | None, limit: int) -> list[dict[str, object]]:
    if dataset == "customers":
        rows = []
        for customer, owner in admin_data_export_dao.list_customers(db, start, end, limit):
            rows.append(
                {
                    "id": customer.id,
                    "name_masked": _mask_text(customer.name),
                    "phone_masked": _mask_phone(customer.phone),
                    "student_name_masked": _mask_text(customer.student_name),
                    "grade": customer.grade,
                    "interested_subject": customer.interested_subject,
                    "stage": customer.stage,
                    "source": customer.source,
                    "owner_username": owner.username if owner else None,
                    "created_at": _serialize(customer.created_at),
                    "updated_at": _serialize(customer.updated_at),
                }
            )
        return rows

    if dataset == "chat_messages":
        rows = []
        for message, customer, user in admin_data_export_dao.list_chat_messages(db, start, end, limit):
            masked_content = message.content_masked or ""
            rows.append(
                {
                    "id": message.id,
                    "customer_id": customer.id,
                    "message_id": message.wecom_message_id,
                    "direction": message.direction,
                    "message_type": message.message_type,
                    "content_preview": masked_content[:80],
                    "content_length": len(masked_content),
                    "user_username": user.username if user else None,
                    "sent_at": _serialize(message.sent_at),
                    "created_at": _serialize(message.created_at),
                }
            )
        return rows

    if dataset == "audit_logs":
        return [
            {
                "id": item.id,
                "actor_user_id": item.actor_user_id,
                "actor_username": item.actor_username_snapshot,
                "actor_role": item.actor_role_snapshot,
                "actor_source": item.actor_source,
                "action": item.action,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "detail": _sanitize_detail(item.detail_json),
                "result": item.result,
                "ip_masked": _mask_ip(item.ip_address),
                "request_id": item.request_id,
                "created_at": _serialize(item.created_at),
            }
            for item in admin_data_export_dao.list_audit_logs(db, start, end, limit)
        ]

    if dataset == "ai_feedback":
        return [
            {
                "id": item.id,
                "suggestion_id": item.suggestion_id,
                "customer_id": item.customer_id,
                "actor_user_id": item.actor_user_id,
                "target_type": item.target_type,
                "target_id": item.target_id,
                "action": item.action,
                "edited_content_present": bool(item.edited_content),
                "note_present": bool(item.note),
                "created_at": _serialize(item.created_at),
            }
            for item in admin_data_export_dao.list_feedback(db, start, end, limit)
        ]

    raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的数据集")


def _render(rows: list[dict[str, object]], output_format: str) -> tuple[bytes, str]:
    if output_format == "json":
        return json.dumps(rows, ensure_ascii=False, indent=2).encode("utf-8"), "application/json; charset=utf-8"
    if output_format != "csv":
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="不支持的导出格式")
    fields = list(rows[0].keys()) if rows else ["empty"]
    buffer = io.StringIO(newline="")
    writer = csv.DictWriter(buffer, fieldnames=fields, extrasaction="ignore")
    writer.writeheader()
    for row in rows:
        writer.writerow({key: json.dumps(value, ensure_ascii=False) if isinstance(value, (dict, list)) else value for key, value in row.items()})
    return buffer.getvalue().encode("utf-8-sig"), "text/csv; charset=utf-8"


def export_dataset(
    db: Session,
    actor: User,
    dataset: str,
    output_format: str,
    start: datetime | None,
    end: datetime | None,
    limit: int,
) -> tuple[bytes, str, str]:
    if start is not None and end is not None and start > end:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="start 不能晚于 end")
    rows = _build_rows(db, dataset, start, end, limit)
    content, media_type = _render(rows, output_format)
    append_audit_log(
        db,
        actor,
        "admin.data_exported",
        "data_export",
        dataset,
        {
            "format": output_format,
            "start": start.isoformat() if start else None,
            "end": end.isoformat() if end else None,
            "limit": limit,
            "row_count": len(rows),
            "redacted": True,
        },
    )
    db.commit()
    return content, media_type, f"k12-{dataset}-export.{output_format}"
