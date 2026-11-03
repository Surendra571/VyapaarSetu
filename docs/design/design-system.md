# VyapaarSetu — Design System & Visual Tokens
**Version:** 1.0.0 (Phase 0 Planning)  
**Philosophy:** Purpose-built, high-contrast, task-justified UI for Kirana retailers and distributor operations. No decorative fluff, no generic dashboard cards, zero unnecessary gradients.

---

## 1. Brand Color Tokens

| Token Name | Hex Code | Tailwind Class | Semantic Usage & Contrast Compliance |
| :--- | :--- | :--- | :--- |
| `primary` | `#123B35` | `bg-brand-primary` / `text-brand-primary` | Deep Forest Teal. Main header, top app bar, desk sidebar, primary brand identity. Passes WCAG AAA (contrast ratio 10.4:1 against white). |
| `action` | `#187A65` | `bg-brand-action` / `text-brand-action` | Vibrant Jade. Primary interactive elements: "Confirm Order", "Approve", "Add to Cart", Stepper increment buttons. High visibility outdoors. |
| `background`| `#F5F6F2` | `bg-brand-background` | Warm Off-White. Main screen background. Reduces glare in outdoor kirana sunlight compared to pure `#FFFFFF`. |
| `accent` | `#E8A33B` | `bg-brand-accent` / `text-brand-accent` | Warm Mustard / Marigold. Promotional scheme tags ("Buy 10 Get 1 Free"), active discounts, pending alerts. Distinct from error reds. |
| `text-main` | `#27343B` | `text-brand-text` | Deep Slate. All primary headings, product titles, numerical prices. High legibility. |
| `border` | `#E2E7E1` | `border-brand-border` | Muted Sage Border. Form inputs, table separators, card outlines. Subtle yet crisp structure. |

### Semantic State Colors
- **Success:** `#1F8752` (Orders approved, in-stock badge, verified match).
- **Warning / Credit Hold:** `#D97706` (Orders on credit hold, low inventory threshold).
- **Destructive / Error:** `#DC2626` (Out of stock pill, rejection action, validation failure).
- **Surface White:** `#FFFFFF` (Card surfaces, input field fills, modal dialogs).

---

## 2. Typography Specification

### Primary & Devanagari Pairings
- **Latin Font:** `Inter` (sans-serif) — Clean, legible numbers, tabular numerals for currency.
- **Devanagari Font:** `Noto Sans Devanagari` — Native Indian script readability for Hindi product titles (e.g., *"ग्लूकोज बिस्कुट 75 ग्राम"*), scheme banners, and regional terminology.

### Type Scale & Hierarchy
```css
/* Display / App Headings */
--text-2xl: 1.5rem (24px) / line-height: 1.3 / font-weight: 700 (Desktop Page Titles)
--text-xl:  1.25rem (20px) / line-height: 1.35 / font-weight: 600 (Mobile Screen Headers)
--text-lg:  1.125rem (18px) / line-height: 1.4 / font-weight: 600 (Product Card Titles, Total Amount)
--text-base: 1.0rem (16px) / line-height: 1.5 / font-weight: 500 (Primary Buttons, Input Fields)
--text-sm:  0.875rem (14px) / line-height: 1.4 / font-weight: 400 & 500 (Scheme Badges, Secondary Meta)
--text-xs:  0.75rem (12px) / line-height: 1.3 / font-weight: 500 (Confidence Scores, Timestamps, HSN)
```

---

## 3. 8px Spacing System

All padding, margins, gaps, and component sizes follow a strict 8px harmonic grid:

| Token | Dimension | Applied Use Case |
| :--- | :--- | :--- |
| `space-1` | `4px` | Micro spacing (pill badge padding, icon-to-label inline gaps) |
| `space-2` | `8px` | Standard compact padding (input inner vertical padding, chip gaps) |
| `space-3` | `12px` | Intermediate gap (between product image and detail stack) |
| `space-4` | `16px` | Standard base margin (card padding, mobile screen horizontal gutter) |
| `space-6` | `24px` | Section separators, spacing between major order review blocks |
| `space-8` | `32px` | Modal dialog interior padding, desktop column gutters |
| `space-12` | `48px` | **Minimum mobile touch target height** for all interactive buttons |
| `space-16` | `64px` | Bottom navigation bar clearance height |

---

## 4. Core Component Specifications

### 4.1 Primary Action Button
- **Height:** Exactly `48px` on mobile, `40px` on desktop.
- **Background:** `bg-[#187A65]` with active feedback `active:bg-[#123B35]`.
- **Text:** White (`#FFFFFF`), `font-medium`, `text-base`.
- **Radius:** `rounded-lg` (8px radius).
- **Elevation:** Zero dropshadows (`shadow-none`). Clean solid fill for clarity.

### 4.2 Quantity Stepper (Peti / Case Counter)
Kirana shopkeepers need fast, tactile case adjustments:
- Left decrement button: `48x48px` touch target, icon `Minus`.
- Center count display: `min-w-[48px]`, bold tabular numerals, font-size `18px`.
- Right increment button: `48x48px` touch target, icon `Plus`.
- Direct manual input on number tap to allow rapid entry of large quantities (e.g. 50 cases).

### 4.3 AI Match Confidence Pill
Displays the certainty of the server-side SKU match:
- **High Confidence (> 90%):** `bg-emerald-50 text-emerald-800 border-emerald-200` ("Matched • 96%")
- **Medium Confidence (75% - 89%):** `bg-amber-50 text-amber-800 border-amber-200` ("Review Match • 81%")
- **Low / Ambiguous (< 75%):** `bg-rose-50 text-rose-800 border-rose-200` ("Select SKU")

### 4.4 Promotional Scheme Badge
- **Background:** Warm mustard tint `bg-[#FFF7ED]`.
- **Border:** `border-[#E8A33B]`.
- **Text:** `text-[#9A3412]`, bold, with tag icon.
- **Example:** `🏷️ Buy 10 Get 1 Free (स्कीम)`

### 4.5 Retailer Bottom Navigation Bar
- Fixed bottom bar on mobile screens.
- Total height `64px` (`border-t border-[#E2E7E1] bg-white`).
- 4 primary destinations:
  1. **Catalogue (सामान सूची)** — Home icon
  2. **Quick AI Order (आर्डर लिखें)** — Sparkles / Mic icon (highlighted)
  3. **Cart (कार्ट)** — Shopping Bag with live item count badge
  4. **My Orders (पिछले आर्डर)** — Receipt icon

---

## 5. Accessibility & Ergonomics

1. **Touch Ergonomics:** All buttons, counter tabs, and form toggles maintain a minimum interactive touch area of `48px x 48px` to accommodate users with dusty or wet hands in Kirana storefront conditions.
2. **High-Contrast Text:** Text elements strictly maintain a minimum contrast ratio of 4.5:1 against their backgrounds under WCAG AA specifications.
3. **Multi-lingual Context:** Crucial unit labels (Peti / Cases / Dozen) and scheme benefits display parallel Hindi text to eliminate misinterpretation.

