from typing import List, Tuple
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.models.retailer import Retailer
from app.schemas.catalog import RetailerPriceResponse
from app.api.deps import require_retailer
from app.services.pricing_service import PricingService

router = APIRouter()


@router.get(
    "/retailers/me/prices",
    response_model=List[RetailerPriceResponse],
    summary="Get Retailer-Specific Custom Price List",
    description="Returns the authenticated retailer's contracted dealer prices, with master fallback (Excl. GST).",
)
async def get_my_contracted_prices(
    retailer_auth: Tuple[User, Retailer] = Depends(require_retailer),
    db: AsyncSession = Depends(get_db),
) -> List[RetailerPriceResponse]:
    _, retailer = retailer_auth
    return await PricingService.get_retailer_full_pricelist(db, retailer.id)

