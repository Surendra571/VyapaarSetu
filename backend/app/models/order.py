import uuid
from datetime import datetime
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, DateTime, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.retailer import Retailer
    from app.models.catalog import Product
    from app.models.pricing import Scheme
    from app.models.user import User
    from app.models.audit import ExportBatch, AuditLog


class Order(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Retailer order header representing submitted, held, or approved orders."""

    __tablename__ = "orders"

    order_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retailers.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_DESK_APPROVAL",  # DRAFT | PENDING_DESK_APPROVAL | CREDIT_HOLD | APPROVED | REJECTED | EXPORTED
        nullable=False,
        index=True,
    )

    # Business Constraint 2: Subtotals strictly exclude GST
    subtotal_excl_gst: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    credit_hold_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )
    desk_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )
    rejection_reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Operational audit fields
    approved_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    approved_at: Mapped[Optional[datetime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    export_batch_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("export_batches.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )

    # Relationships
    retailer: Mapped["Retailer"] = relationship(
        "Retailer",
        back_populates="orders",
    )
    items: Mapped[List["OrderItem"]] = relationship(
        "OrderItem",
        back_populates="order",
        cascade="all, delete-orphan",
    )
    approved_by_user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="approved_orders",
        foreign_keys=[approved_by_user_id],
    )
    export_batch: Mapped[Optional["ExportBatch"]] = relationship(
        "ExportBatch",
        back_populates="orders",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="order",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItem(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Line items with immutable product, price, and scheme snapshots."""

    __tablename__ = "order_items"

    order_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    ordered_qty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    approved_qty: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    uom_type: Mapped[str] = mapped_column(
        String(50),
        default="CASE",  # CASE | PACK | PIECE
        nullable=False,
    )

    # Applied Scheme Data
    applied_scheme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="SET NULL"),
        nullable=True,
    )
    scheme_discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    free_item_qty: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    line_subtotal_excl_gst: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )

    # Immutable Point-in-time Snapshots
    product_name_snapshot: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )
    sku_code_snapshot: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
    )
    price_per_unit_snapshot: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )
    price_basis_snapshot: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # Preserves UNRESOLVED_PACK_OR_CASE or authoritative basis
    )
    scheme_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(200),
        nullable=True,
    )
    discount_percentage_snapshot: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(5, 2),
        nullable=True,
    )
    free_product_name_snapshot: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )
    free_sku_code_snapshot: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )

    # Relationships
    order: Mapped["Order"] = relationship(
        "Order",
        back_populates="items",
    )
    product: Mapped["Product"] = relationship(
        "Product",
        back_populates="order_items",
    )
    applied_scheme: Mapped[Optional["Scheme"]] = relationship(
        "Scheme",
        back_populates="order_items",
    )
    benefits: Mapped[List["OrderItemBenefit"]] = relationship(
        "OrderItemBenefit",
        back_populates="order_item",
        cascade="all, delete-orphan",
        lazy="selectin",
    )


class OrderItemBenefit(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """
    Independent benefit representation for free-product SKUs or specific discounts
    awarded to a purchased order item by a scheme.
    Guarantees that multiple awarded SKUs are never merged or conflated.
    """

    __tablename__ = "order_item_benefits"

    order_item_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("order_items.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    scheme_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("schemes.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    scheme_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    benefit_type: Mapped[str] = mapped_column(
        String(50),
        nullable=False,  # FREE_GOODS | SLAB_DISCOUNT | FLAT_DISCOUNT
    )

    # For FREE_GOODS benefits:
    awarded_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    awarded_sku_code: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
    )
    awarded_product_name: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )
    awarded_quantity: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
    )
    awarded_uom: Mapped[str] = mapped_column(
        String(50),
        default="CASE",
        nullable=False,
    )

    # For monetary discounts:
    discount_amount: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=Decimal("0.00"),
        nullable=False,
    )

    # Audit & explanation details
    calculation_details: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    order_item: Mapped["OrderItem"] = relationship(
        "OrderItem",
        back_populates="benefits",
    )
    scheme: Mapped[Optional["Scheme"]] = relationship(
        "Scheme",
        lazy="selectin",
    )
    awarded_product: Mapped[Optional["Product"]] = relationship(
        "Product",
        foreign_keys=[awarded_product_id],
        lazy="selectin",
    )


