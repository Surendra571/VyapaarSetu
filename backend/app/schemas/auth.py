import uuid
from decimal import Decimal
from typing import Optional
from pydantic import BaseModel, Field, ConfigDict


class DemoLoginRequest(BaseModel):
    """Demo login request by phone number or preset role."""
    phone_number: Optional[str] = Field(
        default=None,
        description="Registered phone number (e.g. 9826011111 for Retailer 1, 9826000000 for Order Desk)",
        examples=["9826011111"],
    )
    role: Optional[str] = Field(
        default=None,
        description="Optional shortcut role selector: ROLE_RETAILER | ROLE_ORDER_DESK",
        examples=["ROLE_RETAILER"],
    )
    otp_code: Optional[str] = Field(
        default="123456",
        description="Mock OTP code (default 123456)",
        examples=["123456"],
    )


class RetailerProfileResponse(BaseModel):
    """Retailer business and credit ledger metadata."""
    id: uuid.UUID
    retailer_code: str
    store_name: str
    owner_name: str
    address: str
    city: str
    gst_number: Optional[str] = None
    credit_limit: Decimal
    outstanding_amount: Decimal
    available_credit: Decimal
    is_credit_locked: bool
    pricing_tier: str

    model_config = ConfigDict(from_attributes=True)


class UserProfileResponse(BaseModel):
    """User account details and associated role."""
    id: uuid.UUID
    phone_number: str
    full_name: str
    role: str
    is_active: bool
    retailer: Optional[RetailerProfileResponse] = None

    model_config = ConfigDict(from_attributes=True)


class TokenResponse(BaseModel):
    """JWT Bearer authentication token and user profile."""
    access_token: str
    token_type: str = "bearer"
    user: UserProfileResponse
