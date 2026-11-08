import uuid
from decimal import Decimal
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Numeric, String, Text, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.pricing import RetailerPrice
    from app.models.order import Order
    from app.models.ai_capture import AICapture
    from app.models.catalog import SKUAlias


class Retailer(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Retailer kirana business profile and credit ledger attributes."""

    __tablename__ = "retailers"

    user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    retailer_code: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    store_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
        index=True,
    )
    owner_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    address: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    city: Mapped[str] = mapped_column(
        String(100),
        default="Jabalpur",
        nullable=False,
    )
    gst_number: Mapped[Optional[str]] = mapped_column(
        String(30),
        nullable=True,
    )

    # Isolated Credit Ledger Attributes (Per Business Constraint 5)
    credit_limit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    outstanding_amount: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    available_credit: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    is_credit_locked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    pricing_tier: Mapped[str] = mapped_column(
        String(50),
        default="STANDARD",
        nullable=False,
    )

    # Relationships
    user: Mapped["User"] = relationship(
        "User",
        back_populates="retailers",
    )
    custom_prices: Mapped[List["RetailerPrice"]] = relationship(
        "RetailerPrice",
        back_populates="retailer",
        cascade="all, delete-orphan",
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="retailer",
        cascade="all, delete-orphan",
    )
    ai_captures: Mapped[List["AICapture"]] = relationship(
        "AICapture",
        back_populates="retailer",
        cascade="all, delete-orphan",
    )
    custom_aliases: Mapped[List["SKUAlias"]] = relationship(
        "SKUAlias",
        back_populates="retailer",
        cascade="all, delete-orphan",
    )

    __table_args__ = (
        Index("idx_retailer_user_store", "user_id", "store_name"),
    )

