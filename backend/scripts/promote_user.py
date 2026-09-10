import argparse

from sqlalchemy import select

from app.db.session import SessionLocal
from app.models.user import User


VALID_ROLES = {"sales", "manager", "admin"}


def main():
    """修改指定用户的角色。"""

    parser = argparse.ArgumentParser(
        description="提升或修改用户角色",
    )

    parser.add_argument(
        "username",
        help="要修改角色的用户名",
    )

    parser.add_argument(
        "role",
        choices=sorted(VALID_ROLES),
        help="目标角色",
    )

    args = parser.parse_args()

    with SessionLocal() as db:
        user = db.scalar(
            select(User).where(User.username == args.username)
        )

        if user is None:
            raise SystemExit(
                f"找不到用户：{args.username}"
            )

        user.role = args.role
        db.commit()

        print(
            f"用户 {user.username} 的角色已设置为 {user.role}"
        )


if __name__ == "__main__":
    main()