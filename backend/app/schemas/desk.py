import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field


class DeskOrderLinePatchRequest(BaseModel):
    """Order desk adjustment to a line item (e.g. Due to physical stock variance)."""
    approved_qty: int = Field(..., ge=0, description="Corrected approved quantity in cases")
    reason: str = Field(..., min_length=3, description="Mandatory audit explanation for quantity change")


class DeskOrderHoldRequest(BaseModel):
    """Place an order on credit hold or administrative review."""
    reason: str = Field(..., min_length=3, description="Justification for placing order on hold")


class DeskOrderRejectRequest(BaseModel):
    """Reject an order and release reserved inventory back to warehouse."""
    reason: str = Field(..., min_length=3, description="Mandatory reason for order rejection")


class DeskOrderApproveRequest(BaseModel):
    """Approve order for warehouse picking and dispatch."""
    notes: str = Field(default="Approved by Order Desk", description="Desk processing remarks")
    override_credit_hold: bool = Field(default=False, description="Explicit flag if overriding a credit hold")


class VanLoadingStoreBreakdown(BaseModel):
    store_name: str
    retailer_code: str
    order_number: str
    purchased_cases: int
    free_cases: int
    total_cases: int


class VanLoadingItem(BaseModel):
    """SKU-level aggregation for warehouse packing & van loading."""
    sku_code: str
    product_name: str
    pack_size: str
    default_dealer_price: Decimal
    purchased_cases: int
    free_cases: int
    total_cases: int
    store_count: int
    stores: List[VanLoadingStoreBreakdown] = Field(default_factory=list)


class VanLoadingListResponse(BaseModel):
    """Warehouse dispatch sheet of all approved orders."""
    generated_at: datetime
    total_approved_orders: int
    total_dispatch_cases: int
    total_purchased_cases: int
    total_free_goods_cases: int
    items: List[VanLoadingItem]


class InactiveRetailerItem(BaseModel):
    """Retailer with no confirmed or approved order in the threshold period."""
    retailer_id: uuid.UUID
    retailer_code: str
    store_name: str
    owner_name: str
    phone_number: str
    city: str
    address: str
    credit_limit: Decimal
    outstanding_amount: Decimal
    available_credit: Decimal
    is_credit_locked: bool
    last_order_date: Optional[datetime] = None
    days_since_last_order: Optional[int] = None
    inactivity_tier: str = "WARNING"  # WARNING (14-21 days) | CRITICAL (>21 days) | NEVER_ORDERED


class InactiveRetailersResponse(BaseModel):
    """Report of kirana stores needing sales rep follow-up."""
    threshold_days: int
    total_inactive_retailers: int
    page: int = 1
    page_size: int = 20
    total_pages: int = 1
    retailers: List[InactiveRetailerItem]


