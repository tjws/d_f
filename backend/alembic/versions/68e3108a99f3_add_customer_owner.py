"""add customer owner

Revision ID: 68e3108a99f3
Revises: 716b42e36a93
Create Date: 2026-09-10 21:35:25.972412

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '68e3108a99f3'
down_revision: Union[str, None] = '716b42e36a93'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """使用 SQLite batch 模式增加客户负责人字段和外键。"""

    bind = op.get_bind()
    if bind.dialect.name != "sqlite":
        # PostgreSQL 支持原生 ALTER TABLE；不要使用 recreate="always"，
        # 否则会把 customers 的主键序列重命名为 Alembic 临时名称。
        op.add_column("customers", sa.Column("owner_id", sa.Integer(), nullable=True))
        op.create_index("ix_customers_owner_id", "customers", ["owner_id"], unique=False)
        op.create_foreign_key(
            "fk_customers_owner_id_users",
            "customers",
            "users",
            ["owner_id"],
            ["id"],
        )
        return

    inspector = sa.inspect(bind)

    columns = {
        column["name"]
        for column in inspector.get_columns("customers")
    }

    indexes = {
        index["name"]
        for index in inspector.get_indexes("customers")
    }

    foreign_keys = {
        foreign_key.get("name")
        for foreign_key in inspector.get_foreign_keys("customers")
    }

    with op.batch_alter_table(
        "customers",
        recreate="always",
    ) as batch_op:
        if "owner_id" not in columns:
            batch_op.add_column(
                sa.Column(
                    "owner_id",
                    sa.Integer(),
                    nullable=True,
                )
            )

        if "ix_customers_owner_id" not in indexes:
            batch_op.create_index(
                "ix_customers_owner_id",
                ["owner_id"],
                unique=False,
            )

        if "fk_customers_owner_id_users" not in foreign_keys:
            batch_op.create_foreign_key(
                "fk_customers_owner_id_users",
                "users",
                ["owner_id"],
                ["id"],
            )


def downgrade() -> None:
    """回退客户负责人字段。"""

    if op.get_bind().dialect.name != "sqlite":
        op.drop_constraint("fk_customers_owner_id_users", "customers", type_="foreignkey")
        op.drop_index("ix_customers_owner_id", table_name="customers")
        op.drop_column("customers", "owner_id")
        return

    with op.batch_alter_table(
        "customers",
        recreate="always",
    ) as batch_op:
        batch_op.drop_constraint(
            "fk_customers_owner_id_users",
            type_="foreignkey",
        )
        batch_op.drop_index("ix_customers_owner_id")
        batch_op.drop_column("owner_id")
