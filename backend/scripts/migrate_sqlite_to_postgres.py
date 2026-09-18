"""一次性把本地 SQLite 数据复制到已迁移好的 PostgreSQL。

默认只展示各表行数。必须显式传入 --execute 才会写入目标库；
源 SQLite 文件始终只读，目标库非空时会拒绝运行，避免覆盖数据。
"""

import argparse
import os
from pathlib import Path

from sqlalchemy import create_engine, func, insert, select, text

from app.db.base import Base
from app.models.ai_suggestion import AISuggestion  # noqa: F401
from app.models.ai_workflow_run import AIWorkflowRun  # noqa: F401
from app.models.audit_log import AuditLog  # noqa: F401
from app.models.chat_message import ChatMessage  # noqa: F401
from app.models.customer import Customer  # noqa: F401
from app.models.customer_profile import CustomerProfile  # noqa: F401
from app.models.customer_tag import CustomerTag  # noqa: F401
from app.models.integration_event import IntegrationEvent  # noqa: F401
from app.models.organization import Organization  # noqa: F401
from app.models.role_permission import RolePermission  # noqa: F401
from app.models.schedule import Schedule  # noqa: F401
from app.models.student import Student  # noqa: F401
from app.models.tag import Tag  # noqa: F401
from app.models.timeline_event import TimelineEvent  # noqa: F401
from app.models.user import User  # noqa: F401


BACKEND_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_URL = f"sqlite:///{(BACKEND_DIR / 'data' / 'app.db').as_posix()}"
# 这些记录由 Alembic 固定初始化；源/目标数量一致时保留目标版本，不重复插入。
PREPOPULATED_TABLES = {"role_permissions"}


def _count_rows(connection, table) -> int:
    return int(connection.scalar(select(func.count()).select_from(table)) or 0)


def main() -> None:
    parser = argparse.ArgumentParser(description="迁移 SQLite 学习数据到空 PostgreSQL 数据库")
    parser.add_argument("--execute", action="store_true", help="确认后才真正写入 PostgreSQL")
    parser.add_argument("--source-url", default=DEFAULT_SOURCE_URL)
    args = parser.parse_args()

    target_url = os.getenv("POSTGRES_DATABASE_URL")
    if not target_url or not target_url.startswith("postgresql"):
        raise SystemExit("请通过 POSTGRES_DATABASE_URL 提供 PostgreSQL 连接地址")

    source_engine = create_engine(args.source_url)
    target_engine = create_engine(target_url, pool_pre_ping=True)
    with source_engine.connect() as source, target_engine.begin() as target:
        source_tables = set(source.dialect.get_table_names(source))
        for table in Base.metadata.sorted_tables:
            if table.name not in source_tables:
                print(f"{table.name}: SQLite 中不存在，跳过")
                continue
            source_count = _count_rows(source, table)
            target_count = _count_rows(target, table)
            print(f"{table.name}: source={source_count}, target={target_count}")
            if table.name in PREPOPULATED_TABLES and target_count == source_count:
                print(f"{table.name}: 已由迁移初始化，跳过复制")
                continue
            if target_count:
                raise SystemExit("目标 PostgreSQL 不是空库，已停止，未写入任何数据")
            if not args.execute or source_count == 0:
                continue
            rows = source.execute(select(table)).mappings().all()
            target.execute(insert(table), [dict(row) for row in rows])
            if "id" in table.c:
                maximum_id = target.scalar(select(func.max(table.c.id)))
                if maximum_id is not None:
                    # 手工保留主键后同步 PostgreSQL 序列，避免下一次新增记录发生主键冲突。
                    target.execute(
                        text("SELECT setval(pg_get_serial_sequence(:table_name, 'id'), :value, true)"),
                        {"table_name": table.name, "value": maximum_id},
                    )

    print("迁移完成" if args.execute else "仅预检完成；加入 --execute 才会写入 PostgreSQL")


if __name__ == "__main__":
    main()
