"""${message}

Revision ID: 0001
"""
from alembic import op
import sqlalchemy as sa

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    pass  # create_all on startup for v1


def downgrade():
    pass
