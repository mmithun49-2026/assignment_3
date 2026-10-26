import pytest
from playwright.async_api import async_playwright, expect


PRACTICE_HTML = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Playwright Interaction Practice</title>
    <style>
        body { font-family: Arial, sans-serif; padding: 25px; }
        #menu { display: none; padding: 10px; background: #eee; }
        #menu a { display: block; padding: 5px; }
        #scroll-box { height: 120px; width: 300px; overflow-y: auto;
                      border: 1px solid black; }
        .item { height: 45px; padding: 5px; }
        #context-menu { display: none; padding: 10px; background: #ddd; }
        #hidden-panel { display: none; padding: 10px; }
    </style>
</head>
<body>
    <h1>Interaction Skills Practice</h1>

    <section>
        <h2>1. Hover menu</h2>
        <button id="hover-target">Hover over me</button>
        <div id="menu" role="menu">
            <a href="#reports" role="menuitem">Reports</a>
        </div>
    </section>

    <section>
        <h2>2. Dynamic dropdown</h2>
        <button id="load-options">Load options</button>
        <select id="category" aria-label="Category">
            <option value="">Choose a category</option>
        </select>
    </section>

    <section>
        <h2>3. Right-click</h2>
        <p id="right-click-target">Right-click this harmless paragraph.</p>
        <div id="context-menu" role="menu">
            <span role="menuitem">Practice context menu opened</span>
        </div>
    </section>

    <section>
        <h2>4. Double-click</h2>
        <p id="double-click-target">
            Double-click this text to edit it.
        </p>
        <p id="double-click-result" aria-live="polite">
            Not edited yet
        </p>
    </section>

    <section>
        <h2>5. Incremental scrolling</h2>
        <div id="scroll-box" aria-label="Product list">
            <div class="item">Product 1</div>
            <div class="item">Product 2</div>
            <div class="item">Product 3</div>
        </div>
    </section>

    <section>
        <h2>6. Hidden content</h2>
        <button id="reveal-panel">Show details</button>
        <div id="hidden-panel">
            <p>Additional details are now visible.</p>
            <button id="details-action">View details</button>
        </div>
    </section>

    <script>
        // Hover menu
        const hoverTarget = document.querySelector("#hover-target");
        const menu = document.querySelector("#menu");

        hoverTarget.addEventListener("mouseenter", () => {
            menu.style.display = "block";
        });

        // Dynamic dropdown
        document.querySelector("#load-options").addEventListener(
            "click", () => {
                const dropdown = document.querySelector("#category");
                if (dropdown.options.length === 1) {
                    ["Books", "Computers", "Electronics"].forEach(name => {
                        const option = document.createElement("option");
                        option.value = name.toLowerCase();
                        option.textContent = name;
                        dropdown.appendChild(option);
                    });
                }
            }
        );

        // Right-click context menu
        document.querySelector("#right-click-target").addEventListener(
            "contextmenu", event => {
                event.preventDefault();
                document.querySelector("#context-menu").style.display =
                    "block";
            }
        );

        // Double-click action
        document.querySelector("#double-click-target").addEventListener(
            "dblclick", () => {
                document.querySelector("#double-click-result").textContent =
                    "Double-click verified";
            }
        );

        // Add more items as the user scrolls near the bottom.
        const scrollBox = document.querySelector("#scroll-box");
        let loadedCount = 3;

        scrollBox.addEventListener("scroll", () => {
            if (
                scrollBox.scrollTop + scrollBox.clientHeight >=
                scrollBox.scrollHeight - 5
            ) {
                if (loadedCount < 6) {
                    loadedCount++;
                    const item = document.createElement("div");
                    item.className = "item";
                    item.textContent = "Product " + loadedCount;
                    scrollBox.appendChild(item);
                }
            }
        });

        // Reveal hidden content through normal UI.
        document.querySelector("#reveal-panel").addEventListener(
            "click", () => {
                document.querySelector("#hidden-panel").style.display =
                    "block";
            }
        );
    </script>
</body>
</html>
"""


@pytest.mark.asyncio
async def test_interaction_skills():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        page = await browser.new_page()

        try:
            await page.set_content(PRACTICE_HTML)
            print("Practice page opened:", await page.title())

            # 1. Mouse hover
            await page.locator("#hover-target").hover()

            menu = page.get_by_role("menu").filter(
                has=page.get_by_role("menuitem", name="Reports")
            )
            await expect(menu).to_be_visible()

            print("PASS: Hover menu is visible")

            # 2. Dynamic dropdown
            dropdown = page.get_by_role("combobox", name="Category")

            await expect(
                dropdown.get_by_role("option", name="Books")
            ).to_have_count(0)

            await page.get_by_role(
                "button", name="Load options"
            ).click()

            await expect(
                dropdown.get_by_role("option", name="Books")
            ).to_be_attached()

            await dropdown.select_option(label="Books")
            await expect(dropdown).to_have_value("books")

            print("PASS: Dynamic dropdown loaded and Books selected")

            # 3. Right-click
            right_click_target = page.locator("#right-click-target")
            await right_click_target.click(button="right")

            context_menu = page.get_by_role(
                "menuitem", name="Practice context menu opened"
            )
            await expect(context_menu).to_be_visible()

            print("PASS: Right-click opened the custom context menu")

            # 4. Double-click
            await page.locator("#double-click-target").dblclick()

            await expect(
                page.locator("#double-click-result")
            ).to_have_text("Double-click verified")

            print("PASS: Double-click changed the page content")

            # 5. Incremental scrolling / lazy loading
            scroll_box = page.locator("#scroll-box")
            items = scroll_box.locator(".item")

            initial_count = await items.count()
            assert initial_count == 3

            # Scroll the container in increments and wait for new items.
            for _ in range(3):
                current_count = await items.count()

                await scroll_box.evaluate(
                    "(el) => el.scrollBy(0, 100)"
                )

                try:
                    await expect(items).to_have_count(
                        current_count + 1, timeout=3000
                    )
                    print(
                        "New item loaded. Count:",
                        await items.count()
                    )
                except AssertionError:
                    # The current scroll may not have reached the bottom.
                    await scroll_box.evaluate(
                        "(el) => el.scrollTop = el.scrollHeight"
                    )

                    if await items.count() > current_count:
                        print(
                            "New item loaded after scrolling to bottom."
                        )
                    else:
                        break

            final_count = await items.count()
            assert final_count > initial_count, (
                "No new items appeared after scrolling"
            )

            print(
                f"PASS: Lazy loading verified "
                f"({initial_count} -> {final_count} items)"
            )

            # 6. Hidden content: verify hidden, then reveal normally.
            hidden_panel = page.locator("#hidden-panel")

            await expect(hidden_panel).to_be_hidden()
            assert not await hidden_panel.is_visible()

            await page.get_by_role(
                "button", name="Show details"
            ).click()

            await expect(hidden_panel).to_be_visible()

            # Interact only after the panel is visible.
            await page.get_by_role(
                "button", name="View details"
            ).click()

            print("PASS: Hidden panel revealed through normal UI")

            await page.screenshot(
                path="interaction_skills_result.png",
                full_page=True,
            )

        finally:
            await browser.close()