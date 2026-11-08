import asyncio
from sqlalchemy import text
from app.core.database import engine

async def migrate():
    async with engine.begin() as conn:
        await conn.execute(text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500);"))
        await conn.execute(text("UPDATE products SET image_url = '/images/products/' || sku_code || '.webp' WHERE image_url IS NULL;"))
    print("Database migration for image_url completed successfully!")

if __name__ == "__main__":
    asyncio.run(migrate())
