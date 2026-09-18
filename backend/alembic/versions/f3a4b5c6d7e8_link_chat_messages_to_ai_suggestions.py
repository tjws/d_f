"""link outbound chat messages to reviewed AI suggestions"""

from alembic import op
import sqlalchemy as sa


revision = "f3a4b5c6d7e8"
down_revision = "f2a3b4c5d6e7"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.add_column(sa.Column("suggestion_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_chat_messages_suggestion_id",
            "ai_suggestions",
            ["suggestion_id"],
            ["id"],
            ondelete="SET NULL",
        )
        batch_op.create_index("ix_chat_messages_suggestion_id", ["suggestion_id"], unique=False)


def downgrade() -> None:
    with op.batch_alter_table("chat_messages", schema=None) as batch_op:
        batch_op.drop_index("ix_chat_messages_suggestion_id")
        batch_op.drop_constraint("fk_chat_messages_suggestion_id", type_="foreignkey")
        batch_op.drop_column("suggestion_id")
