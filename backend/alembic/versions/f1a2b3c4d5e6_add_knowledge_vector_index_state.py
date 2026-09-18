"""add knowledge vector index state

Revision ID: f1a2b3c4d5e6
Revises: f0a1b2c3d4e5
"""

from alembic import op
import sqlalchemy as sa


revision = "f1a2b3c4d5e6"
down_revision = "f0a1b2c3d4e5"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("knowledge_documents", sa.Column("vector_index_status", sa.String(length=20), nullable=False, server_default="pending"))
    op.add_column("knowledge_documents", sa.Column("vector_index_error", sa.Text(), nullable=True))
    op.add_column("knowledge_documents", sa.Column("vector_index_attempts", sa.Integer(), nullable=False, server_default="0"))
    op.add_column("knowledge_documents", sa.Column("vector_indexed_at", sa.DateTime(timezone=True), nullable=True))
    op.add_column("knowledge_documents", sa.Column("vector_content_hash", sa.String(length=64), nullable=True))
    op.add_column("knowledge_documents", sa.Column("vector_embedding_model", sa.String(length=100), nullable=True))
    op.create_index("ix_knowledge_documents_vector_index_status", "knowledge_documents", ["vector_index_status"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_knowledge_documents_vector_index_status", table_name="knowledge_documents")
    op.drop_column("knowledge_documents", "vector_embedding_model")
    op.drop_column("knowledge_documents", "vector_content_hash")
    op.drop_column("knowledge_documents", "vector_indexed_at")
    op.drop_column("knowledge_documents", "vector_index_attempts")
    op.drop_column("knowledge_documents", "vector_index_error")
    op.drop_column("knowledge_documents", "vector_index_status")
