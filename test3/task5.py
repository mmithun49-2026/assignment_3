import pytest
from playwright.async_api import expect


@pytest.mark.asyncio
async def test_home_page(page, log_step):
    log_step("Opening the practice website")

    await page.goto(
        "https://demowebshop.tricentis.com/",
        wait_until="domcontentloaded",
        timeout=60000,
    )

    log_step(f"Page opened; URL: {page.url}")

    log_step("Checking that the site header is visible")
    await expect(page.locator(".header")).to_be_visible()

    log_step("Checking the page title")
    assert "Demo Web Shop" in await page.title()

    log_step("Home page checks passed")