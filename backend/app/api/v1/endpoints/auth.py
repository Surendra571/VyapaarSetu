from decimal import Decimal
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Request
from fastapi.responses import HTMLResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.security import create_access_token
from app.models.user import User
from app.models.retailer import Retailer
from app.services.sms_service import sms_provider
from app.schemas.auth import (
    DemoLoginRequest,
    SendOtpRequest,
    RegisterRetailerRequest,
    TokenResponse,
    UserProfileResponse,
    RetailerProfileResponse,
)
from app.schemas.common import StandardMessageResponse
from app.api.deps import get_current_user

router = APIRouter()


def normalize_phone(phone: Optional[str]) -> str:
    """Normalize phone number to 10-digit Indian mobile format."""
    if not phone:
        return ""
    cleaned = "".join(filter(str.isdigit, phone.strip()))
    if cleaned.startswith("91") and len(cleaned) == 12:
        cleaned = cleaned[2:]
    elif cleaned.startswith("0") and len(cleaned) == 11:
        cleaned = cleaned[1:]
    return cleaned


@router.post(
    "/auth/send-otp",
    response_model=StandardMessageResponse,
    summary="Request OTP SMS",
    description="Generates and dispatches transactional OTP code to phone number via configured provider.",
)
async def send_otp(
    payload: DemoLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> StandardMessageResponse:
    raw_phone = payload.phone_number.strip() if payload.phone_number else "9826011111"
    phone = normalize_phone(raw_phone) or raw_phone
    if hasattr(sms_provider, "otp_store"):
        can_send, rate_err = sms_provider.otp_store.can_send(phone)
        if not can_send:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=rate_err)
        otp = sms_provider.otp_store.generate_and_store(phone)
    else:
        otp = "123456"

    sent = await sms_provider.send_otp(phone, otp)
    if not sent:
        raise HTTPException(status_code=500, detail="Failed to deliver SMS OTP.")

    # In production, phone number is masked to prevent enumeration attacks
    masked_phone = f"******{phone[-4:]}" if len(phone) >= 4 else phone
    return StandardMessageResponse(
        message=f"OTP dispatched successfully to {masked_phone}. (Dev hint: {otp} or demo 123456)"
    )


@router.get(
    "/auth/sms-status",
    summary="Get SMS Provider Configuration Status",
    description="Returns current SMS provider mode (mock or live gateway) and configuration status.",
)
async def get_sms_status():
    return sms_provider.get_status()


@router.get(
    "/auth/demo-login",
    summary="Mock OTP Demo Authentication (Browser Helper)",
    description="Allows direct browser GET navigation to demo-login: automatically sets access token in localStorage and loads the workspace screens.",
)
async def demo_login_get(
    request: Request,
    role: Optional[str] = None,
    phone: Optional[str] = None,
    redirect: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    target_phone = phone or ("9826000000" if (role and "desk" in role.lower()) else "9826011111")
    stmt = select(User).options(selectinload(User.retailers)).where(User.phone_number == target_phone)
    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        stmt_any = select(User).options(selectinload(User.retailers))
        res_any = await db.execute(stmt_any)
        user = res_any.scalars().first()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No matching demo user found in database.",
        )

    claims = {"role": user.role}
    if user.retailers:
        claims["retailer_id"] = str(user.retailers[0].id)

    access_token = create_access_token(subject=str(user.id), claims=claims)

    target_redirect = redirect or ("/desk" if (role and "desk" in role.lower()) else "/catalogue")
    if not target_redirect.startswith("/") or target_redirect.startswith("//"):
        target_redirect = "/catalogue"

    accept = request.headers.get("accept", "")
    if "text/html" in accept:
        html_content = f"""<!DOCTYPE html>
<html>
<head>
  <meta charset="utf-8">
  <title>VyapaarSetu - Launching Demo Workspace...</title>
  <style>
    body {{
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: #064e3b;
      color: #f0fdf4;
      display: flex;
      flex-direction: column;
      align-items: center;
      justify-content: center;
      height: 100vh;
      margin: 0;
    }}
    .box {{
      text-align: center;
      background: rgba(255, 255, 255, 0.08);
      border: 1px solid rgba(255, 255, 255, 0.15);
      border-radius: 20px;
      padding: 40px;
      max-width: 420px;
    }}
    .spinner {{
      width: 40px;
      height: 40px;
      border: 4px solid rgba(255,255,255,0.2);
      border-top-color: #34d399;
      border-radius: 50%;
      animation: spin 0.8s linear infinite;
      margin: 0 auto 20px;
    }}
    @keyframes spin {{ to {{ transform: rotate(360deg); }} }}
    h2 {{ margin: 0 0 10px; font-weight: 800; }}
    p {{ margin: 0; font-size: 14px; opacity: 0.85; }}
  </style>
</head>
<body>
  <div class="box">
    <div class="spinner"></div>
    <h2>Opening VyapaarSetu</h2>
    <p>Signed in as <b>{user.full_name}</b> ({user.role}). Redirecting to workspace screens...</p>
  </div>
  <script>
    localStorage.setItem('vyapaar_access_token', '{access_token}');
    setTimeout(() => {{ window.location.href = '{target_redirect}'; }}, 300);
  </script>
</body>
</html>"""
        return HTMLResponse(content=html_content)

    return {
        "access_token": access_token,
        "token_type": "bearer",
        "redirect_url": target_redirect,
        "user": {
            "id": str(user.id),
            "phone_number": user.phone_number,
            "full_name": user.full_name,
            "role": user.role,
        },
        "message": "Demo token issued. For standard API authentication, POST to /api/v1/auth/demo-login.",
    }


