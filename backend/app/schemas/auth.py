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


class SendOtpRequest(BaseModel):
    """Request transactional OTP code to mobile number."""
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="10-digit mobile number",
        examples=["9826011111"],
    )


class RegisterRetailerRequest(BaseModel):
    """Retailer self-registration request with business details and OTP."""
    phone_number: str = Field(
        ...,
        min_length=10,
        max_length=15,
        description="10-digit Indian mobile number",
        examples=["9876543210"],
    )
    full_name: str = Field(
        ...,
        min_length=2,
        max_length=150,
        description="Owner / contact full name",
        examples=["Rajesh Kumar"],
    )
    store_name: str = Field(
        ...,
        min_length=2,
        max_length=200,
        description="Kirana / shop / business name",
        examples=["Kumar Super Store"],
    )
    city: Optional[str] = Field(
        default="Jabalpur",
        max_length=100,
        description="Operating city",
        examples=["Jabalpur"],
    )
    address: Optional[str] = Field(
        default="Main Market, Jabalpur",
        max_length=300,
        description="Shop address or landmark",
        examples=["Shop 4, Wright Town, Jabalpur"],
    )
    gst_number: Optional[str] = Field(
        default=None,
        max_length=30,
        description="Optional GSTIN number",
    )
    otp_code: str = Field(
        default="123456",
        min_length=4,
        max_length=10,
        description="Verification OTP received via SMS",
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
