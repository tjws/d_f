"""只读检查运行依赖与 AI 配置，不调用外部模型。"""

from datetime import datetime, timezone
import os
import json
from collections.abc import Callable
from typing import Any
from pathlib import Path

import redis
from qdrant_client import QdrantClient
from sqlalchemy import text
from sqlalchemy.engine import Engine

from app.db.session import engine as default_engine
from app.knowledge.qdrant_store import get_qdrant_client as default_qdrant_factory
from app.workers.broker import broker as worker_broker


def check_runtime_dependencies(
    *,
    database_engine: Engine | None = None,
    redis_from_url: Callable[..., Any] | None = None,
    qdrant_factory: Callable[[], QdrantClient] | None = None,
) -> dict[str, str]:
    """检查依赖状态；依赖工厂可注入，便于 API 和单元测试复用。"""

    checks: dict[str, str] = {}
    try:
        with (database_engine or default_engine).connect() as connection:
            connection.execute(text("SELECT 1"))
        checks["database"] = "ok"
    except Exception:
        checks["database"] = "error"

    try:
        factory = redis_from_url or redis.Redis.from_url
        client = factory(
            os.getenv("REDIS_URL", "redis://localhost:6380/0"),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        client.ping()
        client.close()
        checks["redis"] = "ok"
    except Exception:
        checks["redis"] = "error"

    if os.getenv("RAG_VECTOR_ENABLED", "0").strip() == "1":
        try:
            (qdrant_factory or default_qdrant_factory)().get_collections()
            checks["qdrant"] = "ok"
        except Exception:
            checks["qdrant"] = "error"
    else:
        checks["qdrant"] = "disabled"

    return checks


def _provider_name(setting: str, default: str) -> str:
    return os.getenv(setting, os.getenv("AI_PROVIDER", default)).strip().lower() or default


def get_ai_provider_status() -> dict[str, object]:
    """返回非敏感配置摘要；绝不返回 API Key 本身，也不触发模型调用。"""

    default_provider = _provider_name("AI_PROVIDER", "bailian")
    workflow_providers = {
        "reply": _provider_name("AI_REPLY_PROVIDER", default_provider),
        "profile": _provider_name("AI_PROFILE_PROVIDER", default_provider),
        "tag": _provider_name("AI_TAG_PROVIDER", default_provider),
        "schedule": _provider_name("AI_SCHEDULE_PROVIDER", default_provider),
    }
    return {
        "default_provider": default_provider,
        "workflow_providers": workflow_providers,
        "embedding_provider": os.getenv("RAG_EMBEDDING_PROVIDER", "bailian").strip().lower() or "bailian",
        "embedding_model": os.getenv("BAILIAN_EMBEDDING_MODEL", "text-embedding-v4").strip() or "text-embedding-v4",
        "bailian_api_key_configured": bool(os.getenv("DASHSCOPE_API_KEY", "").strip()),
    }


def get_worker_status() -> dict[str, object]:
    """读取 Worker 短期心跳和队列长度，不读取或修改业务数据。"""

    required = any(
        os.getenv(name, default).strip().lower() == "queue"
        for name, default in (
            ("AI_WORKFLOW_EXECUTION_MODE", "sync"),
            ("KNOWLEDGE_INDEX_EXECUTION_MODE", "manual"),
        )
    )
    if not required:
        return {
            "required": False,
            "status": "disabled",
            "worker_id": None,
            "last_seen_at": None,
            "queue_depths": {},
        }

    client = None
    try:
        client = redis.Redis.from_url(
            os.getenv("REDIS_URL", "redis://localhost:6380/0"),
            socket_connect_timeout=1,
            socket_timeout=1,
        )
        raw = client.get(os.getenv("WORKER_HEARTBEAT_KEY", "k12_sales_assistant:worker:heartbeat"))
        queue_depths = {
            queue_name: int(worker_broker.do_qsize(queue_name))
            for queue_name in ("ai_workflow", "knowledge_index")
        }
        if not raw:
            return {
                "required": True,
                "status": "offline",
                "worker_id": None,
                "last_seen_at": None,
                "queue_depths": queue_depths,
            }
        payload = json.loads(raw.decode() if isinstance(raw, bytes) else raw)
        return {
            "required": True,
            "status": "online",
            "worker_id": payload.get("worker_id"),
            "last_seen_at": payload.get("updated_at"),
            "queue_depths": queue_depths,
        }
    except Exception:
        return {
            "required": True,
            "status": "error",
            "worker_id": None,
            "last_seen_at": None,
            "queue_depths": {},
        }
    finally:
        if client is not None:
            client.close()


def get_backup_status() -> dict[str, object]:
    """只读取备份文件元数据，不执行 pg_dump/pg_restore。"""

    raw_directory = os.getenv("BACKUP_DIRECTORY", "").strip()
    directory = Path(raw_directory) if raw_directory else Path(__file__).resolve().parents[2] / "backups"
    try:
        max_age_hours = max(1, int(os.getenv("BACKUP_MAX_AGE_HOURS", "24") or "24"))
    except ValueError:
        max_age_hours = 24
    prune_enabled = os.getenv("BACKUP_PRUNE_ENABLED", "0").strip() == "1"
    configured = bool(raw_directory) or directory.exists()
    if not configured:
        return {
            "configured": False,
            "directory": str(directory),
            "latest_backup_at": None,
            "latest_backup_name": None,
            "latest_size_bytes": None,
            "age_seconds": None,
            "status": "disabled",
            "max_age_hours": max_age_hours,
            "automatic_prune_enabled": prune_enabled,
        }
    backups = sorted(directory.glob("*.dump"), key=lambda path: path.stat().st_mtime, reverse=True) if directory.is_dir() else []
    if not backups:
        return {
            "configured": True,
            "directory": str(directory),
            "latest_backup_at": None,
            "latest_backup_name": None,
            "latest_size_bytes": None,
            "age_seconds": None,
            "status": "missing",
            "max_age_hours": max_age_hours,
            "automatic_prune_enabled": prune_enabled,
        }
    latest = backups[0]
    latest_at = datetime.fromtimestamp(latest.stat().st_mtime, tz=timezone.utc)
    age_seconds = max(0, int((datetime.now(timezone.utc) - latest_at).total_seconds()))
    return {
        "configured": True,
        "directory": str(directory),
        "latest_backup_at": latest_at,
        "latest_backup_name": latest.name,
        "latest_size_bytes": latest.stat().st_size,
        "age_seconds": age_seconds,
        "status": "ok" if age_seconds <= max_age_hours * 3600 else "stale",
        "max_age_hours": max_age_hours,
        "automatic_prune_enabled": prune_enabled,
    }


def get_system_status() -> dict[str, object]:
    dependencies = check_runtime_dependencies()
    worker = get_worker_status()
    return {
        "checked_at": datetime.now(timezone.utc),
        "ready": all(value in {"ok", "disabled"} for value in dependencies.values()),
        "dependencies": {name: {"status": status} for name, status in dependencies.items()},
        "ai": get_ai_provider_status(),
        "worker": worker,
        "backup": get_backup_status(),
    }
