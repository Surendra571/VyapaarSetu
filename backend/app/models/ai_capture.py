import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import Boolean, ForeignKey, Integer, Numeric, String, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.retailer import Retailer
    from app.models.catalog import Product


class AICapture(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Raw unstructured text capture session from WhatsApp or manual paste."""

    __tablename__ = "ai_captures"

    retailer_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("retailers.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    raw_text: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )
    status: Mapped[str] = mapped_column(
        String(50),
        default="PENDING_PARSE",  # PENDING_PARSE | PARSED_PENDING_REVIEW | CONFIRMED_TO_CART | DISCARDED
        nullable=False,
        index=True,
    )
    model_version: Mapped[str] = mapped_column(
        String(50),
        default="gpt-4o",
        nullable=False,
    )

    # Relationships
    retailer: Mapped["Retailer"] = relationship(
        "Retailer",
        back_populates="ai_captures",
    )
    lines: Mapped[List["AICaptureLine"]] = relationship(
        "AICaptureLine",
        back_populates="ai_capture",
        cascade="all, delete-orphan",
    )


class AICaptureLine(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Parsed items with SKU matching confidence and alternatives."""

    __tablename__ = "ai_capture_lines"

    ai_capture_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ai_captures.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    line_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    raw_line_text: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
    )
    parsed_item_name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )
    parsed_quantity: Mapped[int] = mapped_column(
        Integer,
        default=1,
        nullable=False,
    )
    parsed_uom: Mapped[str] = mapped_column(
        String(50),
        default="CASE",
        nullable=False,
    )

    # SKU matching & Confidence (Business Constraint 8)
    matched_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    confidence_score: Mapped[Decimal] = mapped_column(
        Numeric(3, 2),
        default=Decimal("0.00"),
        nullable=False,
    )
    alternatives_json: Mapped[Optional[List[Dict[str, Any]]]] = mapped_column(
        JSON,
        nullable=True,  # Stores list of alternative product matches with confidence scores
    )
    is_uncertain: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Human Confirmation & Resolution (Business Constraint 7 & 8)
    resolved_product_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("products.id", ondelete="SET NULL"),
        nullable=True,
    )
    resolved_quantity: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
    )
    is_confirmed: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )
    resolution_note: Mapped[Optional[str]] = mapped_column(
        String(250),
        nullable=True,
    )

    # Relationships
    ai_capture: Mapped["AICapture"] = relationship(
        "AICapture",
        back_populates="lines",
    )
    matched_product: Mapped[Optional["Product"]] = relationship(
        "Product",
        foreign_keys=[matched_product_id],
    )
    resolved_product: Mapped[Optional["Product"]] = relationship(
        "Product",
        foreign_keys=[resolved_product_id],
    )

