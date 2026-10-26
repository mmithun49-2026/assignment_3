from pathlib import Path

import pytest
from playwright.async_api import async_playwright, expect


BASE_URL = "https://demowebshop.tricentis.com/"
SEARCH_TERM = "Computing and Internet"
SCREENSHOT_DIR = Path("artifacts/screenshots")


@pytest.mark.asyncio
async def test_demowebshop_end_to_end():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. Open the home page and verify main navigation.
            await page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            await expect(page.locator(".header")).to_be_visible()
            await expect(page.locator(".header-menu")).to_be_visible()

            print("Step 1 PASS: Home page and main navigation visible")
            print("Page title:", await page.title())

            # 2. Hover over Books and check for a hover-driven submenu.
            books_link = page.locator(
                ".header-menu a[href='/books']"
            )

            if await books_link.count() > 0:
                await books_link.first.hover()
                await page.screenshot(
                    path=str(SCREENSHOT_DIR / "navigation_hover.png"),
                    full_page=True,
                )

                submenu = page.locator(
                    ".header-menu li ul:visible"
                )

                if await submenu.count() > 0:
                    print("Step 2 PASS: Hover menu became visible")
                else:
                    print(
                        "Step 2 LIMITATION: No hover-driven submenu "
                        "appeared for Books."
                    )
            else:
                print(
                    "Step 2 LIMITATION: Books navigation link not found."
                )

            # 3. Open Books and verify the category page.
            if await books_link.count() > 0:
                await books_link.first.click()
            else:
                await page.goto(
                    BASE_URL + "books",
                    wait_until="domcontentloaded",
                )

            await expect(
                page.locator(".page-title")
            ).to_be_visible(timeout=15000)

            await expect(
                page.locator(".product-item").first
            ).to_be_visible(timeout=15000)

            print("Step 3 PASS: Books category opened")

            # Scroll through the product listing and inspect its content.
            products_before_scroll = await page.locator(
                ".product-item"
            ).count()

            await page.evaluate(
                "window.scrollTo(0, document.body.scrollHeight)"
            )

            await page.wait_for_load_state("domcontentloaded")

            products_after_scroll = await page.locator(
                ".product-item"
            ).count()

            print(
                "Products before scroll:",
                products_before_scroll,
            )
            print(
                "Products after scroll:",
                products_after_scroll,
            )

            if products_after_scroll > products_before_scroll:
                print("Step 7: Additional products appeared after scrolling")
            else:
                print(
                    "Step 7: No additional products loaded by scrolling. "
                    "This page may use ordinary pagination instead."
                )

            # Check whether the category has pagination.
            pagination = page.locator(
                ".pager a, .pager span"
            )
            print(
                "Pagination elements found:",
                await pagination.count(),
            )

            # 4. Search using the site's search box.
            search_box = page.locator("#small-searchterms")
            await expect(search_box).to_be_visible(timeout=15000)
            await search_box.fill(SEARCH_TERM)

            # Autocomplete is optional; handle it only if it appears.
            suggestions = page.locator(
                ".ui-autocomplete:visible li, "
                ".ui-autocomplete:visible .ui-menu-item"
            )

            try:
                await expect(suggestions.first).to_be_visible(
                    timeout=2500
                )

                suggestion_texts = await suggestions.all_text_contents()
                print("Autocomplete suggestions:", suggestion_texts)

                matching_suggestion = page.locator(
                    ".ui-autocomplete:visible li, "
                    ".ui-autocomplete:visible .ui-menu-item"
                ).filter(has_text=SEARCH_TERM)

                if await matching_suggestion.count() > 0:
                    await matching_suggestion.first.click()
                    print("Step 4 PASS: Matching suggestion selected")
                else:
                    await search_box.press("Enter")
                    print(
                        "No exact matching suggestion; "
                        "submitted the search text instead."
                    )

            except AssertionError:
                await search_box.press("Enter")
                print(
                    "No visible autocomplete suggestions; "
                    "submitted the search normally."
                )

            await expect(
                page.locator(".product-item").first
            ).to_be_visible(timeout=20000)

            print("Search results URL:", page.url)

            # 5. Find the expected product by visible title.
            matching_product = page.locator(
                ".product-item"
            ).filter(has_text=SEARCH_TERM)

            if await matching_product.count() == 0:
                # If the exact title is not listed, stop rather than
                # silently adding a different product to the cart.
                await page.screenshot(
                    path=str(
                        SCREENSHOT_DIR / "search_results.png"
                    ),
                    full_page=True,
                )
                pytest.fail(
                    f"No search result matched '{SEARCH_TERM}'. "
                    "Inspect artifacts/screenshots/search_results.png."
                )

            product_link = matching_product.first.locator(
                ".product-title a"
            )
            selected_title = (
                await product_link.inner_text()
            ).strip()

            print("Selected product:", selected_title)
            await product_link.click()

            # Verify product details.
            product_heading = page.locator(".product-name h1")
            await expect(product_heading).to_be_visible(
                timeout=15000
            )

            detail_title = (await product_heading.inner_text()).strip()
            assert detail_title, "Product title is empty"

            print("Product detail title:", detail_title)

            price_locator = page.locator(
                ".product-price span, .prices .price"
            ).first

            await expect(price_locator).to_be_visible(timeout=15000)
            price_text = (await price_locator.inner_text()).strip()

            assert price_text, "Product price is empty"
            print("Product price:", price_text)

            # 6. Safe right-click and double-click on the product heading.
            # The heading is not the Add to cart or checkout control.
            await product_heading.click(button="right")
            print("Step 6 PASS: Right-clicked product heading")

            await product_heading.dblclick()
            print("Step 6 PASS: Double-clicked product heading")

            # 8. Check the cart notification while it is hidden, if present.
            notification = page.locator(
                ".bar-notification.success"
            )

            notification_was_hidden = False
            if await notification.count() > 0:
                notification_was_hidden = (
                    not await notification.first.is_visible()
                )

            if notification_was_hidden:
                print(
                    "Step 8: Success notification is initially hidden."
                )
            else:
                print(
                    "Step 8: No initially hidden success notification "
                    "was identified."
                )

            # Add to cart. Use the product page's visible button.
            add_to_cart = page.locator(
                "input.add-to-cart-button, "
                "button.add-to-cart-button"
            ).first

            await expect(add_to_cart).to_be_visible(timeout=15000)
            await expect(add_to_cart).to_be_enabled()
            await add_to_cart.click()

            # Wait for the site's normal success notification.
            await expect(notification.first).to_be_visible(
                timeout=15000
            )

            print("Step 5 PASS: Add-to-cart confirmation appeared")

            if notification_was_hidden:
                print(
                    "Step 8 PASS: Hidden notification became visible "
                    "after the normal Add to cart action."
                )

            notification_text = (
                await notification.first.inner_text()
            ).strip()
            print("Cart confirmation:", notification_text)

            # Verify cart count if the theme exposes one.
            cart_qty = page.locator(
                ".cart-qty"
            ).first

            if await cart_qty.count() > 0:
                cart_count_text = (
                    await cart_qty.inner_text()
                ).strip()
                print("Cart count display:", cart_count_text)

            # Verify the selected product appears in the cart.
            cart_link = page.locator(
                "a[href='/cart']"
            ).first

            if await cart_link.count() > 0:
                await cart_link.click()
            else:
                await page.goto(
                    BASE_URL + "cart",
                    wait_until="domcontentloaded",
                )

            await expect(
                page.locator(".cart")
            ).to_be_visible(timeout=15000)

            cart_product = page.locator(
                ".cart .product a"
            ).filter(has_text=detail_title)

            await expect(cart_product.first).to_be_visible(
                timeout=15000
            )

            print(
                "Step 5 PASS: Selected product verified in the cart"
            )

            await page.screenshot(
                path=str(SCREENSHOT_DIR / "cart_verification.png"),
                full_page=True,
            )

            print(
                "Completed successfully. Stopped at cart verification; "
                "no order was submitted."
            )

        finally:
            await browser.close()