from playwright.sync_api import sync_playwright
from load_django import *
from parser_app.models import MobileGadget
import json
import time


def get_text(page, xpath):
    try:
        el = page.query_selector(f"xpath={xpath}")
        if not el:
            return None
        return el.inner_text().strip()
    except:
        return None


def get_product(page, search_str):
    product = {}


    # OPEN SITE
    page.goto("https://brain.com.ua", wait_until="domcontentloaded")

    # SEARCH PRODUCT — Selenium-style logic in Playwright
    search_boxes = page.locator("xpath=//input[@class='quick-search-input']")
    count = search_boxes.count()

    print("Found inputs:", count)

    for i in range(count):
        box = search_boxes.nth(i)
        print(f"Trying input #{i+1}")

        try:
            # Try to fill
            box.fill(search_str)

            # Try pressing Enter
            box.press("Enter")

            print(f"Input #{i+1} worked!")
            break

        except Exception as e:
            print(f"Input #{i+1} FAILED → {type(e).__name__}")
            continue

    page.wait_for_selector("xpath=//div[contains(@class,'br-pp-img-grid')]", timeout=10000)

    # Click first product
    page.query_selector("xpath=(//div[contains(@class,'br-pp-img-grid')])[1]").click()

    page.wait_for_selector("xpath=//h1[contains(@class,'main-title')]", timeout=10000)

    # PRODUCT BASIC INFO (XPATH)

    product["full_name"] = get_text(page, "//h1[contains(@class,'main-title')]")
    product["color"] = get_text(page, "//a[contains(@title,'Колір')]")
    product["memory_volume"] = get_text(page, "//a[contains(@title,'Вбудована пам')]")
    product["price_use"] = get_text(page, "//div[contains(@class,'main-price-block')]")
    product["price_action"] = None

    # IMAGES
    try:
        imgs = page.query_selector_all("xpath=//img[contains(@class,'br-main-img')]")
        product["picture_urls"] = [img.get_attribute("src") for img in imgs]
    except:
        product["picture_urls"] = []

    # OTHER FIELDS
    product["product_code"] = get_text(page, "//span[contains(@class,'br-pr-code-val')]")
    product["review_count"] = get_text(page, "//a[contains(@class,'forbid-click')]/span")
    product["series"] = get_text(page, "//span[text()='Модель']/following-sibling::span")
    product["display_size"] = get_text(page, "//span[text()='Діагональ екрану']/following-sibling::span")
    product["resolution"] = get_text(page, "//span[text()='Роздільна здатність екрану']/following-sibling::span")

    # SCROLL TO LOAD SPECS
    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
    page.wait_for_selector("xpath=//div[contains(@class,'br-pr-chr-item')]", timeout=10000)

    # SPECIFICATIONS (XPATH ONLY)
    specs = {}

    spec_blocks = page.query_selector_all("xpath=//div[contains(@class,'br-pr-chr-item')]")

    for block in spec_blocks:
        # Get block title
        h3 = block.query_selector("xpath=.//h3")
        if not h3:
            continue
        spec_name = h3.inner_text().strip()
        specs[spec_name] = {}

        # Rows inside block
        rows = block.query_selector_all("xpath=.//div/div")

        for row in rows:
            spans = row.query_selector_all("xpath=.//span")
            if len(spans) < 2:
                continue

            key = spans[0].inner_text().strip()

            link = spans[1].query_selector("xpath=.//a")
            if link:
                value = link.inner_text().strip()
            else:
                value = spans[1].inner_text().strip()

            specs[spec_name][key] = value

    product["specifications"] = json.dumps(specs, indent=4, ensure_ascii=False)

    return product


# MAIN SCRIPT
with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(permissions=[])
    page = context.new_page()

    search_str = "Apple iPhone 15 128GB Black"
    product = get_product(page, search_str)

    browser.close()

# PRINT RESULTS
for key, val in product.items():
    print(f"{key}: {val}")

# SAVE TO DB
try:
    gadget, created = MobileGadget.objects.get_or_create(
        full_name=product['full_name'],
        color=product['color'],
        memory_volume=product['memory_volume'],
        price_use=product['price_use'],
        price_action=product['price_action'],
        pic_links=product['picture_urls'],
        product_code=product["product_code"],
        review_count=product['review_count'],
        series=product['series'],
        display_size=product['display_size'],
        resolution=product['resolution'],
        specifications=product['specifications']
    )
    print("New gadget saved." if created else "Gadget already exists.")
except Exception as e:
    print("Database error:", e)
