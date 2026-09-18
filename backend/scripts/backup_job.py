"""供 Task Scheduler 或容器定时执行的备份+只读校验任务。"""

import argparse
import os
from pathlib import Path

from scripts.backup_postgres import create_backup
from scripts.verify_backup import verify_backup


def run_job(output: Path, prune_days: int | None = None, confirm_prune: bool = False) -> Path:
    backup = create_backup(output)
    verify_backup(backup)
    if prune_days is not None:
        if not confirm_prune or os.getenv("BACKUP_PRUNE_ENABLED", "0").strip() != "1":
            raise ValueError("清理旧备份需要 --confirm-prune 且 BACKUP_PRUNE_ENABLED=1")
        cutoff = backup.stat().st_mtime - prune_days * 86400
        for candidate in output.glob("*.dump"):
            if candidate != backup and candidate.stat().st_mtime < cutoff:
                candidate.unlink()
    return backup


def main() -> int:
    parser = argparse.ArgumentParser(description="创建并校验 PostgreSQL 备份")
    parser.add_argument("--output", type=Path, default=Path(os.getenv("BACKUP_DIRECTORY", "backend/backups")))
    parser.add_argument("--prune-days", type=int, default=None)
    parser.add_argument("--confirm-prune", action="store_true")
    args = parser.parse_args()
    if args.prune_days is not None and args.prune_days < 1:
        parser.error("--prune-days 必须大于 0")
    try:
        backup = run_job(args.output, args.prune_days, args.confirm_prune)
    except (ValueError, FileNotFoundError) as exc:
        parser.error(str(exc))
    print(f"backup_job_verified={backup}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
