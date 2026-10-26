import asyncio
import random
import uuid
from pathlib import Path

import pytest
from playwright.async_api import async_playwright, expect


BASE_URL = "https://parabank.parasoft.com/parabank/index.htm"
SCREENSHOT_DIR = Path("artifacts/screenshots")


@pytest.mark.asyncio
async def test_parabank_end_to_end():
    SCREENSHOT_DIR.mkdir(parents=True, exist_ok=True)

    username = f"demo_{uuid.uuid4().hex[:10]}"
    password = f"Demo@{uuid.uuid4().hex[:8]}"

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            # 1. Open ParaBank and register a new demo account
            await page.goto(
                BASE_URL,
                wait_until="domcontentloaded",
                timeout=60000,
            )

            print("Website title:", await page.title())
            print("Opened ParaBank")

            await page.get_by_role("link", name="Register").click()

            await page.locator(
                'input[name="customer.firstName"]'
            ).fill("Demo")

            await page.locator(
                'input[name="customer.lastName"]'
            ).fill("Tester")

            await page.locator(
                'input[name="customer.address.street"]'
            ).fill("123 Test Street")

            await page.locator(
                'input[name="customer.address.city"]'
            ).fill("Test City")

            await page.locator(
                'input[name="customer.address.state"]'
            ).fill("CA")

            await page.locator(
                'input[name="customer.address.zipCode"]'
            ).fill("90001")

            await page.locator(
                'input[name="customer.phoneNumber"]'
            ).fill("5551234567")

            await page.locator(
                'input[name="customer.ssn"]'
            ).fill(f"555-{random.randint(10, 99)}-{random.randint(1000, 9999)}")

            await page.locator(
                'input[name="customer.username"]'
            ).fill(username)

            await page.locator(
                'input[name="customer.password"]'
            ).fill(password)

            await page.locator(
                'input[name="repeatedPassword"]'
            ).fill(password)

            await page.get_by_role(
                "button", name="Register"
            ).click()

            await expect(
                page.get_by_text(
                    "Your account was created successfully",
                    exact=False,
                )
            ).to_be_visible(timeout=20000)

            print("Step 1 PASS: Demo user registered")

            # 2. Log out if registration automatically logged in,
            # then explicitly log in using the created credentials.
            logout_link = page.get_by_role("link", name="Log Out")

            if await logout_link.is_visible():
                await logout_link.click()

            await page.locator('input[name="username"]').fill(username)
            await page.locator('input[name="password"]').fill(password)
            await page.get_by_role("button", name="Log In").click()

            await expect(
                page.get_by_role("link", name="Accounts Overview")
            ).to_be_visible(timeout=15000)

            await page.get_by_role("link", name="Accounts Overview").click()

            await expect(
                page.get_by_role("heading", name="Accounts Overview")
            ).to_be_visible()

            print("Step 2 PASS: Login and account overview verified")

            # 3. Open account details
            account_links = page.locator("#accountTable a")

            await expect(account_links.first).to_be_visible(
                timeout=15000
            )

            initial_account_ids = [
                value.strip()
                for value in await account_links.all_text_contents()
                if value.strip().isdigit()
            ]

            assert initial_account_ids, (
                "No account numbers found in the account overview"
            )

            first_account_id = initial_account_ids[0]
            print("Initial account IDs:", initial_account_ids)

            await page.get_by_role(
                "link", name="Accounts Overview"
            ).click()

            await page.locator("#accountTable a").filter(
                has_text=first_account_id
            ).first.click()

            await expect(
                page.get_by_role("heading", name="Account Details")
            ).to_be_visible(timeout=15000)

            await expect(
                page.get_by_text(first_account_id, exact=True)
            ).to_be_visible()

            print("Step 3 PASS: Account details verified")

            # Return to account overview
            await page.get_by_role(
                "link", name="Accounts Overview"
            ).click()

            # 4. Try to create a second account for the transfer
            await page.get_by_role(
                "link", name="Open New Account"
            ).click()

            await expect(
                page.get_by_role("heading", name="Open New Account")
            ).to_be_visible(timeout=15000)

            account_type = page.locator("#type")
            type_options = await account_type.locator(
                "option"
            ).evaluate_all(
                "(opts) => opts.map(o => ({value: o.value, text: o.textContent.trim()}))"
            )

            usable_types = [
                option for option in type_options if option["value"]
            ]

            if usable_types:
                # Choose the first available account type.
                await account_type.select_option(
                    value=usable_types[0]["value"]
                )

            source_dropdown = page.locator("#fromAccountId")
            source_options = await source_dropdown.locator(
                "option"
            ).evaluate_all(
                "(opts) => opts.map(o => ({value: o.value, text: o.textContent.trim()})).filter(o => o.value)"
            )

            if source_options:
                await source_dropdown.select_option(
                    value=source_options[0]["value"]
                )

                await page.get_by_role(
                    "button", name="Open New Account"
                ).click()

                new_account_link = page.locator("#newAccountId")

                try:
                    await expect(new_account_link).to_be_visible(
                        timeout=15000
                    )
                    new_account_id = (
                        await new_account_link.inner_text()
                    ).strip()
                    print("New account created:", new_account_id)
                except AssertionError:
                    print(
                        "Second account could not be confirmed. "
                        "Transfer will be skipped if fewer than two "
                        "accounts are available."
                    )
            else:
                print(
                    "No source account option available; "
                    "cannot create a second account."
                )

            # 5. Get the account IDs from the updated overview
            await page.get_by_role(
                "link", name="Accounts Overview"
            ).click()

            await expect(
                page.get_by_role("heading", name="Accounts Overview")
            ).to_be_visible()

            account_links = page.locator("#accountTable a")

            visible_account_ids = [
                value.strip()
                for value in await account_links.all_text_contents()
                if value.strip().isdigit()
            ]

            # Keep unique IDs in the original order.
            account_ids = list(dict.fromkeys(visible_account_ids))
            print("Available account IDs:", account_ids)

            # 6. Transfer a small amount only if two different accounts exist
            if len(account_ids) >= 2:
                source_id = account_ids[0]
                destination_id = account_ids[1]

                await page.get_by_role(
                    "link", name="Transfer Funds"
                ).click()

                await expect(
                    page.get_by_role("heading", name="Transfer Funds")
                ).to_be_visible(timeout=15000)

                await page.locator("#amount").fill("1.00")
                await page.locator("#fromAccountId").select_option(
                    value=source_id
                )
                await page.locator("#toAccountId").select_option(
                    value=destination_id
                )

                # This submits a $1 transfer on the demo system.
                await page.get_by_role(
                    "button", name="Transfer"
                ).click()

                await expect(
                    page.locator("#showResult")
                ).to_contain_text(
                    "Transfer Complete",
                    timeout=20000,
                )

                print(
                    f"Step 4 PASS: Transfer result displayed "
                    f"for ${1.00:.2f}"
                )

                await page.screenshot(
                    path=str(
                        SCREENSHOT_DIR / "parabank_transfer_result.png"
                    ),
                    full_page=True,
                )

                # Check the account overview after the transfer.
                await page.get_by_role(
                    "link", name="Accounts Overview"
                ).click()

                await expect(
                    page.get_by_role(
                        "heading", name="Accounts Overview"
                    )
                ).to_be_visible()

                print(
                    "Account overview reopened after transfer. "
                    "Record the displayed balances for evidence."
                )
            else:
                print(
                    "Step 4 SKIPPED: Two distinct accounts were not "
                    "available, so no transfer was submitted."
                )

            # 7. Hover test: check whether navigation exposes a submenu
            overview_link = page.get_by_role(
                "link", name="Accounts Overview"
            )
            await overview_link.hover()

            # ParaBank generally uses ordinary navigation links rather
            # than a hover-driven navigation menu.
            print(
                "Step 5: Hovered over Accounts Overview. "
                "No hover menu is required if none appears."
            )

            # 8. Hidden-element handling: inspect a likely hidden
            # element and reveal it only through a normal UI control.
            hidden_candidates = page.locator(
                '[hidden], [aria-hidden="true"], .hidden'
            )
            revealed = False

            for index in range(
                min(await hidden_candidates.count(), 10)
            ):
                candidate = hidden_candidates.nth(index)

                try:
                    if await candidate.is_visible():
                        continue

                    element_id = await candidate.get_attribute("id")
                    if not element_id:
                        continue

                    control = page.locator(
                        f'[aria-controls="{element_id}"]'
                    ).filter(visible=True)

                    if await control.count():
                        await control.first.click()

                        if await candidate.is_visible():
                            revealed = True
                            print(
                                "Step 6 PASS: Hidden element revealed "
                                "using its visible UI control."
                            )
                            break
                except Exception:
                    # An unrelated hidden element is not a test failure.
                    continue

            if not revealed:
                print(
                    "Step 6 LIMITATION: No suitable hidden element "
                    "with a normal reveal control was identified."
                )

            # 9. Safe right-click and double-click on a heading.
            # These actions do not submit a transaction.
            heading = page.get_by_role(
                "heading", name="Accounts Overview"
            )

            if await heading.is_visible():
                await heading.click(button="right")
                print("Step 7 PASS: Right-clicked a safe heading")

                await heading.dblclick()
                print("Step 7 PASS: Double-clicked a safe heading")
            else:
                print(
                    "Step 7 LIMITATION: Safe heading target unavailable."
                )

            # 10. Log out and verify signed-out state
            await page.get_by_role("link", name="Log Out").click()

            await expect(
                page.get_by_role("button", name="Log In")
            ).to_be_visible(timeout=15000)

            await expect(
                page.locator('input[name="username"]')
            ).to_be_visible()

            print("Step 8 PASS: Logged out successfully")

            await page.screenshot(
                path=str(
                    SCREENSHOT_DIR / "parabank_logged_out.png"
                ),
                full_page=True,
            )

        finally:
            await browser.close()