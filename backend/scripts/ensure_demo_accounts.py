"""检查并整理本地演示账号。

默认只读取数据库并输出差异；只有同时提供 ``--apply`` 和
``--reset-passwords`` 时，才会重置已有演示账号的密码。
"""

from __future__ import annotations

import argparse
import os
from dataclasses import dataclass

from sqlalchemy import select

from app.core.security import hash_password
from app.db.session import SessionLocal
from app.models.user import User


DEMO_PASSWORD = os.getenv("DEMO_PASSWORD", "Demo123456!")


@dataclass(frozen=True)
class DemoAccount:
    username: str
    role: str
    full_name: str


DEMO_ACCOUNTS = (
    DemoAccount("demo_admin", "admin", "演示管理员"),
    DemoAccount("demo_manager", "manager", "演示经理"),
    DemoAccount("demo_sales", "sales", "演示销售"),
)


def ensure_demo_accounts(*, apply: bool, reset_passwords: bool) -> dict[str, int]:
    """创建缺失账号，并按显式选项重置演示密码。"""

    if reset_passwords and not apply:
        raise ValueError("--reset-passwords 必须与 --apply 一起使用")

    counters = {"created": 0, "reset": 0, "unchanged": 0, "missing": 0, "role_mismatch": 0}
    with SessionLocal() as db:
        for spec in DEMO_ACCOUNTS:
            user = db.scalar(select(User).where(User.username == spec.username))
            if user is None:
                counters["missing"] += 1
                if apply:
                    db.add(
                        User(
                            username=spec.username,
                            full_name=spec.full_name,
                            role=spec.role,
                            hashed_password=hash_password(DEMO_PASSWORD),
                            wecom_userid=f"mock-{spec.username}",
                        )
                    )
                    counters["created"] += 1
                continue

            if user.role != spec.role:
                counters["role_mismatch"] += 1
            if reset_passwords:
                user.hashed_password = hash_password(DEMO_PASSWORD)
                counters["reset"] += 1
            else:
                counters["unchanged"] += 1

        if apply:
            db.commit()

    return counters


def main() -> int:
    parser = argparse.ArgumentParser(description="检查并整理本地演示账号")
    parser.add_argument("--apply", action="store_true", help="确认写入缺失账号或密码变更")
    parser.add_argument(
        "--reset-passwords",
        action="store_true",
        help="显式重置已有演示账号密码为 DEMO_PASSWORD",
    )
    args = parser.parse_args()

    try:
        result = ensure_demo_accounts(apply=args.apply, reset_passwords=args.reset_passwords)
    except ValueError as exc:
        parser.error(str(exc))

    mode = "applied" if args.apply else "preview"
    print(
        f"demo_accounts_{mode}: created={result['created']} reset={result['reset']} "
        f"missing={result['missing']} unchanged={result['unchanged']} "
        f"role_mismatch={result['role_mismatch']}"
    )
    if not args.apply and result["missing"]:
        print("如需创建缺失账号，请明确执行 --apply；不要在生产环境运行此脚本。")
    if not args.reset_passwords and result["role_mismatch"]:
        print("检测到角色不一致；脚本不会自动覆盖已有角色，请人工核对。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
