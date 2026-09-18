"""命令行运行 RAG 固定问题集评测。"""

from __future__ import annotations

import argparse
import json

from app.db.session import SessionLocal
from app.knowledge.evaluation import evaluate_knowledge


def main() -> None:
    parser = argparse.ArgumentParser(description="评测关键词与 Qdrant RAG 召回")
    parser.add_argument("--limit", type=int, default=3, help="每个问题返回的候选数量，范围 1-5")
    args = parser.parse_args()
    with SessionLocal() as db:
        print(json.dumps(evaluate_knowledge(db=db, limit=args.limit), ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
