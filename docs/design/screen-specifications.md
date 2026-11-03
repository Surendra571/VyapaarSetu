# VyapaarSetu — Screen Specifications
**Version:** 1.0.0 (Phase 0 Planning)  
**Standard:** Every screen is justified by a direct user task. Zero decorative filler.

---

## 1. Retailer Portal Screens

### SCR-RET-01: Phone OTP Login
- **User Role:** Retailer (Kirana Store Owner)
- **Business Objective:** Authenticate Kirana store owner with zero password friction using their registered mobile number.
- **Main Components:**
  - Company A & VyapaarSetu co-branded header.
  - Indian 10-digit mobile number input (+91 prefix pre-filled).
  - "Send OTP (ओटीपी भेजें)" primary button.
  - 6-digit numeric OTP code input with auto-focus.
  - Resend countdown timer (60s).
- **Primary Action:** Tap "Verify & Login (लॉगिन करें)".
- **Loading State:** Button disables with spinner: "Verifying OTP...".
- **Empty State:** Clean entry form with helpful text: "Enter your registered wholesale mobile number".
- **Error State:**
  - Unregistered number: Inline banner: *"This mobile number is not registered with Company A. Contact distributor office at 0761-XXXXXXX."*
  - Invalid OTP: Red border on OTP input with message *"Incorrect OTP. 2 attempts remaining."*
- **Mobile Behavior:** Full screen, large numeric keypad automatically triggered, sticky submit button above virtual keyboard.
- **Desktop Behavior:** Centered card (max-width 420px) on `#F5F6F2` canvas.

---

### SCR-RET-02: Retailer Catalogue & Scheme Explorer
- **User Role:** Retailer
- **Business Objective:** Browse distributor's 4 FMCG brands, inspect real-time case stock, view retailer-specific wholesale prices, and see active schemes.
- **Main Components:**
  - Top search bar with Hindi voice search / text query.
  - Brand horizontal chip filter (Parle, Wheel, Tata Tea, etc.).
  - Product List Cards:
    - High-res product thumbnail.
    - Product title in English & Devanagari (*"Glucose Biscuit 75g / ग्लूकोज बिस्कुट"*).
    - Case Pack detail: *"Case of 96 packs"*.
    - Retailer Dealer Price: Bold `₹8.10/pack` (or `₹777.60/peti`).
    - MRP comparison & estimated margin.
    - Real-time Stock Badge: `In Stock (340 Peti)` or `Out of Stock (खत्म)`.
    - Active Scheme Banner: `🏷️ Buy 10 Cases, Get 1 Free`.
    - Quick Peti Quantity Stepper (`[-] 0 [+]`).
  - Sticky bottom navigation bar with active cart counter.
- **Primary Action:** Tap `+` stepper to add cases to cart.
- **Loading State:** Skeleton cards matching the product card layout.
- **Empty State:** *"No products found for 'xyz'. Try searching by brand or common name."*
- **Error State:** Network reconnect banner at top: *"Offline. Showing cached catalog. Prices will verify on sync."*
- **Mobile Behavior:** Single-column card list, compact sticky cart strip above bottom bar.
- **Desktop Behavior:** 3-column responsive grid with sticky brand filter sidebar.

---

### SCR-RET-03: Quick AI Order Capture Screen
- **User Role:** Retailer
- **Business Objective:** Enable retailers to paste a WhatsApp order message, type in Hinglish, or dictate an order without manually searching individual items.
- **Main Components:**
  - Large text area with prompt placeholder:
    - *"Paste your WhatsApp order list here... Example: bhaiya 5 peti biscuit chhota, 2 peti washing powder 1 kilo"*
  - "Paste from Clipboard" quick-action button.
  - Audio Voice Dictation button (triggers browser speech-to-text / recording).
  - "Parse Order (आर्डर समझें)" action button.
