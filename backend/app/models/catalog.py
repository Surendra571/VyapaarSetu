import uuid
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.retailer import Retailer
    from app.models.pricing import RetailerPrice, SchemeRule
    from app.models.order import OrderItem
    from app.models.ai_capture import AICaptureLine


class Product(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Product master catalogue entity."""

    __tablename__ = "products"

    sku_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
        index=True,
    )
    brand: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    category: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,  # Packaged Food, Home Care, etc.
    )
    pack_size_description: Mapped[str] = mapped_column(
        String(100),
        nullable=False,  # e.g., "75 g", "1 kg", "250 g"
    )
    units_per_case: Mapped[int] = mapped_column(
        Integer,
        nullable=False,  # e.g. 96 for biscuits, 20 for detergent, 40 for tea
    )

    # Dealer Base Price (Excluding GST)
    default_dealer_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    mrp: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Business Constraint 1: Unresolved Pack vs. Case basis marker
    price_basis: Mapped[str] = mapped_column(
        String(50),
        default="UNRESOLVED_PACK_OR_CASE",  # UNRESOLVED_PACK_OR_CASE | PER_CASE | PER_PIECE
        nullable=False,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )
    image_url: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=True,
        default=None,
    )

    # Relationships
    inventory: Mapped["Inventory"] = relationship(
        "Inventory",
        back_populates="product",
        uselist=False,
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    retailer_prices: Mapped[List["RetailerPrice"]] = relationship(
        "RetailerPrice",
        back_populates="product",
        cascade="all, delete-orphan",
    )
    aliases: Mapped[List["SKUAlias"]] = relationship(
        "SKUAlias",
        back_populates="product",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="product",
    )
    qualifying_schemes: Mapped[List["SchemeRule"]] = relationship(
        "SchemeRule",
        back_populates="qualifying_product",
        foreign_keys="SchemeRule.qualifying_product_id",
    )
    free_schemes: Mapped[List["SchemeRule"]] = relationship(
        "SchemeRule",
        back_populates="free_product",
        foreign_keys="SchemeRule.free_product_id",
    )


class Inventory(Base, TimestampMixin):
    """Inventory tracking table per SKU."""

    __tablename__ = "inventory"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        primary_key=True,
    )
    stock_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    reserved_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    available_cases: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        index=True,
    )
    reorder_level_cases: Mapped[int] = mapped_column(
        Integer,
        default=10,
        nullable=False,
    )

    # Relationship
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="inventory",
        lazy="selectin",
    )


class SKUAlias(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Global or retailer-specific aliases for AI matching and natural language ordering."""

    __tablename__ = "sku_aliases"

    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    retailer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retailers.id", ondelete="CASCADE"),
        nullable=True,
        index=True,  # NULL indicates a global alias, otherwise retailer-specific
    )
    alias_text: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    notes: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )

    # Relationships
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="aliases",
        lazy="selectin",
    )
    retailer: Mapped[Optional["Retailer"]] = relationship(
        "Retailer",
        back_populates="custom_aliases",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("alias_text", "retailer_id", name="uq_sku_alias_text_retailer"),
        Index("idx_sku_alias_lookup", "alias_text", "retailer_id"),
    )