@router.post(
    "/auth/login",
    response_model=TokenResponse,
    summary="User Authentication (Sign In)",
    description="Sign in using mobile number and verified OTP.",
)
@router.post(
    "/auth/demo-login",
    response_model=TokenResponse,
    summary="Mock OTP Demo Authentication",
    description="Sign in using demo credentials or mock OTP (default code: 123456).",
)
async def demo_login(
    payload: DemoLoginRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    # 1. Normalize and Verify OTP with Provider
    raw_phone = payload.phone_number.strip() if payload.phone_number else None
    phone_target = normalize_phone(raw_phone) if raw_phone else ("9826000000" if (payload.role and "desk" in payload.role.lower()) else "9826011111")

    valid, msg = sms_provider.verify_otp(phone_target, payload.otp_code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP code. {msg}",
        )

    # 2. Lookup user by phone or role selector
    stmt = select(User).options(selectinload(User.retailers))
    if raw_phone:
        stmt = stmt.where((User.phone_number == phone_target) | (User.phone_number == raw_phone))
    elif payload.role:
        stmt = stmt.where(User.role == payload.role.strip())
    else:
        # Default to Retailer 1
        stmt = stmt.where(User.phone_number == "9826011111")

    res = await db.execute(stmt)
    user = res.scalar_one_or_none()

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No account found with mobile number '{phone_target}'. Please check your number or tap 'Create Account' to sign up in 30 seconds.",
        )

    # 3. Build token claims
    retailer_profile = None
    claims = {"role": user.role}
    if user.retailers:
        r = user.retailers[0]
        claims["retailer_id"] = str(r.id)
        retailer_profile = RetailerProfileResponse.model_validate(r)

    access_token = create_access_token(subject=str(user.id), claims=claims)

    user_profile = UserProfileResponse(
        id=user.id,
        phone_number=user.phone_number,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        retailer=retailer_profile,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_profile,
    )


@router.post(
    "/auth/register",
    response_model=TokenResponse,
    summary="Retailer Account Self-Registration (Sign Up)",
    description="Registers a new Kirana store retailer account using mobile number verification and creates business ledger profile.",
)
async def register_retailer(
    payload: RegisterRetailerRequest,
    db: AsyncSession = Depends(get_db),
) -> TokenResponse:
    phone = normalize_phone(payload.phone_number)
    if len(phone) < 10:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid mobile number. Please enter a valid 10-digit Indian mobile number.",
        )

    # 1. Verify OTP code
    valid, msg = sms_provider.verify_otp(phone, payload.otp_code)
    if not valid:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Invalid OTP code. {msg}",
        )

    # 2. Check if account already exists
    stmt = select(User).where(User.phone_number == phone)
    res = await db.execute(stmt)
    existing_user = res.scalar_one_or_none()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"An account with mobile number '{phone}' already exists. Please switch to Sign In.",
        )

    # 3. Generate unique retailer code
    unique_suffix = secrets.token_hex(3).upper()
    retailer_code = f"RET-JBP-{unique_suffix}"

    # 4. Create User entity
    new_user = User(
        phone_number=phone,
        full_name=payload.full_name.strip(),
        role="ROLE_RETAILER",
        is_active=True,
    )
    db.add(new_user)
    await db.flush()

    # 5. Create Retailer entity with standard starter credit limit
    new_retailer = Retailer(
        user_id=new_user.id,
        retailer_code=retailer_code,
        store_name=payload.store_name.strip(),
        owner_name=payload.full_name.strip(),
        address=payload.address.strip() if payload.address else "Main Market, Jabalpur",
        city=payload.city.strip() if payload.city else "Jabalpur",
        gst_number=payload.gst_number.strip() if payload.gst_number else None,
        credit_limit=Decimal("50000.00"),
        outstanding_amount=Decimal("0.00"),
        available_credit=Decimal("50000.00"),
        is_credit_locked=False,
        pricing_tier="STANDARD",
    )
    db.add(new_retailer)
    await db.commit()
    await db.refresh(new_user)
    await db.refresh(new_retailer)

    # 6. Issue access token and return token response
    claims = {"role": new_user.role, "retailer_id": str(new_retailer.id)}
    access_token = create_access_token(subject=str(new_user.id), claims=claims)

    retailer_profile = RetailerProfileResponse.model_validate(new_retailer)
    user_profile = UserProfileResponse(
        id=new_user.id,
        phone_number=new_user.phone_number,
        full_name=new_user.full_name,
        role=new_user.role,
        is_active=new_user.is_active,
        retailer=retailer_profile,
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        user=user_profile,
    )


@router.get(
    "/auth/me",
    response_model=UserProfileResponse,
    summary="Get Authenticated User Profile",
    description="Validates Bearer token and returns authenticated retailer or desk operator details.",
)
async def get_me(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
) -> UserProfileResponse:
    # Explicitly load retailers relationship to guarantee tenancy
    stmt = select(User).options(selectinload(User.retailers)).where(User.id == current_user.id)
    res = await db.execute(stmt)
    user = res.scalar_one()

    retailer_profile = None
    if user.retailers:
        retailer_profile = RetailerProfileResponse.model_validate(user.retailers[0])

    return UserProfileResponse(
        id=user.id,
        phone_number=user.phone_number,
        full_name=user.full_name,
        role=user.role,
        is_active=user.is_active,
        retailer=retailer_profile,
    )


@router.post(
    "/auth/logout",
    summary="Revoke Current Session",
    description="Logs out the user and invalidates the client-side session token.",
)
async def logout(current_user: User = Depends(get_current_user)) -> dict:
    return {
        "status": "success",
        "message": f"User {current_user.phone_number} successfully logged out.",
    }
