import pytest
import logging
from pathlib import Path

import pytest
from playwright.async_api import expect, TimeoutError as PlaywrightTimeoutError

logger = logging.getLogger(__name__)

AMAZON_URL = "https://www.amazon.in/"


@pytest.mark.asyncio
async def test_amazon_shopping_journey(page):
    # 1. Open Amazon India
    response = await page.goto(
        AMAZON_URL,
        wait_until="domcontentloaded",
        timeout=60000,
    )

    assert response is None or response.status < 400
    logger.info("Amazon opened: %s", page.url)

    # 2. Hover over Account & Lists if available
    account_menu = page.locator("#nav-link-accountList")

    if await account_menu.is_visible():
        await account_menu.hover()

        dropdown = page.locator("#nav-al-container")

        try:
            await expect(dropdown).to_be_visible(timeout=5000)
            logger.info("Account hover menu displayed")
        except PlaywrightTimeoutError:
            logger.info("Account hover menu not available")
    else:
        logger.info("Account menu not available")

    # 3. Search for a non-restricted product
    await page.goto(
        "https://www.amazon.in/",
        wait_until="domcontentloaded",
        timeout=60000
    )

    print("Current URL:", page.url)
    print("Page title:", await page.title())

    await page.screenshot(
        path="amazon_debug.png",
        full_page=True
    )

    print("Search boxes found:",
          await page.locator("#twotabsearchtextbox").count())
    search_box = page.locator("#twotabsearchtextbox")
    await expect(search_box).to_be_visible(timeout=15000)

    await search_box.fill("speaker")

    # 4. Handle dynamic suggestions when available
    suggestions = page.locator(
        ".s-suggestion, [role='option']"
    ).filter(has_text="python")

    suggestion_selected = False

    try:
        await suggestions.first.wait_for(
            state="visible",
            timeout=3000,
        )
        await suggestions.first.click()
        suggestion_selected = True
        logger.info("Selected a search suggestion")
    except PlaywrightTimeoutError:
        logger.info("No matching suggestion; submitting search")

    if not suggestion_selected:
        await search_box.press("Enter")

    await page.wait_for_load_state("domcontentloaded")

    # 5. Verify search results
    results = page.locator(
        '[data-component-type="s-search-result"]'
    )

    await expect(results.first).to_be_visible(timeout=30000)

    initial_count = await results.count()
    logger.info("Initial result count: %s", initial_count)

    # Scroll incrementally
    for step in range(3):
        await page.evaluate(
            "() => window.scrollBy(0, window.innerHeight * 0.75)"
        )

        await page.evaluate(
            "() => new Promise(resolve => requestAnimationFrame(resolve))"
        )

        logger.info(
            "Scroll %s: result count = %s",
            step + 1,
            await results.count(),
        )

    final_count = await results.count()

    if final_count <= initial_count:
        logger.info(
            "No additional result cards appeared; "
            "pagination or static results may be used."
        )

    # 6. Open the first product
    product_link = results.first.locator('(//h2[@class="a-size-medium a-spacing-none a-color-base a-text-normal"])[1]').first
    await expect(product_link).to_be_visible()

    search_result_title = (await product_link.inner_text()).strip()
    assert search_result_title, "Search result title is empty"

    await product_link.click()
    await page.wait_for_load_state("domcontentloaded")

    # Validate product title
    product_title = page.locator('//span[@class="a-size-large product-title-word-break"]')
    await expect(product_title).to_be_visible(timeout=30000)

    title_text = (await product_title.inner_text()).strip()
    assert title_text, "Product title is empty"

    logger.info("Product title: %s", title_text)

    # Validate visible price using common Amazon selectors
    price_selectors = [
        "#corePrice_feature_div .a-offscreen",
        ".apexPriceToPay .a-offscreen",
        "#priceblock_ourprice",
        "#priceblock_dealprice",
    ]

    price_text = None

    for selector in price_selectors:
        locator = page.locator(selector).first

        try:
            if await locator.is_visible():
                value = (await locator.inner_text()).strip()

                if value:
                    price_text = value
                    break
        except Exception:
            continue

    assert price_text, (
        "No visible price found. Amazon price markup may have changed."
    )

    logger.info("Product price: %s", price_text)

    # 7. Right-click a harmless product title.
    # Do not select any browser context-menu action.
    await product_title.click(button="right")
    logger.info("Right-click performed")

    # 8. Double-click and 9. hidden-element checks:
    # Use the local practice page if Amazon provides no suitable targets.

    # 10. Save final product details screenshot
    project_root = Path(__file__).resolve().parents[1]
    screenshot_dir = project_root / "artifacts" / "screenshots"
    screenshot_dir.mkdir(parents=True, exist_ok=True)

    screenshot_path = screenshot_dir / "amazon_product_details.png"

    await page.screenshot(
        path=str(screenshot_path),
        full_page=True,
    )

    logger.info("Screenshot saved: %s", screenshot_path)

    # Stop at product details. Never purchase or proceed to payment.
    assert "/dp/" in page.url or "/gp/" in page.url, (
        "Expected an Amazon product details URL"
    )

    logger.info("Test completed without purchasing a product")