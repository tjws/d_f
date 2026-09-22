"""从命令行训练客户流失 Logistic Regression 基线模型。"""

import argparse
import json
from pathlib import Path

from app.churn.artifacts import save_training_artifacts
from app.churn.dataset import load_churn_csv, load_temporal_churn_csv
from app.churn.training import train_logistic_baseline, train_temporal_logistic_baseline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="训练客户流失 Logistic Regression 基线")
    parser.add_argument("--csv", required=True, help="训练 CSV 的绝对路径")
    parser.add_argument(
        "--output-dir",
        default=str(Path(__file__).resolve().parents[1] / "data" / "churn_artifacts"),
        help="模型与评测报告输出目录",
    )
    parser.add_argument(
        "--target-recall",
        type=float,
        default=0.8,
        help="在验证集上希望达到的最低召回率，默认 0.8",
    )
    parser.add_argument("--random-state", type=int, default=42, help="可复现实验的随机种子")
    parser.add_argument(
        "--temporal",
        action="store_true",
        help="启用 observed_at/label_window_end 时间切分契约",
    )
    parser.add_argument(
        "--horizon-days",
        type=int,
        default=30,
        help="时间型数据的未来标签窗口，默认 30 天",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.temporal:
        frame, quality = load_temporal_churn_csv(
            args.csv, label_horizon_days=args.horizon_days
        )
        result = train_temporal_logistic_baseline(
            frame,
            target_recall=args.target_recall,
            random_state=args.random_state,
        )
    else:
        frame, quality = load_churn_csv(args.csv)
        result = train_logistic_baseline(
            frame,
            target_recall=args.target_recall,
            random_state=args.random_state,
        )
    saved = save_training_artifacts(result, quality, args.output_dir)

    summary = {
        "rows": quality.row_count,
        "churn_rate": quality.churn_rate,
        "threshold": result.threshold,
        "test_metrics": result.report["test"],
        "model_path": str(saved.model_path),
        "report_path": str(saved.report_path),
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