- **Primary Action:** Tap "Parse Order (आर्डर समझें)".
- **Loading State:** Pulsing state: *"Reading order items and matching with Company A inventory..."*.
- **Empty State:** Examples of colloquial text formats kirana owners regularly send.
- **Error State:** *"Could not detect any items. Please check the text or browse catalog directly."*
- **Mobile Behavior:** Focused viewport; keyboard opens with paste toolbar visible.
- **Desktop Behavior:** Modal overlay or dedicated split-screen view.

---

### SCR-RET-04: AI Order Review & Candidate Correction Screen
- **User Role:** Retailer
- **Business Objective:** Human-in-the-loop verification. Ensure zero hallucinated items or incorrect quantities are ordered before cart entry.
- **Main Components:**
  - Original raw text quote box at top for reference.
  - Parsed Item Cards:
    - Recognized text chip: `"biscuit chhota"`.
    - Matched SKU card: `Glucose Biscuit 75g (Case of 96)`.
    - Confidence Pill: `96% Match`.
    - Editable Peti quantity stepper initialized to parsed count (e.g. 5).
    - Alternative SKU dropdown if confidence is medium (e.g., "Did you mean Glucose 50g?").
    - Out-of-Stock warning banner for items with 0 inventory (e.g., `Tea Leaf 250g`).
  - Unmatched query alert section for unrecognized lines.
  - Sticky bottom action bar: "Confirm & Add All to Cart".
- **Primary Action:** Review items, adjust quantities, and tap "Add to Cart (कार्ट में डालें)".
- **Loading State:** Shimmering item cards while database matching finishes.
- **Empty State:** N/A (redirects back to capture if no text parsed).
- **Error State:** Highlighting unavailable SKUs with an option to remove or substitute.
- **Mobile Behavior:** Vertical stack with high-contrast confirmation buttons.
- **Desktop Behavior:** Two-column layout: Left column = Original message; Right column = Matched item review cards.

---

### SCR-RET-05: Cart & Scheme Breakdown Preview
- **User Role:** Retailer
- **Business Objective:** Transparently show order pricing, applied trade schemes (free goods and percentage discounts), tax summary, and credit validation before final placement.
- **Main Components:**
  - Ordered items list with case count, case price, and line totals.
  - **Applied Schemes Section:**
    - Highlight card: `🎉 Scheme Applied: 1 Free Case of Glucose Biscuit 75g added`.
    - Highlight card: `🎉 Scheme Applied: ₹304.50 (3%) discount on Detergent Powder`.
  - Financial Summary Card:
    - Gross Subtotal (₹).
    - Total Scheme Discount (₹).
    - Estimated Taxes (GST).
    - Final Net Payable Amount (₹).
  - Credit Limit Bar:
    - Shows available credit balance (e.g., *"₹37,550 available of ₹50,000"*).
    - Warning indicator if order total exceeds credit balance.
  - Delivery notes input box.
- **Primary Action:** Tap "Confirm Order (आर्डर भेजें)" (generates unique Idempotency Key).
- **Loading State:** Button disables with: *"Placing order and reserving inventory..."*.
- **Empty State:** Friendly empty cart illustration: *"Your cart is empty. Add products from the catalogue or use AI capture."*
- **Error State:** Credit hold warning modal: *"This order exceeds your credit limit by ₹4,200. Order will require Order Desk approval before dispatch."*
- **Mobile Behavior:** Bottom sheet or dedicated full page with sticky checkout footer.
- **Desktop Behavior:** 60/40 split layout (Cart items on left, sticky pricing summary on right).

---

### SCR-RET-06: Order Success & Tracking Screen
- **User Role:** Retailer
- **Business Objective:** Immediate confirmation with human-readable Order Number, delivery beat schedule, and WhatsApp sharing option.
- **Main Components:**
  - Success icon with Order Number (`VS-2026-1049`).
  - Current status badge: `Received - Under Review (समीक्षा में)`.
  - Itemized order recap with free scheme goods clearly itemized.
  - "Share Order Copy on WhatsApp" button.
  - "Back to Catalogue" button.
- **Primary Action:** Tap "Back to Catalogue" or "Track Order Status".
- **Mobile & Desktop Behavior:** Centered receipt card view.

