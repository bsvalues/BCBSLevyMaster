"""Initial migration

Revision ID: 1a2b3c4d5e6f
Revises: 
Create Date: 2025-04-01 17:35:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '1a2b3c4d5e6f'
down_revision = None
branch_labels = None
depends_on = None


def upgrade():
    # This is a placeholder for the initial migration.
    # Since the tables are already created, we won't recreate them.
    pass


def downgrade():
    # No need to implement downgrade for initial migration
    pass