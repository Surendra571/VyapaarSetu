from fastapi import APIRouter
from app.api.v1.endpoints import (
    health,
    auth,
    products,
    retailers,
    schemes,
    orders,
    ai_capture,
    desk,
    exports,
)

api_v1_router = APIRouter()

# 1. System Health
api_v1_router.include_router(health.router, tags=["System Health"])

# 2. Authentication
api_v1_router.include_router(auth.router, tags=["Authentication"])

# 3. Catalogue & Pricing
api_v1_router.include_router(products.router, tags=["Catalogue"])
api_v1_router.include_router(retailers.router, tags=["Retailer Pricing"])
api_v1_router.include_router(schemes.router, tags=["Schemes & Promotions"])

# 4. Orders
api_v1_router.include_router(orders.router, tags=["Orders"])

# 5. AI Capture
api_v1_router.include_router(ai_capture.router, prefix="/ai-capture", tags=["AI Order Capture"])

# 6. Order Desk & Tally Export
api_v1_router.include_router(desk.router, prefix="/desk", tags=["Order Desk"])
api_v1_router.include_router(exports.router, prefix="/desk", tags=["Tally Accounting Export"])
