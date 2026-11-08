import uuid
from decimal import Decimal
from typing import Optional, List, Dict, Any, TYPE_CHECKING
from sqlalchemy import ForeignKey, Integer, Numeric, String, Text, JSON, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.user import User
    from app.models.order import Order


class ExportBatch(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Batches of approved orders exported to Tally-compatible CSV."""

    __tablename__ = "export_batches"

    batch_number: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        index=True,
        nullable=False,
    )
    exported_by_user_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="RESTRICT"),
        nullable=False,
        index=True,
    )
    order_count: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )
    total_amount_excl_gst: Mapped[Decimal] = mapped_column(
        Numeric(12, 2),
        nullable=False,
    )
    file_name: Mapped[str] = mapped_column(
        String(250),
        nullable=False,
    )
    file_format: Mapped[str] = mapped_column(
        String(50),
        default="TALLY_CSV",
        nullable=False,
    )
    csv_payload: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
    )

    # Relationships
    exported_by_user: Mapped["User"] = relationship(
        "User",
        back_populates="export_batches",
    )
    orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="export_batch",
    )


class AuditLog(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """Immutable audit trail for desk adjustments, credit overrides, and orders."""

    __tablename__ = "audit_logs"

    entity_name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    entity_id: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
        index=True,
    )
    action: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,  # CREATE | UPDATE | APPROVE | REJECT | CREDIT_OVERRIDE | TALLY_EXPORT
    )
    order_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("orders.id", ondelete="CASCADE"),
        nullable=True,
        index=True,
    )
    user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    old_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    new_values: Mapped[Optional[Dict[str, Any]]] = mapped_column(
        JSON,
        nullable=True,
    )
    reason: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
    )

    # Relationships
    order: Mapped[Optional["Order"]] = relationship(
        "Order",
        back_populates="audit_logs",
    )
    user: Mapped[Optional["User"]] = relationship(
        "User",
        back_populates="audit_logs",
    )

    __table_args__ = (
        Index("idx_audit_entity_lookup", "entity_name", "entity_id"),
    )

