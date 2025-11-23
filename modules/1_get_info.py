from playwright.sync_api import sync_playwright
from load_django import *
from parser_app.models import MobileGadget
import json
import time


def scrape_specs(page):
    # Scroll so specs load (Brain.com.ua lazy loads them)
    page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
    
    # Wait until specification blocks appear
    page.wait_for_selector(".br-pr-chr-item", timeout=5000)

    specific_s = {}
    spec_blocks = page.query_selector_all(".br-pr-chr-item")

    for block in spec_blocks:
        # Get block title (e.g. "Процесор", "Пам'ять")
        spec_name_el = block.query_selector("h3")
        if not spec_name_el:
            continue

        spec_name = spec_name_el.inner_text().strip()
        specific_s[spec_name] = {}

        # Each specification row is inside div > div
        rows = block.query_selector_all("div > div")

        for row in rows:
            spans = row.query_selector_all("span")
            if len(spans) < 2:
                continue

            key = spans[0].inner_text().strip()

            # Value may contain a link
            link = spans[1].query_selector("a")
            if link:
                value = link.inner_text().strip()
            else:
                value = spans[1].inner_text().strip()

            specific_s[spec_name][key] = value

    return json.dumps(specific_s, indent=4, ensure_ascii=False)

product = {}

with sync_playwright() as p:
    browser = p.chromium.launch(headless=False)
    context = browser.new_context(permissions=[])
    page = context.new_page()

    page.goto("https://brain.com.ua")
    print("sleep")
    time.sleep(30)

    search_str = "Apple iPhone 15 128GB Black"

    # # Search input -- dosnt work
    # page.click("input.quick-search-input")
    # page.keyboard.type(search_str, delay=50)
    # page.keyboard.press("Enter")

    page.evaluate(f"""
                    const el = document.querySelector('input.quick-search-input');
                    el.focus();
                    el.value = '{search_str}';
                    el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    document.querySelector('input[type="submit"]').click();
                """)
    print("sleep2")
    time.sleep(20)

    # Wait for product list
    page.wait_for_selector(".view-grid .br-pp-img-grid a")

    # Click first product
    qrid_elements = page.query_selector_all(".view-grid .br-pp-img-grid a")
    qrid_elements[0].click()

    page.wait_for_selector("h1.main-title")


    # ========================
    # START SCRAPING
    # ========================

    # FULL NAME
    try:
        product["full_name"] = page.inner_text("h1.main-title").strip()
    except:
        product["full_name"] = None

    # COLOR
    try:
        color = page.get_attribute('a[title^="Колір"]', "title")
        product["color"] = color.replace("Колір", "").strip()
    except:
        product["color"] = None

    # MEMORY VOLUME
    try:
        mem = page.get_attribute('a[title^="Вбудована пам\'ять"]', "title")
        product["memory_volume"] = mem.replace("Вбудована пам'ять", "").strip()
    except:
        product["memory_volume"] = None

    # PRICE
    try:
        product["price_use"] = page.inner_text(".price-wrapper span").strip()
    except:
        product["price_use"] = None

    product["price_action"] = None

    # IMAGES
    try:
        image_elements = page.query_selector_all("img.br-main-img")
        product["picture_urls"] = [img.get_attribute("src") for img in image_elements]
    except:
        product["picture_urls"] = []

    # PRODUCT CODE
    try:
        product["product_code"] = page.inner_text("span.br-pr-code-val").strip()
    except:
        product["product_code"] = None

    # REVIEW COUNT
    try:
        product["review_count"] = page.inner_text("a.forbid-click span").strip()
    except:
        product["review_count"] = None

    # SERIES
    product["series"] = None
    try:
        blocks = page.query_selector_all("div.br-pr-chr-item")
        for block in blocks:
            spans = block.query_selector_all("span")
            span_texts = [s.inner_text().strip() for s in spans]

            for i in range(len(span_texts) - 1):
                if span_texts[i] == "Модель":
                    product["series"] = span_texts[i + 1]
                    break
    except:
        pass

    # DISPLAY SIZE
    try:
        ds = page.get_attribute('a[title^="Діагональ екрану"]', "title")
        product["display_size"] = ds.replace("Діагональ екрану", "").strip()
    except:
        product["display_size"] = None

    # RESOLUTION
    try:
        rs = page.get_attribute('a[title^="Роздільна здатність екрану"]', "title")
        product["resolution"] = rs.replace("Роздільна здатність екрану", "").strip()
    except:
        product["resolution"] = None

    product["specifications"] = scrape_specs(page)

    print("\n======= PRODUCT DATA =======")
    for k, v in product.items():
        print(k, ":", v)

    browser.close()

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
        print("Saved new gadget" if created else "Gadget already exists")

    except Exception as e:
        print("Database error:", e)


