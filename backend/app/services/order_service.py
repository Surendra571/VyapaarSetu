import uuid
from datetime import datetime, timezone
from decimal import Decimal
from typing import List, Optional
from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status

from app.models.catalog import Product, Inventory
from app.models.retailer import Retailer
from app.models.order import Order, OrderItem, OrderItemBenefit
from app.models.audit import AuditLog
from app.schemas.order import (
    OrderItemCreate,
    OrderPreviewResponse,
    OrderPreviewLineResponse,
    BenefitDetail,
    OrderDetailResponse,
    OrderItemResponse,
    AuditLogResponse,
    RepeatOrderPreviewResponse,
    RepeatOrderLineDiff,
)
from app.services.pricing_service import PricingService
from app.services.inventory_service import InventoryService
from app.services.scheme_service import SchemeService
from app.services.credit_service import CreditService


class OrderService:
    """Orchestrates order calculation, transactional submission, and lifecycle transitions."""

    @staticmethod
    async def preview_order(
        session: AsyncSession,
        retailer: Retailer,
        items: List[OrderItemCreate],
    ) -> OrderPreviewResponse:
        """Evaluate prices, schemes, stock sufficiency, and credit impact without persisting."""
        evaluated_lines: List[OrderPreviewLineResponse] = []
        subtotal_acc = Decimal("0.00")
        discount_acc = Decimal("0.00")
        total_cases_acc = 0
        has_insufficient = False
        has_any_scheme_conflict = False

        for item in items:
            # Fetch product with inventory
            prod_stmt = (
                select(Product)
                .where(Product.id == item.product_id, Product.is_active == True)
                .options(selectinload(Product.inventory))
            )
            prod_res = await session.execute(prod_stmt)
            product = prod_res.scalar_one_or_none()

            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID '{item.product_id}' was not found or is inactive.",
                )

            # 1. Price resolution (Excl. GST)
            unit_price, price_basis, _ = await PricingService.get_effective_price(
                session, retailer.id, product
            )

            # 2. Stock check
            avail_cases = product.inventory.available_cases if product.inventory else 0
            is_sufficient = avail_cases >= item.quantity_cases
            if not is_sufficient:
                has_insufficient = True

            # 3. Scheme promotion evaluation (supports multi-benefit FREE_GOODS & SLAB_DISCOUNT with conflict detection)
            scheme_res = await SchemeService.evaluate_product_schemes(
                session, product, item.quantity_cases, unit_price
            )

            discount = scheme_res.discount_amount
            scheme_name = scheme_res.scheme_name
            free_qty = scheme_res.free_quantity
            free_name = scheme_res.free_product_name
            free_sku = scheme_res.free_sku_code
            if scheme_res.has_conflict:
                has_any_scheme_conflict = True

            line_benefits = [
                BenefitDetail(
                    scheme_id=b.scheme.id if b.scheme else None,
                    scheme_name=b.scheme.name if b.scheme else "Trade Scheme",
                    benefit_type=b.rule_type_canonical,
                    awarded_product_id=b.free_product_id,
                    awarded_sku_code=b.free_sku_code,
                    awarded_product_name=b.free_product_name,
                    awarded_quantity=b.free_quantity,
                    awarded_uom=b.awarded_uom,
                    discount_amount=b.discount_amount,
                    explanation=b.explanation,
                )
                for b in scheme_res.benefits
            ]

            # 4. Math: Line subtotal (Excl. GST)
            gross = unit_price * Decimal(item.quantity_cases)
            net_line = max(Decimal("0.00"), gross - discount)

            subtotal_acc += net_line
            discount_acc += discount
            total_cases_acc += item.quantity_cases

            evaluated_lines.append(
                OrderPreviewLineResponse(
                    product_id=product.id,
                    sku_code=product.sku_code,
                    product_name=product.name,
                    requested_qty=item.quantity_cases,
                    available_stock=avail_cases,
                    is_stock_sufficient=is_sufficient,
                    unit_price_excl_gst=unit_price,
                    price_basis=price_basis,
                    applied_scheme_name=scheme_name,
                    discount_amount_excl_gst=discount,
                    free_goods_qty=free_qty,
                    free_goods_product_name=free_name,
                    free_goods_sku_code=free_sku,
                    line_subtotal_excl_gst=net_line,
                    scheme_explanation=scheme_res.explanation,
                    has_scheme_conflict=scheme_res.has_conflict,
                    scheme_conflict_note=scheme_res.conflict_note,
                    benefits=line_benefits,
                )
            )

        # 5. Credit standing check
        credit_eval = CreditService.evaluate_credit_standing(retailer, subtotal_acc)

        all_free_goods_list = [
            b
            for line in evaluated_lines
            for b in line.benefits
            if b.awarded_quantity > 0 and b.awarded_product_id
        ]

        return OrderPreviewResponse(
            lines=evaluated_lines,
            total_cases=total_cases_acc,
            subtotal_excl_gst=subtotal_acc,
            total_discount_excl_gst=discount_acc,
            has_insufficient_stock=has_insufficient,
            has_scheme_conflicts=has_any_scheme_conflict,
            credit_check=credit_eval,
            all_free_goods=all_free_goods_list,
        )

    @staticmethod
    async def create_order(
        session: AsyncSession,
        retailer: Retailer,
        items: List[OrderItemCreate],
        delivery_notes: Optional[str] = None,
        client_order_id: Optional[str] = None,
    ) -> Order:
        """Create order inside a database transaction with stock reservation and immutable snapshots."""
        # 0. Idempotency check for offline sync (Phase 5)
        if client_order_id:
            existing = await session.execute(
                select(Order)
                .where(
                    Order.retailer_id == retailer.id,
                    Order.desk_notes.contains(f"[offline_id:{client_order_id}]"),
                )
                .options(
                    selectinload(Order.items).selectinload(OrderItem.benefits),
                    selectinload(Order.audit_logs),
                    selectinload(Order.retailer),
                )
            )
            existing_order = existing.scalar_one_or_none()
            if existing_order:
                return existing_order

        effective_notes = delivery_notes
        if client_order_id:
            prefix = f"[offline_id:{client_order_id}]"
            effective_notes = f"{prefix} {delivery_notes}".strip() if delivery_notes else prefix

        # 1. Preview order first to compute calculations
        preview = await OrderService.preview_order(session, retailer, items)

        # Business Constraint 4: Explicit stockout handling - do not silently create partial orders
        if preview.has_insufficient_stock:
            shortages = [
                f"'{l.product_name}' ({l.sku_code}): requested {l.requested_qty} cases, available {l.available_stock} cases (short by {l.requested_qty - l.available_stock})"
                for l in preview.lines
                if not l.is_stock_sufficient
            ]
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order rejected due to insufficient stock: {'; '.join(shortages)}. VyapaarSetu strictly prevents silent partial orders.",
            )

        # 2. Check credit hold condition
        initial_status = (
            "CREDIT_HOLD"
            if preview.credit_check.will_trigger_credit_hold
            else "PENDING_DESK_APPROVAL"
        )
        hold_reason = (
            preview.credit_check.notice
            if preview.credit_check.will_trigger_credit_hold
            else None
        )

        # 3. Generate unique order number (e.g. VS-20261106-XXXX)
        now_utc = datetime.now(timezone.utc)
        order_number = f"VS-{now_utc.strftime('%Y%m%d')}-{uuid.uuid4().hex[:6].upper()}"

        order = Order(
            id=uuid.uuid4(),
            order_number=order_number,
            retailer_id=retailer.id,
            status=initial_status,
            subtotal_excl_gst=preview.subtotal_excl_gst,
            credit_hold_reason=hold_reason,
            desk_notes=effective_notes,
        )
        session.add(order)

        # 4. Process line items with stock reservation and snapshot persistence
        for line in preview.lines:
            # Atomically reserve stock in inventory
            reserved = await InventoryService.reserve_inventory(
                session, line.product_id, line.requested_qty
            )
            if not reserved:
                await session.rollback()
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Stock for '{line.product_name}' was just reserved by another order. Please refresh cart.",
                )

            # Create immutable snapshot item
            order_item = OrderItem(
                id=uuid.uuid4(),
                order=order,
                product_id=line.product_id,
                ordered_qty=line.requested_qty,
                approved_qty=line.requested_qty,
                uom_type="CASE",
                scheme_discount_amount=line.discount_amount_excl_gst,
                free_item_qty=line.free_goods_qty,
                line_subtotal_excl_gst=line.line_subtotal_excl_gst,
                # Snapshots:
                product_name_snapshot=line.product_name,
                sku_code_snapshot=line.sku_code,
                price_per_unit_snapshot=line.unit_price_excl_gst,
                price_basis_snapshot=line.price_basis,
                scheme_name_snapshot=line.applied_scheme_name,
                free_product_name_snapshot=line.free_goods_product_name,
                free_sku_code_snapshot=line.free_goods_sku_code,
            )
            session.add(order_item)

            # Persist independent multi-benefit line items
            for b in line.benefits:
                benefit_row = OrderItemBenefit(
                    id=uuid.uuid4(),
                    order_item=order_item,
                    scheme_id=b.scheme_id,
                    scheme_name=b.scheme_name,
                    benefit_type=b.benefit_type,
                    awarded_product_id=b.awarded_product_id,
                    awarded_sku_code=b.awarded_sku_code,
                    awarded_product_name=b.awarded_product_name,
                    awarded_quantity=b.awarded_quantity,
                    awarded_uom=b.awarded_uom,
                    discount_amount=b.discount_amount,
                    calculation_details=b.explanation,
                )
                session.add(benefit_row)

        # 5. Update retailer credit ledger
        retailer.outstanding_amount += preview.subtotal_excl_gst
        retailer.available_credit = max(
            Decimal("0.00"), retailer.credit_limit - retailer.outstanding_amount
        )

        # 6. Audit Trail
        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="Order",
            entity_id=str(order.id),
            action="CREATE",
            order=order,
            user_id=retailer.user_id,
            reason=f"Order submitted by retailer. Status: {initial_status}",
            new_values={
                "order_number": order.order_number,
                "status": initial_status,
                "subtotal_excl_gst": str(preview.subtotal_excl_gst),
            },
        )
        session.add(audit)

        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def desk_adjust_line(
        session: AsyncSession,
        order_id: uuid.UUID,
        line_id: uuid.UUID,
        new_approved_qty: int,
        operator_user_id: uuid.UUID,
        reason: str,
    ) -> Order:
        """Order desk adjustment to approved quantity with inventory and scheme benefit recalculation."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .options(
                selectinload(Order.items).selectinload(OrderItem.benefits),
                selectinload(Order.items).selectinload(OrderItem.product),
                selectinload(Order.retailer),
                selectinload(Order.audit_logs),
            )
        )
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        # Prevent line modification on terminal orders
        if order.status in ("APPROVED", "EXPORTED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot modify line items for order '{order.order_number}' in terminal status '{order.status}'.",
            )

        target_line: Optional[OrderItem] = None
        for itm in order.items:
            if itm.id == line_id:
                target_line = itm
                break

        if not target_line:
            raise HTTPException(status_code=404, detail="Order line item not found.")

        old_qty = target_line.approved_qty
        diff = old_qty - new_approved_qty

        # Inventory adjustment
        if diff > 0:
            await InventoryService.release_reserved_inventory(
                session, target_line.product_id, diff
            )
        elif diff < 0:
            reserved = await InventoryService.reserve_inventory(
                session, target_line.product_id, abs(diff)
            )
            if not reserved:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=f"Insufficient inventory available to increase quantity to {new_approved_qty} cases.",
                )

        target_line.approved_qty = new_approved_qty

        # Authoritative scheme re-evaluation on quantity change
        prod_stmt = select(Product).where(Product.id == target_line.product_id)
        prod_res = await session.execute(prod_stmt)
        target_prod = prod_res.scalar_one()

        scheme_res = await SchemeService.evaluate_product_schemes(
            session=session,
            product=target_prod,
            quantity_cases=new_approved_qty,
            unit_price=target_line.price_per_unit_snapshot,
        )

        target_line.scheme_discount_amount = scheme_res.discount_amount
        target_line.free_item_qty = scheme_res.free_quantity
        target_line.scheme_name_snapshot = scheme_res.scheme_name
        target_line.free_product_name_snapshot = scheme_res.free_product_name
        target_line.free_sku_code_snapshot = scheme_res.free_sku_code

        # Re-sync OrderItemBenefit collection
        await session.execute(delete(OrderItemBenefit).where(OrderItemBenefit.order_item_id == target_line.id))

        for b in scheme_res.benefits:
            benefit_row = OrderItemBenefit(
                id=uuid.uuid4(),
                order_item=target_line,
                scheme_id=b.scheme.id if b.scheme else None,
                scheme_name=b.scheme.name if b.scheme else "Trade Scheme",
                benefit_type=b.rule_type_canonical,
                awarded_product_id=b.free_product_id,
                awarded_sku_code=b.free_sku_code,
                awarded_product_name=b.free_product_name,
                awarded_quantity=b.free_quantity,
                awarded_uom=b.awarded_uom,
                discount_amount=b.discount_amount,
                calculation_details=b.explanation,
            )
            session.add(benefit_row)

        # Recalculate line subtotal (Excl. GST)
        new_line_gross = target_line.price_per_unit_snapshot * Decimal(new_approved_qty)
        target_line.line_subtotal_excl_gst = max(Decimal("0.00"), new_line_gross - scheme_res.discount_amount)

        # Recalculate order subtotal and adjust retailer credit exposure
        old_order_subtotal = order.subtotal_excl_gst
        order.subtotal_excl_gst = sum(i.line_subtotal_excl_gst for i in order.items)
        subtotal_diff = order.subtotal_excl_gst - old_order_subtotal

        if order.retailer:
            order.retailer.outstanding_amount = max(Decimal("0.00"), order.retailer.outstanding_amount + subtotal_diff)
            order.retailer.available_credit = max(
                Decimal("0.00"),
                order.retailer.credit_limit - order.retailer.outstanding_amount,
            )

        # Audit log
        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="OrderItem",
            entity_id=str(target_line.id),
            action="UPDATE_QUANTITY",
            order=order,
            user_id=operator_user_id,
            old_values={"approved_qty": old_qty, "subtotal": str(old_order_subtotal)},
            new_values={"approved_qty": new_approved_qty, "subtotal": str(order.subtotal_excl_gst)},
            reason=f"{reason} (Scheme recalculation: {scheme_res.explanation or 'Standard pricing'})",
        )
        session.add(audit)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def approve_order(
        session: AsyncSession,
        order_id: uuid.UUID,
        operator_user_id: uuid.UUID,
        notes: str,
        override_credit: bool = False,
    ) -> Order:
        """Approve order and commit stock deduction."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .options(
                selectinload(Order.items),
                selectinload(Order.retailer),
                selectinload(Order.audit_logs),
            )
        )
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        # Prevent duplicate approval (Negative test #7)
        if order.status in ("APPROVED", "EXPORTED"):
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Order '{order.order_number}' is already approved (current status: '{order.status}'). Duplicate approval rejected.",
            )
        if order.status == "REJECTED":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve order '{order.order_number}' because it was previously rejected.",
            )

        if order.status == "CREDIT_HOLD" and not override_credit:
            raise HTTPException(
                status_code=400,
                detail="Order is on credit hold. Explicit override_credit_hold flag is required to approve.",
            )

        # Commit stock deductions
        for itm in order.items:
            await InventoryService.commit_stock_deduction(
                session, itm.product_id, itm.approved_qty
            )

        order.status = "APPROVED"
        order.approved_by_user_id = operator_user_id
        order.approved_at = datetime.now(timezone.utc)

        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="Order",
            entity_id=str(order.id),
            action="APPROVE",
            order=order,
            user_id=operator_user_id,
            reason=f"Approved by Order Desk. Notes: {notes}. Credit override: {override_credit}",
            new_values={"status": "APPROVED"},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def hold_order(
        session: AsyncSession,
        order_id: uuid.UUID,
        operator_user_id: uuid.UUID,
        reason: str,
    ) -> Order:
        """Place order on administrative or credit hold."""
        stmt = select(Order).where(Order.id == order_id)
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        if order.status in ("APPROVED", "EXPORTED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot place order '{order.order_number}' on hold from status '{order.status}'.",
            )

        order.status = "CREDIT_HOLD"
        order.credit_hold_reason = reason

        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="Order",
            entity_id=str(order.id),
            action="HOLD",
            order=order,
            user_id=operator_user_id,
            reason=reason,
            new_values={"status": "CREDIT_HOLD"},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def reject_order(
        session: AsyncSession,
        order_id: uuid.UUID,
        operator_user_id: uuid.UUID,
        reason: str,
    ) -> Order:
        """Reject order, release reserved inventory, and reverse retailer credit."""
        stmt = (
            select(Order)
            .where(Order.id == order_id)
            .with_for_update()
            .options(
                selectinload(Order.items),
                selectinload(Order.retailer),
                selectinload(Order.audit_logs),
            )
        )
        res = await session.execute(stmt)
        order = res.scalar_one_or_none()

        if not order:
            raise HTTPException(status_code=404, detail="Order not found.")

        if order.status in ("EXPORTED", "REJECTED"):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject order '{order.order_number}' already in status '{order.status}'.",
            )

        # Release reserved inventory
        for itm in order.items:
            await InventoryService.release_reserved_inventory(
                session, itm.product_id, itm.approved_qty
            )

        # Reverse credit exposure
        if order.retailer:
            order.retailer.outstanding_amount = max(
                Decimal("0.00"),
                order.retailer.outstanding_amount - order.subtotal_excl_gst,
            )
            order.retailer.available_credit = (
                order.retailer.credit_limit - order.retailer.outstanding_amount
            )

        order.status = "REJECTED"
        order.rejection_reason = reason

        audit = AuditLog(
            id=uuid.uuid4(),
            entity_name="Order",
            entity_id=str(order.id),
            action="REJECT",
            order=order,
            user_id=operator_user_id,
            reason=reason,
            new_values={"status": "REJECTED"},
        )
        session.add(audit)
        await session.commit()
        await session.refresh(order)
        return order

    @staticmethod
    async def preview_repeat_order(
        session: AsyncSession,
        retailer: Retailer,
        original_order_id: uuid.UUID,
    ) -> RepeatOrderPreviewResponse:
        """
        Loads the historical order, fetches current live pricing, stock, schemes,
        and credit, and returns a detailed diff highlighting any changes.
        """
        stmt = (
            select(Order)
            .where(Order.id == original_order_id, Order.retailer_id == retailer.id)
            .options(
                selectinload(Order.items).selectinload(OrderItem.benefits),
            )
        )
        res = await session.execute(stmt)
        orig_order = res.scalar_one_or_none()
        if not orig_order:
            raise HTTPException(status_code=404, detail="Historical order was not found.")

        diff_lines: List[RepeatOrderLineDiff] = []
        has_price_diff = False
        has_stock_diff = False
        has_scheme_diff = False
        subtotal_acc = Decimal("0.00")
        discount_acc = Decimal("0.00")
        total_cases_acc = 0

        for itm in orig_order.items:
            # Live product catalog status check
            prod_stmt = (
                select(Product)
                .where(Product.id == itm.product_id)
                .options(selectinload(Product.inventory))
            )
            prod_res = await session.execute(prod_stmt)
            prod = prod_res.scalar_one_or_none()

            is_discontinued = prod is None or not prod.is_active
            avail_stock = prod.inventory.available_cases if prod and prod.inventory else 0
            is_stock_ok = avail_stock >= itm.ordered_qty if not is_discontinued else False

            if not is_stock_ok or is_discontinued:
                has_stock_diff = True

            # Live retailer price re-resolution
            if prod:
                cur_price, price_basis, _ = await PricingService.get_effective_price(
                    session, retailer.id, prod
                )
            else:
                cur_price = itm.price_per_unit_snapshot
                price_basis = itm.price_basis_snapshot

            price_changed = cur_price != itm.price_per_unit_snapshot
            if price_changed:
                has_price_diff = True
            p_diff = cur_price - itm.price_per_unit_snapshot

            # Live promotional trade scheme re-evaluation
            cur_scheme_name = None
            cur_discount = Decimal("0.00")
            cur_free_qty = 0
            cur_benefits: List[BenefitDetail] = []
            if prod and not is_discontinued:
                sch_res = await SchemeService.evaluate_product_schemes(
                    session, prod, itm.ordered_qty, cur_price
                )
                cur_scheme_name = sch_res.scheme_name
                cur_discount = sch_res.discount_amount
                cur_free_qty = sch_res.free_quantity
                cur_benefits = [
                    BenefitDetail(
                        scheme_id=b.scheme.id if b.scheme else None,
                        scheme_name=b.scheme.name if b.scheme else "Trade Scheme",
                        benefit_type=b.rule_type_canonical,
                        awarded_product_id=b.free_product_id,
                        awarded_sku_code=b.free_sku_code,
                        awarded_product_name=b.free_product_name,
                        awarded_quantity=b.free_quantity,
                        awarded_uom=b.awarded_uom,
                        discount_amount=b.discount_amount,
                        explanation=b.explanation,
                    )
                    for b in sch_res.benefits
                ]
                if (
                    cur_scheme_name != itm.scheme_name_snapshot
                    or cur_free_qty != itm.free_item_qty
                    or cur_discount != itm.scheme_discount_amount
                ):
                    has_scheme_diff = True

            # Live subtotal calculation
            line_gross = cur_price * Decimal(itm.ordered_qty)
            cur_subtotal = max(Decimal("0.00"), line_gross - cur_discount)

            if not is_discontinued and is_stock_ok:
                subtotal_acc += cur_subtotal
                discount_acc += cur_discount
                total_cases_acc += itm.ordered_qty

            diff_lines.append(
                RepeatOrderLineDiff(
                    product_id=itm.product_id,
                    sku_code=itm.sku_code_snapshot,
                    product_name=itm.product_name_snapshot,
                    original_requested_qty=itm.ordered_qty,
                    current_requested_qty=itm.ordered_qty,
                    historical_unit_price=itm.price_per_unit_snapshot,
                    current_unit_price=cur_price,
                    price_changed=price_changed,
                    price_diff=p_diff,
                    price_basis=price_basis,
                    available_stock=avail_stock,
                    is_stock_sufficient=is_stock_ok,
                    is_discontinued=is_discontinued,
                    current_scheme_name=cur_scheme_name,
                    current_discount_amount=cur_discount,
                    current_free_qty=cur_free_qty,
                    current_line_subtotal=cur_subtotal,
                    benefits=cur_benefits,
                )
            )

        credit_eval = CreditService.evaluate_credit_standing(retailer, subtotal_acc)
        can_proceed = not has_stock_diff and not credit_eval.is_credit_breached

        notices = []
        if has_stock_diff:
            notices.append("Some products from your previous order have stock shortages or have been discontinued.")
        if has_price_diff:
            notices.append("Catalog prices have updated since your previous order.")
        if has_scheme_diff:
            notices.append("Applicable promotional trade schemes have changed.")
        if not notices:
            notices.append("All products from previous order are available at unchanged pricing.")

        return RepeatOrderPreviewResponse(
            original_order_id=orig_order.id,
            original_order_number=orig_order.order_number,
            lines=diff_lines,
            has_price_changes=has_price_diff,
            has_unavailable_items=has_stock_diff,
            has_scheme_changes=has_scheme_diff,
            subtotal_excl_gst=subtotal_acc,
            total_discount_excl_gst=discount_acc,
            total_cases=total_cases_acc,
            credit_check=credit_eval,
            can_proceed=can_proceed,
            revalidation_notice=" ".join(notices),
        )