---

## 2. Order Desk Console Screens (Distributor Staff)

### SCR-DSK-01: Order Desk Staff Login
- **User Role:** Order Desk Operator / Admin
- **Business Objective:** Secure office workstation authentication.
- **Main Components:** Email input, password input, remember me toggle, "Sign in to Order Desk" button.
- **Primary Action:** Click "Sign In".
- **Error State:** "Invalid credentials" error banner.
- **Behavior:** Clean desktop card layout.

---

### SCR-DSK-02: Operations Order Desk Dashboard
- **User Role:** Order Desk Operator
- **Business Objective:** Monitor, filter, and triage incoming retailer orders in real time.
- **Main Components:**
  - Metric Tickers:
    - Pending Review Count (e.g., `14 Orders`).
    - Credit Hold Count (e.g., `3 Orders`).
    - Approved Today (`112 Orders`).
    - Total Value (₹).
  - Segmented Filter Tabs:
    - `All Incoming` | `Pending Review` | `Credit Holds` | `Approved` | `Exported to Tally`.
  - Operational Order Table:
    - Order # & Timestamp.
    - Retailer Store Name, Owner Name & Phone.
    - Route Beat (e.g., *Gorakhpur Beat, Jabalpur*).
    - Total Cases & Net Amount.
    - Input Source Badge (`AI WhatsApp`, `Manual PWA`).
    - Credit Status Badge (`Normal`, `Exceeded`).
    - Quick Action: "Review & Approve".
- **Primary Action:** Click an order row to open the Inspection Panel.
- **Loading State:** Skeleton table rows with pulse animation.
- **Empty State:** "No orders awaiting review for the selected filter."
- **Desktop Behavior:** Full-width responsive data table with sticky header and column sorting.
- **Mobile Behavior:** Responsive fallback to compact list cards (optimized for mobile supervisor view).

---

### SCR-DSK-03: Order Inspection & Inline Correction Panel
- **User Role:** Order Desk Operator
- **Business Objective:** Inspect the raw input message against parsed SKUs, adjust case quantities if stock is tight, review scheme calculations, resolve credit holds, and approve the order.
- **Main Components:**
  - Side-by-side verification pane:
    - **Left Pane:** Original raw message (e.g., WhatsApp text or voice note player).
    - **Right Pane:** Editable order lines.
  - Line Item Editor:
    - SKU, Description, Case Pack.
    - Requested Cases vs Approved Cases input.
    - Applied Scheme details (Free cases, discount %).
    - AI Confidence Score & Match Source tag.
    - "Swap SKU" search modal.
  - Credit Check Widget:
    - Outstanding Ledger Balance vs Credit Limit.
    - If Credit Hold: "Override Credit Hold" checkbox with mandatory reason textarea.
  - Action Bar:
    - "Reject Order" (Red button with reason prompt).
    - "Save Adjustments".
    - "Approve Order & Queue for Tally" (Green button).
- **Primary Action:** Click "Approve Order".
- **Loading State:** Disabled buttons with status: *"Saving audit trail & updating inventory..."*.
- **Desktop Behavior:** Split-screen layout (40% raw input / 60% structured editor).

---

### SCR-DSK-04: Tally Export Batch Console
- **User Role:** Order Desk Operator / Accountant
- **Business Objective:** Generate standard Tally ERP-compatible CSV/XML files for batch import into Company A's local Tally installation.
- **Main Components:**
  - Batch selection filter (Date range, Route Beat, Approved orders not yet exported).
  - Selected orders count & cumulative invoice amount.
  - Table preview of Tally voucher mappings (Party Ledger, Stock Item Name, Quantity, Rate, Free Item Ledger).
  - "Download Tally CSV (Sales Orders)" primary button.
  - "Mark as Exported" confirmation toggle.
- **Primary Action:** Click "Download Tally CSV".
- **Loading State:** "Generating Tally CSV..." progress indicator.
- **Desktop Behavior:** Standard accounting export interface with downloadable file stream.

