import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, UniqueConstraint, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.retailer import Retailer
    from app.models.catalog import Product
    from app.models.order import OrderItem


class RetailerPrice(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Custom negotiated dealer prices per retailer and product (Excl. GST)."""

    __tablename__ = "retailer_prices"

    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retailers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    custom_price: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    price_basis: Mapped[str] = mapped_column(
        String(50),
        default="UNRESOLVED_PACK_OR_CASE",  # Configurable / unresolved per constraint 1
        nullable=False,
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    retailer: Mapped["Retailer"] = relationship(
        "Retailer",
        back_populates="custom_prices",
        lazy="selectin",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="retailer_prices",
        lazy="selectin",
    )

    __table_args__ = (
        UniqueConstraint("retailer_id", "product_id", name="uq_retailer_product_price"),
        Index("idx_retailer_price_lookup", "retailer_id", "product_id"),
    )


class Scheme(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Trade promotion schemes (Volume discounts, free goods, slab deals)."""

    __tablename__ = "schemes"

    scheme_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        index=True,
    )

    # Business Constraint 3: Scheme stacking must be configurable (not assumed)
    is_stackable: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    priority: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    valid_from: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    valid_to: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    # Relationships
    rules: Mapped[List["SchemeRule"]] = relationship(
        "SchemeRule",
        back_populates="scheme",
        cascade="all, delete-orphan",
        lazy="selectin",
    )
    order_items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="applied_scheme",
    )


class SchemeRule(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Specific conditions and reward actions for a trade scheme."""

    __tablename__ = "scheme_rules"

    scheme_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    rule_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # BUY_X_GET_Y_FREE | PERCENTAGE_DISCOUNT | FLAT_DISCOUNT
    )
    qualifying_product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    min_quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    free_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    free_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    discount_percentage: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    discount_amount: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(10, 2),
        nullable=True,
    )

    # Relationships
    scheme: Mapped["Scheme"] = relationship(
        "Scheme",
        back_populates="rules",
        lazy="selectin",
    )
    qualifying_product: Mapped["Product"] = relationship(
        "Product",
        back_populates="qualifying_schemes",
        foreign_keys=[qualifying_product_id],
        lazy="selectin",
    )
    free_product: Mapped[Optional["Product"]] = relationship(
        "Product",
        back_populates="free_schemes",
        foreign_keys=[free_product_id],
        lazy="selectin",
    )
