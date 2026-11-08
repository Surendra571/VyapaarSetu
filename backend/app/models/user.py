import uuid
from typing import Optional, List, TYPE_CHECKING
from sqlalchemy import Boolean, String
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.models.base import Base, UUIDPrimaryKeyMixin, TimestampMixin

if TYPE_CHECKING:
    from app.models.retailer import Retailer
    from app.models.order import Order
    from app.models.audit import ExportBatch, AuditLog


class User(Base, UUIDPrimaryKeyMixin, TimestampMixin):
    """System user representing retailers, desk operators, or administrators."""

    __tablename__ = "users"

    phone_number: Mapped[str] = mapped_column(
        String(20),
        unique=True,
        index=True,
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(
        String(150),
        nullable=False,
    )
    role: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True,
        default="ROLE_RETAILER",  # ROLE_RETAILER | ROLE_ORDER_DESK
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
    )

    # Relationships
    retailers: Mapped[List["Retailer"]] = relationship(
        "Retailer",
        back_populates="user",
        cascade="all, delete-orphan",
    )
    approved_orders: Mapped[List["Order"]] = relationship(
        "Order",
        back_populates="approved_by_user",
        foreign_keys="Order.approved_by_user_id",
    )
    export_batches: Mapped[List["ExportBatch"]] = relationship(
        "ExportBatch",
        back_populates="exported_by_user",
    )
    audit_logs: Mapped[List["AuditLog"]] = relationship(
        "AuditLog",
        back_populates="user",
    )

