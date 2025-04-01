"""Add search index to Property table

Revision ID: 2a3b4c5d6e7f
Revises: 1a2b3c4d5e6f
Create Date: 2025-04-01 17:40:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = '2a3b4c5d6e7f'
down_revision = '1a2b3c4d5e6f'
branch_labels = None
depends_on = None


def upgrade():
    # Create a GIN index for full-text search on the property_id column
    op.execute(
        "CREATE INDEX idx_property_search ON property USING gin (to_tsvector('english', property_id))"
    )
    
    # Create indexes for common query patterns
    op.create_index(op.f('ix_property_updated_at'), 'property', ['updated_at'], unique=False)
    op.create_index(op.f('ix_tax_code_updated_at'), 'tax_code', ['updated_at'], unique=False)


def downgrade():
    # Drop indexes
    op.drop_index(op.f('ix_tax_code_updated_at'), table_name='tax_code')
    op.drop_index(op.f('ix_property_updated_at'), table_name='property')
    op.execute("DROP INDEX idx_property_search")