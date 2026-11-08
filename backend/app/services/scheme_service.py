import uuid
from datetime import datetime, timezone
from decimal import Decimal, ROUND_HALF_UP
from typing import Optional, List, Dict, Any, Tuple
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.models.catalog import Product
from app.models.pricing import Scheme, SchemeRule


class EvaluatedBenefit:
    """Detailed evaluation result of a single scheme rule."""

    def __init__(
        self,
        scheme: Scheme,
        rule: SchemeRule,
        discount_amount: Decimal,
        free_quantity: int,
        free_product_id: Optional[uuid.UUID],
        free_product_name: Optional[str],
        explanation: str,
        rule_type_canonical: str,
        free_sku_code: Optional[str] = None,
        awarded_uom: str = "CASE",
    ):
        self.scheme = scheme
        self.rule = rule
        self.discount_amount = discount_amount
        self.free_quantity = free_quantity
        self.free_product_id = free_product_id
        self.free_product_name = free_product_name
        self.free_sku_code = free_sku_code
        self.explanation = explanation
        self.rule_type_canonical = rule_type_canonical
        self.awarded_uom = awarded_uom

    @property
    def estimated_value(self) -> Decimal:
        """Heuristic monetary evaluation for comparative ranking."""
        # Value of discount + nominal valuation for free cases
        return self.discount_amount + Decimal(str(self.free_quantity * 50))


class SchemeEvaluationResult:
    """Final aggregated promotion decision for an order line item."""

    def __init__(
        self,
        scheme_name: Optional[str] = None,
        scheme_id: Optional[uuid.UUID] = None,
        discount_amount: Decimal = Decimal("0.00"),
        free_quantity: int = 0,
        free_product_id: Optional[uuid.UUID] = None,
        free_product_name: Optional[str] = None,
        free_sku_code: Optional[str] = None,
        explanation: Optional[str] = None,
        has_conflict: bool = False,
        conflict_note: Optional[str] = None,
        is_stacked: bool = False,
        applied_rules_snapshot: Optional[List[Dict[str, Any]]] = None,
        benefits: Optional[List[EvaluatedBenefit]] = None,
    ):
        self.scheme_name = scheme_name
        self.scheme_id = scheme_id
        self.discount_amount = discount_amount
        self.free_quantity = free_quantity
        self.free_product_id = free_product_id
        self.free_product_name = free_product_name
        self.free_sku_code = free_sku_code
        self.explanation = explanation
        self.has_conflict = has_conflict
        self.conflict_note = conflict_note
        self.is_stacked = is_stacked
        self.applied_rules_snapshot = applied_rules_snapshot or []
        self.benefits = benefits or []

    @property
    def free_goods_benefits(self) -> List[Dict[str, Any]]:
        """
        Independent list of all awarded free-good SKUs.
        Guarantees that distinct SKUs are never merged or conflated.
        """
        return [
            {
                "product_id": b.free_product_id,
                "sku_code": b.free_sku_code,
                "product_name": b.free_product_name,
                "quantity_cases": b.free_quantity,
                "uom": b.awarded_uom,
                "scheme_id": b.scheme.id,
                "scheme_name": b.scheme.name,
                "explanation": b.explanation,
            }
            for b in self.benefits
            if b.free_quantity > 0 and b.free_product_id
        ]



