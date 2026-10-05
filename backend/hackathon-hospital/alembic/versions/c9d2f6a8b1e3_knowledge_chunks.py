"""knowledge chunks for RAG

Revision ID: c9d2f6a8b1e3
Revises: b8c1e5f7a9d0
Create Date: 2026-10-05 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'c9d2f6a8b1e3'
down_revision: Union[str, Sequence[str], None] = 'b8c1e5f7a9d0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

EMBEDDING_DIM = 1536


def upgrade() -> None:
    """Upgrade schema."""
    is_postgres = op.get_bind().dialect.name == "postgresql"
    if is_postgres:
        from pgvector.sqlalchemy import Vector
        op.execute("CREATE EXTENSION IF NOT EXISTS vector")
        embedding_type = Vector(EMBEDDING_DIM)
    else:
        embedding_type = sa.JSON()

    op.create_table(
        'knowledge_chunks',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('doc_slug', sa.String(length=100), nullable=False),
        sa.Column('doc_title', sa.String(length=255), nullable=False),
        sa.Column('chunk_key', sa.String(length=300), nullable=False),
        sa.Column('section', sa.String(length=255), nullable=False),
        sa.Column('content', sa.Text(), nullable=False),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('embedding', embedding_type, nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('doc_slug', 'chunk_key', name='uq_knowledge_chunk'),
    )
    op.create_index(op.f('ix_knowledge_chunks_doc_slug'), 'knowledge_chunks', ['doc_slug'], unique=False)
    if is_postgres:
        # Approximate nearest-neighbour index for cosine similarity.
        op.execute("CREATE INDEX ix_knowledge_chunks_embedding ON knowledge_chunks USING hnsw (embedding vector_cosine_ops)")


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f('ix_knowledge_chunks_doc_slug'), table_name='knowledge_chunks')
    op.drop_table('knowledge_chunks')
