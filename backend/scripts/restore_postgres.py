"""恢复演练脚本。恢复会覆盖目标库，必须显式确认且建议使用临时数据库。"""

import argparse
import os
import subprocess
from pathlib import Path


def main() -> int:
    parser = argparse.ArgumentParser(description="恢复 PostgreSQL custom-format 备份")
    parser.add_argument("backup", type=Path)
    parser.add_argument("--target-url", default=os.getenv("RESTORE_DATABASE_URL"))
    parser.add_argument("--confirm-dangerous-restore", action="store_true", help="确认会覆盖目标数据库")
    args = parser.parse_args()
    if not args.confirm_dangerous_restore:
        parser.error("恢复是危险操作，请添加 --confirm-dangerous-restore")
    if not args.target_url or not args.target_url.startswith(("postgresql://", "postgresql+psycopg://")):
        parser.error("必须提供 PostgreSQL --target-url 或 RESTORE_DATABASE_URL")
    if not args.backup.is_file():
        parser.error(f"备份文件不存在: {args.backup}")
    restore_url = args.target_url.replace("postgresql+psycopg://", "postgresql://", 1)
    subprocess.run(["pg_restore", "--clean", "--if-exists", "--no-owner", "--dbname", restore_url, str(args.backup)], check=True)
    print(f"restore_completed={args.target_url.split('@')[-1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
