import re
import csv
import time
import random
import logging
import asyncio
from datetime import datetime

# Playwright is an optional dependency — only needed for the live scraper
try:
    from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False

log = logging.getLogger(__name__)

BASE_URL = "https://www.amazon.in"

BRAND_QUERIES = {
    "Safari":              "Safari luggage trolley bag",
    "Skybags":             "Skybags trolley bag",
    "American Tourister":  "American Tourister luggage bag",
    "VIP":                 "VIP trolley bag",
    "Aristocrat":          "Aristocrat luggage bag",
    "Nasher Miles":        "Nasher Miles trolley bag",
}


async def human_delay(min_ms=800, max_ms=2500):
    """Async sleep to mimic human browsing pace."""
    await asyncio.sleep(random.uniform(min_ms / 1000, max_ms / 1000))


async def scrape_brand_playwright(brand, query, page_obj, max_pages=3):
    """
    Scrape product listings for a brand using Playwright.

    Args:
        brand:    Brand name
        query:    Amazon search query string
        page_obj: Playwright Page object
        max_pages: Number of search result pages to scrape

    Returns:
        List of product dicts
    """
    products = []
    encoded_query = query.replace(" ", "+")

    for page_num in range(1, max_pages + 1):
        url = f"{BASE_URL}/s?k={encoded_query}&page={page_num}"
        log.info(f"  {brand} — Page {page_num}: {url}")

        try:
            # Navigate with a realistic timeout
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=30000)
            await human_delay(1500, 3000)

            # Wait for search results to appear
            await page_obj.wait_for_selector('[data-component-type="s-search-result"]', timeout=10000)

            # Scroll slowly to trigger lazy-loaded content
            for _ in range(3):
                await page_obj.mouse.wheel(0, 500)
                await human_delay(300, 700)

            # Extract product data via JavaScript evaluation
            cards = await page_obj.query_selector_all('[data-component-type="s-search-result"]')
            log.info(f"  Found {len(cards)} product cards")

            for card in cards:
                try:
                    asin = await card.get_attribute("data-asin") or ""
                    if not asin:
                        continue

                    # Title
                    title_el = await card.query_selector("h2 a span")
                    title = (await title_el.inner_text()).strip() if title_el else ""

                    # Selling price
                    price_el = await card.query_selector(".a-price-whole")
                    price_text = (await price_el.inner_text()).strip() if price_el else ""
                    price = _parse_price(price_text)

                    # MRP (list price)
                    list_price_el = await card.query_selector(".a-text-price .a-offscreen")
                    list_price = _parse_price(
                        await list_price_el.inner_text() if list_price_el else ""
                    )

                    # Rating
                    rating_el = await card.query_selector(".a-icon-alt")
                    rating = None
                    if rating_el:
                        rating_text = await rating_el.inner_text()
                        m = re.match(r"([\d.]+)", rating_text)
                        if m:
                            rating = float(m.group(1))

                    # Review count
                    rev_el = await card.query_selector('[aria-label*="ratings"]')
                    review_count = None
                    if rev_el:
                        rc = (await rev_el.get_attribute("aria-label") or "").replace(",", "")
                        m = re.search(r"(\d+)", rc)
                        if m:
                            review_count = int(m.group(1))

                    # Product URL
                    link_el = await card.query_selector("h2 a")
                    href = await link_el.get_attribute("href") if link_el else ""
                    url_full = BASE_URL + href if href else ""

                    # Discount
                    discount_pct = None
                    if price and list_price and list_price > price:
                        discount_pct = round(((list_price - price) / list_price) * 100, 1)

                    products.append({
                        "product_id": asin,
                        "asin": asin,
                        "brand": brand,
                        "title": title,
                        "price": price,
                        "list_price": list_price,
                        "discount_pct": discount_pct,
                        "rating": rating,
                        "review_count": review_count,
                        "url": url_full,
                        "scraped_at": datetime.now().isoformat(),
                    })

                except Exception as e:
                    log.debug(f"Error parsing card: {e}")

        except PlaywrightTimeout:
            log.warning(f"Timeout on page {page_num} for {brand}")
        except Exception as e:
            log.error(f"Error scraping {brand} page {page_num}: {e}")

    log.info(f"  ✓ {brand}: {len(products)} products collected")
    return products


