"""只读校验 PostgreSQL custom-format 备份，不连接也不修改目标数据库。"""

import argparse
import subprocess
from pathlib import Path


def verify_backup(path: Path) -> None:
    if not path.is_file():
        raise FileNotFoundError(f"备份文件不存在: {path}")
    subprocess.run(["pg_restore", "--list", "--file", "-", str(path)], check=True)


def main() -> int:
    parser = argparse.ArgumentParser(description="校验 PostgreSQL 备份文件目录")
    parser.add_argument("backup", type=Path)
    args = parser.parse_args()
    try:
        verify_backup(args.backup)
    except FileNotFoundError as exc:
        parser.error(str(exc))
    print(f"backup_verified={args.backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
