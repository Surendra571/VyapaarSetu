import csv
import io
import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import Optional, List, Tuple, Any
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.user import User
from app.models.order import Order, OrderItem
from app.models.audit import ExportBatch, AuditLog


def sanitize_csv_cell(value: Any) -> Any:
    """
    Prevents CSV Formula Injection (CWE-1236 / Excel Macro Injection).
    If a text field begins with dangerous formula prefixes ('=', '+', '-', '@', '\t', '\r'),
    prepend a single quote (') to force spreadsheet processors to interpret it as literal text.
    """
    if value is None:
        return ""
    s = str(value)
    if s and s[0] in ("=", "+", "-", "@", "\t", "\r"):
        return f"'{s}"
    return s


class ExportService:
    """Tally-compatible CSV export service formatting approved dispatch batches."""

    @staticmethod
    async def create_tally_export_batch(
        session: AsyncSession,
        operator: User,
        order_ids: Optional[List[uuid.UUID]] = None,
    ) -> Tuple[ExportBatch, str]:
        """
        Export approved orders to Tally-compatible CSV and tag orders as EXPORTED.
        Returns: (ExportBatch, csv_content_string)
        """
        stmt = (
            select(Order)
            .where(Order.status == "APPROVED")
            .options(
                selectinload(Order.items).selectinload(OrderItem.benefits),
                selectinload(Order.retailer),
            )
            .order_by(Order.created_at)
        )
        if order_ids:
            stmt = stmt.where(Order.id.in_(order_ids))

        res = await session.execute(stmt)
        orders = res.scalars().all()

        if not orders:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No approved orders available for Tally export.",
            )

        now_utc = datetime.now(timezone.utc)
        batch_number = f"EXP-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"
        file_name = f"Tally_Orders_Batch_{batch_number}.csv"

        # Construct CSV in-memory
        output = io.StringIO()
        writer = csv.writer(output, lineterminator="\r\n")

        # Tally standard columnar headers
        headers = [
            "Voucher Number",
            "Voucher Date",
            "Party Name",
            "Party Code",
            "Item SKU",
            "Item Name",
            "Billed Qty (Cases)",
            "Free Qty (Cases)",
            "Rate Per Unit (Excl. GST)",
            "Price Basis",
            "Scheme Name",
            "Scheme Discount Amount",
            "Line Amount (Excl. GST)",
            "Desk Approval Remarks",
        ]
        writer.writerow(headers)

        batch_total = Decimal("0.00")

        for ord in orders:
            v_date = ord.created_at.strftime("%Y-%m-%d") if ord.created_at else now_utc.strftime("%Y-%m-%d")
            party_name = ord.retailer.store_name if ord.retailer else "Unknown Retailer"
            party_code = ord.retailer.retailer_code if ord.retailer else "N/A"

            for itm in ord.items:
                free_benefits = [
                    b for b in (itm.benefits or [])
                    if b.benefit_type == "FREE_GOODS" and b.awarded_quantity > 0
                ]

                # 1. Output purchased item line
                purchased_row = [
                    ord.order_number,
                    v_date,
                    party_name,
                    party_code,
                    itm.sku_code_snapshot,
                    itm.product_name_snapshot,
                    itm.approved_qty,
                    0 if free_benefits else itm.free_item_qty,
                    f"{itm.price_per_unit_snapshot:.2f}",
                    itm.price_basis_snapshot,
                    itm.scheme_name_snapshot or "None",
                    f"{itm.scheme_discount_amount:.2f}",
                    f"{itm.line_subtotal_excl_gst:.2f}",
                    ord.desk_notes or "",
                ]
                writer.writerow([sanitize_csv_cell(c) for c in purchased_row])
                batch_total += itm.line_subtotal_excl_gst

                # 2. Output distinct free goods benefits separately (never merged)
                for b in free_benefits:
                    free_row = [
                        ord.order_number,
                        v_date,
                        party_name,
                        party_code,
                        b.awarded_sku_code or itm.sku_code_snapshot,
                        b.awarded_product_name or "Promotional Free Item",
                        0,  # Billed Qty = 0
                        b.awarded_quantity,  # Free Qty
                        "0.00",
                        itm.price_basis_snapshot,
                        b.scheme_name,
                        "0.00",
                        "0.00",
                        f"Free promotional benefit for purchase of {itm.sku_code_snapshot}",
                    ]
                    writer.writerow([sanitize_csv_cell(c) for c in free_row])

            # Transition order status
            ord.status = "EXPORTED"

        csv_content = output.getvalue()

        # Save ExportBatch record
        batch = ExportBatch(
            id=uuid.uuid4(),
            batch_number=batch_number,
            exported_by_user_id=operator.id,
            order_count=len(orders),
            total_amount_excl_gst=batch_total,
            file_name=file_name,
            file_format="TALLY_CSV",
            csv_payload=csv_content,
        )
        session.add(batch)

        for ord in orders:
            ord.export_batch = batch

        # Audit trail
        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="ExportBatch",
            entity_id=str(batch.id),
            action="TALLY_EXPORT",
            user=operator,
            reason=f"Generated Tally CSV export batch with {len(orders)} orders. Total ₹{batch_total:.2f} (Excl. GST).",
            new_values={
                "batch_number": batch_number,
                "order_count": len(orders),
                "total_amount_excl_gst": str(batch_total),
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(batch)
        return (batch, csv_content)

