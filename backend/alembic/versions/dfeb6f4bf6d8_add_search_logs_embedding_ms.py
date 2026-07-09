"""add search_logs.embedding_ms

Revision ID: dfeb6f4bf6d8
Revises: 4eb382cd1de8
Create Date: 2026-07-08 20:39:47.867291

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'dfeb6f4bf6d8'
down_revision: Union[str, Sequence[str], None] = '4eb382cd1de8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: the ix_embeddings_vector_*_cosine indexes are created via raw SQL in
    # the initial migration (not SQLAlchemy Index objects), so autogenerate always
    # flags them as "removed" here — that's a false positive, left out on purpose.
    op.add_column('search_logs', sa.Column('embedding_ms', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('search_logs', 'embedding_ms')
