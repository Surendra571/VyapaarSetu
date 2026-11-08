import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List
from pydantic import BaseModel, Field, ConfigDict


class InventoryAvailabilityResponse(BaseModel):
    """Stock availability in cases."""
    product_id: uuid.UUID
    stock_cases: int
    reserved_cases: int
    available_cases: int
    reorder_level_cases: int
    is_in_stock: bool

    model_config = ConfigDict(from_attributes=True)


class SchemeRuleResponse(BaseModel):
    """Scheme criteria and award actions."""
    id: uuid.UUID
    rule_type: str
    qualifying_product_id: uuid.UUID
    min_quantity: int
    free_product_id: Optional[uuid.UUID] = None
    free_quantity: Optional[int] = None
    discount_percentage: Optional[Decimal] = None
    discount_amount: Optional[Decimal] = None

    model_config = ConfigDict(from_attributes=True)


class SchemeResponse(BaseModel):
    """Trade promotion scheme."""
    id: uuid.UUID
    scheme_code: str
    name: str
    description: Optional[str] = None
    is_active: bool
    is_stackable: bool
    priority: int
    valid_from: Optional[datetime] = None
    valid_to: Optional[datetime] = None
    rules: List[SchemeRuleResponse] = []

    model_config = ConfigDict(from_attributes=True)


class ProductResponse(BaseModel):
    """Catalog product with pricing and availability."""
    id: uuid.UUID
    sku_code: str
    name: str
    brand: str
    category: str
    pack_size_description: str
    units_per_case: int
    default_dealer_price: Decimal = Field(description="Dealer price excluding GST")
    mrp: Optional[Decimal] = None
    price_basis: str = Field(description="Basis marker (UNRESOLVED_PACK_OR_CASE | PER_CASE | PER_PIECE)")
    is_active: bool
    image_url: Optional[str] = None
    available_cases: int = 0
    price_notice: str = "All prices exclude GST. Price basis per pack/case is provisional."

    model_config = ConfigDict(from_attributes=True)


class ProductDetailResponse(ProductResponse):
    """Detailed product with inventory breakdown and qualifying schemes."""
    inventory: Optional[InventoryAvailabilityResponse] = None
    active_schemes: List[SchemeResponse] = []


class RetailerPriceResponse(BaseModel):
    """Contracted custom pricing for the authenticated retailer."""
    product_id: uuid.UUID
    sku_code: str
    product_name: str
    effective_price: Decimal = Field(description="Contracted rate or master dealer price (Excl. GST)")
    price_basis: str
    is_custom_price: bool
    units_per_case: int
    price_notice: str = "Prices exclude GST."
