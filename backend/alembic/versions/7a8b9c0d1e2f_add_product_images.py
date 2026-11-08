"""Add image URLs to products.

Revision ID: 7a8b9c0d1e2f
Revises: 4e317dd8e50a
Create Date: 2026-11-06
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "7a8b9c0d1e2f"
down_revision: Union[str, Sequence[str], None] = "4e317dd8e50a"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);")
    op.execute(
        "UPDATE products "
        "SET image_url = '/images/products/' || sku_code || '.webp' "
        "WHERE image_url IS NULL"
    )


def downgrade() -> None:
    op.execute("ALTER TABLE products DROP COLUMN IF EXISTS image_url;")
