import asyncio
import os
from playwright.async_api import async_playwright

SCREENSHOTS_DIR = r"C:\Users\akkis\.gemini\antigravity\brain\feac37fb-3dbe-4ab2-a122-764b8479e28a\screenshots"
os.makedirs(SCREENSHOTS_DIR, exist_ok=True)

async def capture_screenshots():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.launch(channel="msedge", headless=True)
        except Exception:
            browser = await p.chromium.launch(channel="chrome", headless=True)
        
        # 1. Desktop Context
        desktop = await browser.new_context(viewport={"width": 1280, "height": 850})
        page = await desktop.new_page()

        print("Navigating to login...")
        await page.goto("http://localhost:5173/login")
        await page.wait_for_timeout(1000)

        # Login as retailer
        print("Logging in as Retailer...")
        await page.click("button:has-text('Patel Kirana')")
        await page.wait_for_timeout(300)
        await page.click("button[type='submit']")
        await page.wait_for_url("**/catalogue")
        await page.wait_for_timeout(2000)

        # 1. Catalogue with images (Desktop)
        print("Capturing Catalogue Desktop...")
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_catalogue_desktop.png"), full_page=True)

        # 2. Product Detail Modal (click on first product)
        print("Opening Product Detail Modal...")
        await page.click("h3:has-text('Glucose Biscuit 75g')")
        await page.wait_for_timeout(1000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_product_detail_modal.png"))
        
        # Close modal
        await page.keyboard.press("Escape")
        await page.wait_for_timeout(500)

        # Add items to cart
        print("Adding items to cart...")
        # Add Glucose Biscuit
        add_btns = page.locator("button:has-text('Add to Cart')")
        if await add_btns.count() > 0:
            await add_btns.first.click()
            await page.wait_for_timeout(1000)

        # 3. Cart with product thumbnails
        print("Navigating to cart...")
        await page.goto("http://localhost:5173/cart")
        await page.wait_for_timeout(2000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_cart_desktop.png"), full_page=True)

        # 4. Order Confirmation with thumbnails
        print("Navigating to confirmation...")
        checkout_btn = page.locator("button:has-text('Review & Confirm Order'), button:has-text('Proceed to Order Review')")
        if await checkout_btn.count() > 0:
            await checkout_btn.first.click()
            await page.wait_for_timeout(2000)
            await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "04_order_confirmation_desktop.png"), full_page=True)

        # 5. AI Capture with product images & SKU alternatives
        print("Navigating to AI Capture...")
        await page.goto("http://localhost:5173/ai-capture")
        await page.wait_for_timeout(1000)
        # Click sample message
        sample_pill = page.locator("button:has-text('bhaiya 5 peti biscuit chhota')")
        if await sample_pill.count() > 0:
            await sample_pill.first.click()
            await page.wait_for_timeout(500)
        extract_btn = page.locator("button:has-text('Extract Products with AI'), button:has-text('Extract Order Lines')")
        if await extract_btn.count() > 0:
            await extract_btn.first.click()
            await page.wait_for_timeout(3000)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_ai_capture_desktop.png"), full_page=True)

        # 6. Order History
        print("Navigating to Order History...")
        await page.goto("http://localhost:5173/orders")
        await page.wait_for_timeout(1500)
        await page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "06_order_history_desktop.png"), full_page=True)

        # 7. Mobile Contexts
        print("Capturing Mobile Screens...")
        mobile = await browser.new_context(viewport={"width": 390, "height": 844}, is_mobile=True)
        mob_page = await mobile.new_page()
        await mob_page.goto("http://localhost:5173/login")
        await mob_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "01_login_mobile.png"), full_page=True)
        await mob_page.click("button:has-text('Patel Kirana')")
        await mob_page.wait_for_timeout(300)
        await mob_page.click("button[type='submit']")
        await mob_page.wait_for_url("**/catalogue")
        await mob_page.wait_for_timeout(2000)
        await mob_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "02_catalogue_mobile.png"), full_page=True)

        # Mobile Cart
        await mob_page.goto("http://localhost:5173/cart")
        await mob_page.wait_for_timeout(1500)
        await mob_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "03_cart_mobile.png"), full_page=True)

        # Mobile AI Capture
        await mob_page.goto("http://localhost:5173/ai-capture")
        await mob_page.wait_for_timeout(1500)
        await mob_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "05_ai_capture_mobile.png"), full_page=True)

        # 8. Order Desk Desktop
        print("Logging into Order Desk...")
        desk_page = await desktop.new_page()
        await desk_page.goto("http://localhost:5173/login")
        await desk_page.click("button:has-text('Order Desk Supervisor')")
        await desk_page.wait_for_timeout(300)
        await desk_page.click("button[type='submit']")
        await desk_page.wait_for_url("**/desk*")
        await desk_page.wait_for_timeout(2000)
        await desk_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "07_order_desk_desktop.png"), full_page=True)

        # 9. Tally Export Desktop
        print("Navigating to Tally Export...")
        await desk_page.goto("http://localhost:5173/desk/export")
        await desk_page.wait_for_timeout(1500)
        await desk_page.screenshot(path=os.path.join(SCREENSHOTS_DIR, "08_tally_export_desktop.png"), full_page=True)

        await browser.close()
        print("All screenshots captured successfully!")

if __name__ == "__main__":
    asyncio.run(capture_screenshots())
