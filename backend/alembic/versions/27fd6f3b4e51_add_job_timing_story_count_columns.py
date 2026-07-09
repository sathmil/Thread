"""add job timing/story-count columns

Revision ID: 27fd6f3b4e51
Revises: dfeb6f4bf6d8
Create Date: 2026-07-09 08:19:19.684669

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '27fd6f3b4e51'
down_revision: Union[str, Sequence[str], None] = 'dfeb6f4bf6d8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: the ix_embeddings_vector_*_cosine indexes are raw SQL (see the
    # initial migration), so autogenerate always flags them as "removed"
    # here — a false positive, left out on purpose.
    op.add_column('jobs', sa.Column('story_count', sa.Integer(), nullable=True))
    op.add_column('jobs', sa.Column('duration_ms', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('embedding_ms', sa.Float(), nullable=True))
    op.add_column('jobs', sa.Column('avg_embedding_ms_per_story', sa.Float(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'avg_embedding_ms_per_story')
    op.drop_column('jobs', 'embedding_ms')
    op.drop_column('jobs', 'duration_ms')
    op.drop_column('jobs', 'story_count')
