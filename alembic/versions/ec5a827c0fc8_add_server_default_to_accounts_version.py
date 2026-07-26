"""add server default to accounts.version

Revision ID: ec5a827c0fc8
Revises: b114df939756
Create Date: 2026-07-26 12:10:15.153097

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'ec5a827c0fc8'
down_revision: Union[str, Sequence[str], None] = 'b114df939756'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.alter_column(
        'accounts',
        'version',
        server_default=sa.text('0')
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.alter_column(
        'accounts',
        'version',
        server_default=None
    )
