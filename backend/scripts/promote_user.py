import argparse

from sqlalchemy import func, select
from sqlalchemy.exc import SQLAlchemyError

from app.db.session import SessionLocal
from app.models.audit_log import AuditLog
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

    parser.add_argument(
        "--operator",
        help="执行操作的管理员用户名；初始化时使用 --bootstrap",
    )

    parser.add_argument(
        "--bootstrap",
        action="store_true",
        help="初始化第一个管理员，只能在系统没有管理员时使用",
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

        active_admin_count = db.scalar(
            select(func.count(User.id)).where(
                User.role == "admin",
                User.is_active.is_(True),
            )
        ) or 0

        if args.bootstrap:
            actor_user_id = None
            actor_username_snapshot = None
            actor_role_snapshot = None
            actor_source = "maintenance_script_bootstrap"

            if args.operator is not None:
                raise SystemExit(
                    "--bootstrap 不能同时使用 --operator"
                )

            if args.role != "admin":
                raise SystemExit(
                    "--bootstrap 只能用于设置 admin 角色"
                )

            if active_admin_count > 0:
                raise SystemExit(
                    "系统已有管理员，不能使用 --bootstrap"
                )
        else:
            if args.operator is None:
                raise SystemExit(
                    "普通角色修改必须提供 --operator"
                )

            operator_user = db.scalar(
                select(User).where(
                    User.username == args.operator
                )
            )

            if (
                operator_user is None
                or not operator_user.is_active
                or operator_user.role != "admin"
            ):
                raise SystemExit(
                    "--operator 必须是启用中的管理员"
                )

            if (
                operator_user.id == user.id
                and args.role != "admin"
            ):
                raise SystemExit(
                    "操作者不能通过脚本降低自己的管理员权限"
                )

            actor_user_id = operator_user.id
            actor_username_snapshot = operator_user.username
            actor_role_snapshot = operator_user.role
            actor_source = "maintenance_script"

        # 防止维护脚本把系统最后一个有效管理员降级。
        if user.role == "admin" and args.role != "admin":
            if active_admin_count <= 1:
                raise SystemExit(
                    "不能降级系统最后一个有效管理员"
                )

        old_role = user.role
        new_role = args.role

        # 角色没有变化时，不产生无意义的审计记录。
        if old_role == new_role:
            print(
                f"用户 {user.username} 已经是 {new_role} 角色"
            )
            return

        user.role = new_role

        db.add(
            AuditLog(
                actor_user_id=actor_user_id,
                actor_username_snapshot=actor_username_snapshot,
                actor_role_snapshot=actor_role_snapshot,
                actor_source=actor_source,
                action="user.role_changed",
                target_type="user",
                target_id=str(user.id),
                detail_json={
                    "before": {"role": old_role},
                    "after": {"role": new_role},
                },
                result="success",
            )
        )

        try:
            # 角色和审计记录只进行一次提交。
            db.commit()
        except SQLAlchemyError:
            db.rollback()
            raise

        print(
            f"用户 {user.username} 的角色已设置为 {user.role}"
        )


if __name__ == "__main__":
    main()
