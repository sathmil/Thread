"""add jobs.warning_message

Revision ID: 137b1c28ff9d
Revises: 27fd6f3b4e51
Create Date: 2026-07-09 14:21:17.635317

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '137b1c28ff9d'
down_revision: Union[str, Sequence[str], None] = '27fd6f3b4e51'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    # Note: the ix_embeddings_vector_*_cosine indexes are raw SQL (see the
    # initial migration), so autogenerate always flags them as "removed"
    # here — a false positive, left out on purpose.
    op.add_column('jobs', sa.Column('warning_message', sa.Text(), nullable=True))


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_column('jobs', 'warning_message')
