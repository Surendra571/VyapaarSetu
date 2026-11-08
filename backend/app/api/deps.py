from typing import Tuple, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from app.core.database import get_db
from app.core.security import decode_access_token
from app.models.user import User
from app.models.retailer import Retailer

# HTTP Bearer token extractor
security_scheme = HTTPBearer(auto_error=False)


async def get_current_user(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: AsyncSession = Depends(get_db),
) -> User:
    """Validate JWT access token and return active User with retailers loaded."""
    if not credentials:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication token is missing. Please sign in.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    payload = decode_access_token(credentials.credentials)
    if not payload or "sub" not in payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired access token.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    user_id = payload["sub"]
    stmt = (
        select(User)
        .where(User.id == user_id, User.is_active == True)
        .options(selectinload(User.retailers))
    )
    result = await db.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User account not found or is deactivated.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    return user


async def require_retailer(
    current_user: User = Depends(get_current_user),
) -> Tuple[User, Retailer]:
    """
    Enforce ROLE_RETAILER access control.
    Returns: (current_user, associated_retailer)
    Never trusts client-supplied retailer IDs.
    """
    if current_user.role != "ROLE_RETAILER":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to registered retailers only.",
        )

    if not current_user.retailers:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No retailer business profile is attached to this user account.",
        )

    return (current_user, current_user.retailers[0])


async def require_order_desk(
    current_user: User = Depends(get_current_user),
) -> User:
    """Enforce ROLE_ORDER_DESK access control."""
    if current_user.role != "ROLE_ORDER_DESK":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Access restricted to Order Desk operators and administrators only.",
        )
    return current_user

