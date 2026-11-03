# VyapaarSetu — Assumptions Register & Domain Questions
**Version:** 1.0.0 (Phase 0 Planning)  
**Status:** Open for Stakeholder Review  
**Audience:** Company A Leadership, Jabalpur Operations & Development Team  

---

## 1. Overview
In accordance with our architecture standards, **no business logic or pricing rule is silently decided**. This register documents every domain assumption made during Phase 0 planning, provides our baseline architectural interpretation, and explicitly identifies questions requiring confirmation from Company A.

---

## 2. Domain Assumptions Matrix

| # | Domain Area | Baseline Phase 0 Assumption | Risk / Impact | Status & Decision Needed from Company A |
| :--- | :--- | :--- | :--- | :--- |
| **ASM-01** | **Dealer Price Basis** | In sample data, Glucose Biscuit has `Dealer price ₹8.10` and `case of 96`. We assume ₹8.10 is the **unit/pack dealer price**, meaning 1 case (peti) = `96 × ₹8.10 = ₹777.60`. Similarly, Detergent 1kg has `Dealer price ₹101.50` and `case of 20`, so 1 case = `20 × ₹101.50 = ₹2,030.00`. | If dealer prices are actually already quoted per whole case, order values will be calculated 20x to 96x higher than intended. | **Needs Confirmation:** Are the provided dealer prices (₹8.10, ₹101.50, ₹118.00) per individual consumer unit or per case (peti)? |
| **ASM-02** | **GST Inclusion** | Quoted dealer prices are treated as **GST-Exclusive (Base Taxable Rate)** in B2B wholesale convention. Applicable GST (e.g., 5% on biscuits, 18% on detergents) is calculated on the taxable subtotal and added to the final invoice. | If dealer prices are already GST-inclusive, calculating GST on top creates double taxation on retailer invoices. | **Needs Confirmation:** Do Company A's dealer prices include GST, or is GST levied additionally at checkout? |
| **ASM-03** | **Retailer Pricing Hierarchy** | Pricing resolution follows a strict 2-tier hierarchy: <br>1. If a row exists in `retailer_custom_prices` for the retailer & product within validity dates, use `custom_dealer_price`. <br>2. Else, use the product's `base_dealer_price`. | Tier-based percentage discounts across entire brand categories vs item-level rates. | **Needs Confirmation:** Does Company A use flat price tiers (A/B/C retailers) or individual SKU contract rates? |
| **ASM-04** | **Credit Calculations & Enforcement** | Available Credit = `credit_limit - credit_used - pending_orders_value`. When an order causes available credit to fall below ₹0, the order is **not blocked from submission**, but automatically tagged with `is_credit_hold = true` and `status = 'CREDIT_HOLD'`. Dispatch requires explicit Order Desk manual override. | Hard blocking could lose orders from long-standing kirana stores who pay on delivery (COD). | **Needs Confirmation:** Should retailers over their credit limit be blocked from placing orders, or allowed to submit for desk review? |
| **ASM-05** | **SMS / OTP Provider** | For Phase 0 and local/testing development, we implement an abstract `OTPService` with a deterministic mock provider (`OTP = 459012` for test accounts). For staging/production, we plan integration with an Indian DLT-compliant SMS gateway (e.g. MSG91, Fast2SMS, or Twilio India). | DLT (Distributed Ledger Technology) registration with TRAI is legally required in India for transactional SMS. | **Needs Confirmation:** Does Company A have an existing SMS gateway account / DLT template ID, or should we provision one? |
| **ASM-06** | **Scheme Stacking & Eligibility** | Schemes are evaluated on the ordered case count of qualifying SKUs: <br>- **Scheme A (Biscuits):** For every 10 cases of `SKU-BS-075`, exactly 1 free case is awarded (e.g., 19 cases = 1 free case; 20 cases = 2 free cases). <br>- **Scheme B (Detergent):** If `SKU-DT-1KG` cases >= 5, a flat 3% line discount applies. <br>- **Stacking Rule:** If two promotions apply to the exact same SKU, only the higher-benefit scheme is applied unless explicitly configured as stackable. | Over-discounting if multiple manufacturer schemes compound without control. | **Needs Confirmation:** Can free goods (Scheme A) and cash discounts (Scheme B) ever apply simultaneously to the same line item? |
| **ASM-07** | **Stock Reservation Timing** | Stock is **soft-reserved** when the retailer submits the order (`status = PENDING_DESK_REVIEW`). Hard deduction occurs upon desk approval (`status = APPROVED`). If an order is rejected or cancelled, soft reservations are immediately released. | Race conditions where multiple retailers order the final 10 cases simultaneously before desk review. | **Needs Confirmation:** Should stock be deducted immediately on retailer submission or only when desk staff approves? |
| **ASM-08** | **Tally ERP Integration & Voucher Format** | Import into Company A's Tally is designed as a **Standard Tally-compatible CSV / XML Sales Order export**. Desk staff download this batch file and import it via Tally's *"Import Data > Vouchers"* feature. | Direct ODBC or Tally XML Server (port 9000) integration requires opening firewall ports on Company A's local office LAN. | **Needs Confirmation:** Is manual CSV/XML import into Tally acceptable for Phase 1, or is direct real-time Tally XML port sync required? |

---

## 3. Recommended Action Plan for Phase 1
1. Maintain the documented baseline assumptions in the seed database and calculations.
2. Present this document to Company A's operations manager in Jabalpur during the Phase 0 review checkpoint.
3. Update the `SchemeEngine` and financial configuration immediately upon receiving clarification on ASM-01 and ASM-02.

