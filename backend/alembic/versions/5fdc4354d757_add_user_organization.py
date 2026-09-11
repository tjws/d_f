"""add user organization

Revision ID: 5fdc4354d757
Revises: e4c7a1b2d9f0
Create Date: 2026-09-11 17:27:55.965794

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '5fdc4354d757'
down_revision: Union[str, None] = 'e4c7a1b2d9f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """给现有用户增加可为空的组织归属。"""

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.add_column(sa.Column('organization_id', sa.Integer(), nullable=True))
        batch_op.create_index(batch_op.f('ix_users_organization_id'), ['organization_id'], unique=False)
        batch_op.create_foreign_key(
            'fk_users_organization_id_organizations',
            'organizations',
            ['organization_id'],
            ['id'],
            ondelete='SET NULL',
        )



def downgrade() -> None:
    """移除用户的组织归属字段。"""

    with op.batch_alter_table('users', schema=None) as batch_op:
        batch_op.drop_constraint(
            'fk_users_organization_id_organizations',
            type_='foreignkey',
        )
        batch_op.drop_index(batch_op.f('ix_users_organization_id'))
        batch_op.drop_column('organization_id')