class SchemeService:
    """
    Trade promotion evaluation engine implementing:
    - FREE_GOODS (Buy X cases, get Y free)
    - SLAB_DISCOUNT (Buy at least X cases, get Y% discount)
    - Configurable stacking policy & conflict detection
    - Date validity checking and detailed human explanations
    """

    @staticmethod
    def is_scheme_valid(scheme: Scheme, now_utc: Optional[datetime] = None) -> bool:
        """Check if scheme is active and within effective dates."""
        if not scheme.is_active:
            return False

        current = now_utc or datetime.now(timezone.utc)
        if scheme.valid_from and current < scheme.valid_from:
            return False
        if scheme.valid_to and current > scheme.valid_to:
            return False
        return True

    @staticmethod
    def calculate_rule_benefit(
        scheme: Scheme,
        rule: SchemeRule,
        product: Product,
        quantity_cases: int,
        unit_price: Decimal,
    ) -> Optional[EvaluatedBenefit]:
        """
        Evaluate a single rule against requested quantity.
        Returns EvaluatedBenefit if qualified, None otherwise.
        """
        if quantity_cases < rule.min_quantity:
            return None

        # Normalize rule types
        # FREE_GOODS or BUY_X_GET_Y_FREE
        # SLAB_DISCOUNT or PERCENTAGE_DISCOUNT / FLAT_DISCOUNT
        r_type = (rule.rule_type or "").upper()

        if r_type in ("FREE_GOODS", "BUY_X_GET_Y_FREE"):
            free_per_step = rule.free_quantity or 1
            multiplier = quantity_cases // rule.min_quantity
            total_free = multiplier * free_per_step

            free_pid = rule.free_product_id or product.id
            free_name = rule.free_product.name if rule.free_product else product.name
            free_sku = rule.free_product.sku_code if rule.free_product else product.sku_code

            explanation = (
                f"Qualified for '{scheme.name}': Buy {rule.min_quantity} cases get {free_per_step} free. "
                f"Ordered {quantity_cases} cases -> {total_free} free case(s) of '{free_name}' ({free_sku}) awarded."
            )

            return EvaluatedBenefit(
                scheme=scheme,
                rule=rule,
                discount_amount=Decimal("0.00"),
                free_quantity=total_free,
                free_product_id=free_pid,
                free_product_name=free_name,
                free_sku_code=free_sku,
                explanation=explanation,
                rule_type_canonical="FREE_GOODS",
                awarded_uom="CASE",
            )

        elif r_type in ("SLAB_DISCOUNT", "PERCENTAGE_DISCOUNT"):
            pct = rule.discount_percentage or Decimal("0.00")
            line_gross = unit_price * Decimal(quantity_cases)
            discount = (line_gross * (pct / Decimal("100.00"))).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)

            explanation = (
                f"Qualified for '{scheme.name}': Buy at least {rule.min_quantity} cases get {pct}% slab discount. "
                f"Ordered {quantity_cases} cases -> ₹{discount:.2f} discount applied."
            )

            return EvaluatedBenefit(
                scheme=scheme,
                rule=rule,
                discount_amount=discount,
                free_quantity=0,
                free_product_id=None,
                free_product_name=None,
                explanation=explanation,
                rule_type_canonical="SLAB_DISCOUNT",
            )

        elif r_type == "FLAT_DISCOUNT":
            discount = rule.discount_amount or Decimal("0.00")
            explanation = (
                f"Qualified for '{scheme.name}': Flat ₹{discount:.2f} discount on ordering at least {rule.min_quantity} cases."
            )
            return EvaluatedBenefit(
                scheme=scheme,
                rule=rule,
                discount_amount=discount,
                free_quantity=0,
                free_product_id=None,
                free_product_name=None,
                explanation=explanation,
                rule_type_canonical="FLAT_DISCOUNT",
            )

        return None

    @classmethod
    async def evaluate_product_schemes(
        cls,
        session: AsyncSession,
        product: Product,
        quantity_cases: int,
        unit_price: Decimal,
        override_stacking: Optional[bool] = None,
        override_policy: Optional[str] = None,
    ) -> SchemeEvaluationResult:
        """
        Evaluate all active schemes for a product.
        Enforces configurable stacking policy:
        - If stacking is NOT allowed (default):
          - If multiple schemes qualify and policy is FLAG_CONFLICT_FOR_REVIEW:
            Flags conflict for review instead of silently picking or stacking.
          - If policy is BEST_VALUE:
            Selects the single highest benefit.
        - If stacking IS allowed:
          Combines qualifying benefits.
        """
        allow_stacking = (
            override_stacking
            if override_stacking is not None
            else settings.ALLOW_SCHEME_STACKING
        )
        stacking_policy = (
            override_policy
            if override_policy is not None
            else settings.SCHEME_STACKING_POLICY
        )

        now_utc = datetime.now(timezone.utc)

        # Query all active schemes for this product
        stmt = (
            select(Scheme)
            .join(SchemeRule, SchemeRule.scheme_id == Scheme.id)
            .where(
                Scheme.is_active == True,
                SchemeRule.qualifying_product_id == product.id,
            )
            .options(
                selectinload(Scheme.rules).selectinload(SchemeRule.free_product)
            )
            .order_by(Scheme.priority)
        )
        result = await session.execute(stmt)
        schemes = result.scalars().unique().all()

        qualifying_benefits: List[EvaluatedBenefit] = []

        for sch in schemes:
            if not cls.is_scheme_valid(sch, now_utc):
                continue

            for rule in sch.rules:
                if rule.qualifying_product_id != product.id:
                    continue

                benefit = cls.calculate_rule_benefit(
                    scheme=sch,
                    rule=rule,
                    product=product,
                    quantity_cases=quantity_cases,
                    unit_price=unit_price,
                )
                if benefit:
                    qualifying_benefits.append(benefit)

        # Case 0: No qualifying schemes
        if not qualifying_benefits:
            return SchemeEvaluationResult()

        # Case 1: Exactly one qualifying rule
        if len(qualifying_benefits) == 1:
            b = qualifying_benefits[0]
            return SchemeEvaluationResult(
                scheme_name=b.scheme.name,
                scheme_id=b.scheme.id,
                discount_amount=b.discount_amount,
                free_quantity=b.free_quantity,
                free_product_id=b.free_product_id,
                free_product_name=b.free_product_name,
                free_sku_code=b.free_sku_code,
                explanation=b.explanation,
                has_conflict=False,
                is_stacked=False,
                benefits=[b],
                applied_rules_snapshot=[
                    {
                        "scheme_code": b.scheme.scheme_code,
                        "rule_type": b.rule_type_canonical,
                        "min_qty": b.rule.min_quantity,
                        "discount_amount": str(b.discount_amount),
                        "free_qty": b.free_quantity,
                        "free_sku_code": b.free_sku_code,
                    }
                ],
            )

        # Case 2: Multiple qualifying rules!
        distinct_schemes = {b.scheme.id for b in qualifying_benefits}

        # Subcase 2A: All benefits originate from the SAME scheme (single scheme, multiple benefits)
        if len(distinct_schemes) == 1:
            sch = qualifying_benefits[0].scheme
            total_discount = sum((b.discount_amount for b in qualifying_benefits), Decimal("0.00"))
            total_free = sum(b.free_quantity for b in qualifying_benefits)
            explanations = " + ".join(b.explanation for b in qualifying_benefits)
            primary_free = next((b for b in qualifying_benefits if b.free_quantity > 0), qualifying_benefits[0])

            return SchemeEvaluationResult(
                scheme_name=sch.name,
                scheme_id=sch.id,
                discount_amount=total_discount,
                free_quantity=total_free,
                free_product_id=primary_free.free_product_id,
                free_product_name=primary_free.free_product_name,
                free_sku_code=primary_free.free_sku_code,
                explanation=explanations,
                has_conflict=False,
                is_stacked=False,
                benefits=qualifying_benefits,
                applied_rules_snapshot=[
                    {
                        "scheme_code": b.scheme.scheme_code,
                        "rule_type": b.rule_type_canonical,
                        "discount_amount": str(b.discount_amount),
                        "free_qty": b.free_quantity,
                        "free_sku_code": b.free_sku_code,
                    }
                    for b in qualifying_benefits
                ],
            )

        # Subcase 2B: Multiple distinct schemes qualify — evaluate stacking configuration
        if allow_stacking:
            total_discount = sum((b.discount_amount for b in qualifying_benefits), Decimal("0.00"))
            total_free = sum(b.free_quantity for b in qualifying_benefits)
            names = ", ".join(dict.fromkeys(b.scheme.name for b in qualifying_benefits))
            explanations = " | ".join(b.explanation for b in qualifying_benefits)
            primary_free = next((b for b in qualifying_benefits if b.free_quantity > 0), qualifying_benefits[0])

            return SchemeEvaluationResult(
                scheme_name=f"Stacked Schemes: {names}",
                scheme_id=qualifying_benefits[0].scheme.id,
                discount_amount=total_discount,
                free_quantity=total_free,
                free_product_id=primary_free.free_product_id,
                free_product_name=primary_free.free_product_name,
                free_sku_code=primary_free.free_sku_code,
                explanation=f"Stacked promotions: {explanations}",
                has_conflict=False,
                is_stacked=True,
                benefits=qualifying_benefits,
                applied_rules_snapshot=[
                    {
                        "scheme_code": b.scheme.scheme_code,
                        "rule_type": b.rule_type_canonical,
                        "discount_amount": str(b.discount_amount),
                        "free_qty": b.free_quantity,
                        "free_sku_code": b.free_sku_code,
                    }
                    for b in qualifying_benefits
                ],
            )

        # Non-stackable competing schemes: Check conflict policy
        if stacking_policy == "FLAG_CONFLICT_FOR_REVIEW":
            scheme_titles = [f"'{b.scheme.name}'" for b in qualifying_benefits]
            conflict_msg = (
                f"Scheme conflict detected: {len(qualifying_benefits)} qualifying schemes ({', '.join(scheme_titles)}) "
                f"compete for SKU '{product.sku_code}'. Stacking is disabled and policy is unresolved. "
                f"Flagged for Order Desk manual review to prevent unauthorized double discounting."
            )
            top_scheme = sorted(qualifying_benefits, key=lambda b: (b.scheme.priority, -b.estimated_value))[0]

            return SchemeEvaluationResult(
                scheme_name=top_scheme.scheme.name,
                scheme_id=top_scheme.scheme.id,
                discount_amount=top_scheme.discount_amount,
                free_quantity=top_scheme.free_quantity,
                free_product_id=top_scheme.free_product_id,
                free_product_name=top_scheme.free_product_name,
                free_sku_code=top_scheme.free_sku_code,
                explanation=top_scheme.explanation,
                has_conflict=True,
                conflict_note=conflict_msg,
                is_stacked=False,
                benefits=[top_scheme],
                applied_rules_snapshot=[
                    {
                        "scheme_code": b.scheme.scheme_code,
                        "rule_type": b.rule_type_canonical,
                        "discount_amount": str(b.discount_amount),
                        "free_qty": b.free_quantity,
                        "free_sku_code": b.free_sku_code,
                        "is_conflicting": True,
                    }
                    for b in qualifying_benefits
                ],
            )

        elif stacking_policy == "BEST_VALUE":
            best = sorted(qualifying_benefits, key=lambda b: (b.estimated_value, -b.scheme.priority), reverse=True)[0]
            explanation = (
                f"{best.explanation} (Selected as best value among {len(qualifying_benefits)} non-stackable offers)."
            )
            return SchemeEvaluationResult(
                scheme_name=best.scheme.name,
                scheme_id=best.scheme.id,
                discount_amount=best.discount_amount,
                free_quantity=best.free_quantity,
                free_product_id=best.free_product_id,
                free_product_name=best.free_product_name,
                free_sku_code=best.free_sku_code,
                explanation=explanation,
                has_conflict=False,
                is_stacked=False,
                benefits=[best],
                applied_rules_snapshot=[
                    {
                        "scheme_code": best.scheme.scheme_code,
                        "rule_type": best.rule_type_canonical,
                        "discount_amount": str(best.discount_amount),
                        "free_qty": best.free_quantity,
                        "free_sku_code": best.free_sku_code,
                    }
                ],
            )

        # Fallback to conservative single offer
        top = qualifying_benefits[0]
        return SchemeEvaluationResult(
            scheme_name=top.scheme.name,
            scheme_id=top.scheme.id,
            discount_amount=top.discount_amount,
            free_quantity=top.free_quantity,
            free_product_id=top.free_product_id,
            free_product_name=top.free_product_name,
            explanation=top.explanation,
            has_conflict=True,
            conflict_note="Stacking policy undefined.",
        )