async def scrape_reviews_playwright(asin, brand, page_obj, max_pages=5):
    """Scrape customer reviews for a product ASIN using Playwright."""
    reviews = []

    for page_num in range(1, max_pages + 1):
        url = f"{BASE_URL}/product-reviews/{asin}?reviewerType=all_reviews&pageNumber={page_num}"

        try:
            await page_obj.goto(url, wait_until="domcontentloaded", timeout=25000)
            await human_delay(1000, 2500)

            review_divs = await page_obj.query_selector_all('[data-hook="review"]')
            if not review_divs:
                break

            for div in review_divs:
                try:
                    # Rating
                    rating_el = await div.query_selector('[data-hook="review-star-rating"] .a-icon-alt')
                    rating = None
                    if rating_el:
                        m = re.match(r"([\d.]+)", await rating_el.inner_text())
                        if m:
                            rating = float(m.group(1))

                    # Title
                    title_el = await div.query_selector('[data-hook="review-title"] span:not(.a-icon-alt)')
                    title = (await title_el.inner_text()).strip() if title_el else ""

                    # Body
                    body_el = await div.query_selector('[data-hook="review-body"] span')
                    body = (await body_el.inner_text()).strip() if body_el else ""

                    # Date
                    date_el = await div.query_selector('[data-hook="review-date"]')
                    date_text = (await date_el.inner_text()).strip() if date_el else ""
                    date_match = re.search(r"(\d+\s+\w+\s+\d{4})", date_text)
                    review_date = date_match.group(1) if date_match else date_text

                    # Verified
                    verified_el = await div.query_selector('[data-hook="avp-badge"]')
                    verified = verified_el is not None

                    reviews.append({
                        "review_id": f"REV-PW-{asin}-{len(reviews)}",
                        "product_id": asin,
                        "brand": brand,
                        "rating": rating,
                        "title": title,
                        "body": body,
                        "date": review_date,
                        "verified_purchase": verified,
                        "helpful_votes": 0,
                    })
                except Exception as e:
                    log.debug(f"Error parsing review: {e}")

        except Exception as e:
            log.error(f"Playwright review error (ASIN={asin}, page={page_num}): {e}")
            break

    return reviews


def _parse_price(text):
    if not text:
        return None
    clean = re.sub(r"[₹,\s]", "", str(text).strip())
    try:
        return float(clean)
    except ValueError:
        return None


async def run_playwright_scraper_async(brands=None, product_pages=2, review_pages=4):
    """Main async entrypoint for the Playwright scraper."""
    if not PLAYWRIGHT_AVAILABLE:
        raise ImportError("Playwright not installed. Run: pip install playwright && playwright install chromium")

    if brands is None:
        brands = list(BRAND_QUERIES.keys())

    all_products = []
    all_reviews = []

    async with async_playwright() as pw:
        # Launch Chromium in headless mode with stealth settings
        browser = await pw.chromium.launch(
            headless=True,
            args=[
                "--no-sandbox",
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ]
        )

        # Create a context with realistic browser fingerprint
        context = await browser.new_context(
            viewport={"width": 1366, "height": 768},
            user_agent=(
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            locale="en-IN",
            timezone_id="Asia/Kolkata",
        )

        # Remove the 'webdriver' navigator property that Amazon checks
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
        """)

        page = await context.new_page()

        for brand in brands:
            query = BRAND_QUERIES.get(brand, brand)
            log.info(f"\n━━━ Scraping {brand} (Playwright) ━━━")

            products = await scrape_brand_playwright(brand, query, page, max_pages=product_pages)
            all_products.extend(products)

            for product in products[:8]:
                asin = product.get("asin")
                if asin:
                    reviews = await scrape_reviews_playwright(asin, brand, page, max_pages=review_pages)
                    all_reviews.extend(reviews)
                    await human_delay(2000, 5000)

        await browser.close()

    # Save results
    import os
    os.makedirs("data/raw", exist_ok=True)

    if all_products:
        with open("data/raw/products_raw.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_products[0].keys())
            writer.writeheader()
            writer.writerows(all_products)

    if all_reviews:
        with open("data/raw/reviews_raw.csv", "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=all_reviews[0].keys())
            writer.writeheader()
            writer.writerows(all_reviews)

    log.info(f"\n✅ Done: {len(all_products)} products, {len(all_reviews)} reviews")


def run_playwright_scraper(**kwargs):
    """Sync wrapper for the async Playwright scraper."""
    asyncio.run(run_playwright_scraper_async(**kwargs))


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    run_playwright_scraper()
