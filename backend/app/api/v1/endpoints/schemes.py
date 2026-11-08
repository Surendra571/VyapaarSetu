from typing import List
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.models.user import User
from app.schemas.catalog import SchemeResponse
from app.api.deps import get_current_user
from app.repositories.scheme_repo import list_active_schemes

router = APIRouter()


@router.get(
    "/schemes",
    response_model=List[SchemeResponse],
    summary="List Active Trade Promotions",
    description="Active volume discounts, slab deals, and free goods promotions.",
)
async def get_active_schemes(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> List[SchemeResponse]:
    schemes = await list_active_schemes(db)
    return [SchemeResponse.model_validate(s) for s in schemes]

