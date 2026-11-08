"""Add free goods snapshot and multi-benefit order item benefits.

Revision ID: d93a11c7f5a1
Revises: 7a8b9c0d1e2f
Create Date: 2026-11-08
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "d93a11c7f5a1"
down_revision: Union[str, Sequence[str], None] = "7a8b9c0d1e2f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add snapshot columns to order_items for single-benefit backward-compatibility
    op.execute("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS free_product_name_snapshot VARCHAR(250);")
    op.execute("ALTER TABLE order_items ADD COLUMN IF NOT EXISTS free_sku_code_snapshot VARCHAR(50);")

    # 2. Create order_item_benefits table for robust multi-benefit scheme modeling
    op.execute("""
    CREATE TABLE IF NOT EXISTS order_item_benefits (
        id UUID PRIMARY KEY,
        order_item_id UUID NOT NULL REFERENCES order_items(id) ON DELETE CASCADE,
        scheme_id UUID REFERENCES schemes(id) ON DELETE SET NULL,
        scheme_name VARCHAR(200) NOT NULL,
        benefit_type VARCHAR(50) NOT NULL,
        awarded_product_id UUID REFERENCES products(id) ON DELETE RESTRICT,
        awarded_sku_code VARCHAR(50),
        awarded_product_name VARCHAR(250),
        awarded_quantity INTEGER NOT NULL DEFAULT 0,
        awarded_uom VARCHAR(50) NOT NULL DEFAULT 'CASE',
        discount_amount NUMERIC(10, 2) NOT NULL DEFAULT 0.00,
        calculation_details TEXT,
        created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
    );
    """)
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_item_benefits_order_item_id ON order_item_benefits (order_item_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_item_benefits_scheme_id ON order_item_benefits (scheme_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_order_item_benefits_awarded_product_id ON order_item_benefits (awarded_product_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS order_item_benefits CASCADE;")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS free_sku_code_snapshot;")
    op.execute("ALTER TABLE order_items DROP COLUMN IF EXISTS free_product_name_snapshot;")
