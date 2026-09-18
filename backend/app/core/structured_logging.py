"""标准库 logging 的 JSON 输出配置，不记录敏感请求正文。"""

import json
import logging
from datetime import datetime, timezone

from app.core.request_context import actor_user_id_var, request_id_var


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        payload = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "event": getattr(record, "event", record.getMessage()),
            "request_id": request_id_var.get(),
            "actor_user_id": actor_user_id_var.get(),
        }
        for field in ("method", "path", "status_code", "duration_ms", "run_id", "customer_id", "provider_name"):
            value = getattr(record, field, None)
            if value is not None:
                payload[field] = value
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def configure_json_logging() -> None:
    handler = logging.StreamHandler()
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)
