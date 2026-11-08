from decimal import Decimal
from typing import Tuple
from app.models.retailer import Retailer
from app.schemas.order import CreditCheckSummary


class CreditService:
    """Manages retailer credit ledger invariants and configurable credit-hold policy."""

    @staticmethod
    def evaluate_credit_standing(
        retailer: Retailer,
        proposed_order_amount_excl_gst: Decimal,
    ) -> CreditCheckSummary:
        """
        Evaluate if a proposed order subtotal breaches the retailer's available credit.
        Invariance: available_credit = credit_limit - outstanding_amount.
        """
        limit = retailer.credit_limit
        outstanding = retailer.outstanding_amount
        available = max(Decimal("0.00"), limit - outstanding)

        # Check breach: current outstanding + proposed subtotal > limit
        total_exposure = outstanding + proposed_order_amount_excl_gst
        is_breached = total_exposure > limit
        will_hold = retailer.is_credit_locked or is_breached

        if retailer.is_credit_locked:
            notice = "Account is administratively locked for credit review."
        elif is_breached:
            excess = total_exposure - limit
            notice = f"Order exceeds available credit limit by ₹{excess:.2f}. Will require Order Desk approval."
        else:
            notice = "Credit standing healthy. Order eligible for normal processing."

        return CreditCheckSummary(
            credit_limit=limit,
            current_outstanding=outstanding,
            available_credit=available,
            proposed_order_amount=proposed_order_amount_excl_gst,
            is_credit_breached=is_breached,
            will_trigger_credit_hold=will_hold,
            notice=notice,
        )

