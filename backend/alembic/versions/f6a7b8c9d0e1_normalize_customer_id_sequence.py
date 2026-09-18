"""normalize customer id sequence

Revision ID: f6a7b8c9d0e1
Revises: e5f6a7b8c9d0
Create Date: 2026-09-15
"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op


revision: str = "f6a7b8c9d0e1"
down_revision: Union[str, Sequence[str], None] = "e5f6a7b8c9d0"
branch_labels = None
depends_on = None


def upgrade() -> None:
    """只规范 PostgreSQL 中历史 batch migration 留下的序列名。"""

    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return

    current = bind.scalar(sa.text("SELECT pg_get_serial_sequence('customers', 'id')"))
    if current == "public._alembic_tmp_customers_id_seq":
        op.execute(sa.text("ALTER SEQUENCE _alembic_tmp_customers_id_seq RENAME TO customers_id_seq"))


def downgrade() -> None:
    # 序列名称不影响业务数据；回退不再改回难以理解的历史临时名称。
    pass
