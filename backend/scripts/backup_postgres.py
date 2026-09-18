"""生成 PostgreSQL custom-format 备份；不会把环境变量写入备份文件。"""

import argparse
import os
import subprocess
from datetime import datetime, timezone
from pathlib import Path


def create_backup(output: Path) -> Path:
    """创建一份 PostgreSQL custom-format 备份并返回文件路径。"""
    database_url = os.getenv("DATABASE_URL")
    if not database_url or not database_url.startswith(("postgresql://", "postgresql+psycopg://")):
        raise ValueError("请通过 DATABASE_URL 指定 PostgreSQL 连接，拒绝备份 SQLite")
    output.mkdir(parents=True, exist_ok=True)
    filename = output / f"k12_sales_{datetime.now(timezone.utc):%Y%m%dT%H%M%SZ}.dump"
    dump_url = database_url.replace("postgresql+psycopg://", "postgresql://", 1)
    subprocess.run(["pg_dump", "--format=custom", "--no-owner", "--file", str(filename), dump_url], check=True)
    return filename


def main() -> int:
    parser = argparse.ArgumentParser(description="备份 PostgreSQL 数据库")
    parser.add_argument("--output", type=Path, default=Path("backend/backups"))
    args = parser.parse_args()
    try:
        filename = create_backup(args.output)
    except ValueError as exc:
        parser.error(str(exc))
    print(f"backup_created={filename}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
