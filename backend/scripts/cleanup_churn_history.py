"""预览或清理过期流失评分批次；默认绝不删除。"""

import argparse
from datetime import datetime, timedelta, timezone

from sqlalchemy import func, select

from app.dao.churn_risk_dao import ChurnRiskDAO
from app.db.session import SessionLocal
from app.models.churn_scoring_batch import ChurnScoringBatch


def main() -> None:
    parser = argparse.ArgumentParser(description="清理过期流失评分历史")
    parser.add_argument("--older-than-days", type=int, default=730)
    parser.add_argument(
        "--apply",
        action="store_true",
        help="显式确认删除；省略时只显示预计删除数量",
    )
    args = parser.parse_args()
    if args.older_than_days < 30:
        raise SystemExit("保留期不能少于 30 天")
    cutoff = datetime.now(timezone.utc) - timedelta(days=args.older_than_days)
    with SessionLocal() as db:
        count = int(
            db.scalar(
                select(func.count(ChurnScoringBatch.id)).where(
                    ChurnScoringBatch.created_at < cutoff
                )
            )
            or 0
        )
        print(f"cutoff={cutoff.isoformat()} batches={count} apply={args.apply}")
        if args.apply and count:
            ChurnRiskDAO().delete_batches_before(db, cutoff)
            db.commit()


if __name__ == "__main__":
    main()
