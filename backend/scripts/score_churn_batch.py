"""使用已训练模型批量生成并保存客户流失风险。"""

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from app.db.session import SessionLocal
from app.services.churn_risk_service import score_churn_csv_batch


def build_parser() -> argparse.ArgumentParser:
    backend_dir = Path(__file__).resolve().parents[1]
    parser = argparse.ArgumentParser(description="批量生成客户流失风险评分")
    parser.add_argument("--csv", required=True, help="待评分 CSV 的绝对路径")
    parser.add_argument(
        "--model",
        default=str(backend_dir / "data" / "churn_artifacts" / "churn_logistic_baseline.joblib"),
        help="第一阶段生成的可信 joblib 模型路径",
    )
    parser.add_argument("--source-system", default="csv", help="外部学生编号来源命名空间")
    parser.add_argument(
        "--observation-at",
        default=None,
        help="本批数据观察时间，ISO 8601，例如 2026-09-20T00:00:00+00:00",
    )
    parser.add_argument(
        "--medium-threshold",
        type=float,
        default=None,
        help="可选的中风险阈值；默认使用高风险阈值的 60%",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    with SessionLocal() as db:
        from datetime import datetime

        summary = score_churn_csv_batch(
            db,
            csv_path=args.csv,
            model_path=args.model,
            medium_threshold=args.medium_threshold,
            source_system=args.source_system,
            observation_at=(datetime.fromisoformat(args.observation_at) if args.observation_at else None),
        )
    print(json.dumps(asdict(summary), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
