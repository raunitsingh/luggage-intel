import os
import re
import csv
import time
import random
import logging
from datetime import datetime

import requests
from bs4 import BeautifulSoup

# ── Logging setup ─────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
log = logging.getLogger(__name__)

# ── Constants ─────────────────────────────────────────────────────────────────
BASE_URL = "https://www.amazon.in"

# These search terms map directly to Amazon India search results
BRAND_QUERIES = {
    "Safari":              "Safari+luggage+trolley+bag",
    "Skybags":             "Skybags+trolley+bag",
    "American Tourister":  "American+Tourister+luggage+bag",
    "VIP":                 "VIP+trolley+bag",
    "Aristocrat":          "Aristocrat+luggage+bag",
    "Nasher Miles":        "Nasher+Miles+trolley+bag",
}

# Rotate through realistic browser User-Agents to avoid detection
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
]


def get_headers():
    """Return realistic request headers with a rotating User-Agent."""
    return {
        "User-Agent": random.choice(USER_AGENTS),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "en-IN,en;q=0.9,hi;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
        "TE": "Trailers",
    }


def polite_sleep(min_sec=2.0, max_sec=5.0):
    """Sleep for a random interval to mimic human browsing pace."""
    delay = random.uniform(min_sec, max_sec)
    time.sleep(delay)


class AmazonScraper:
    """
    Scrapes product listings and customer reviews from Amazon India.

    Example:
        scraper = AmazonScraper()
        products = scraper.search_brand("Safari", pages=3)
        reviews  = scraper.get_reviews(product_asin, max_pages=5)
    """

    def __init__(self, proxy=None):
        self.session = requests.Session()
        self.proxies = {"http": proxy, "https": proxy} if proxy else None
        self.scraped_asins = set()  # Avoid re-scraping the same product

    def _get(self, url, retries=3):
        """
        Make a GET request with retry logic and error handling.
        Returns a BeautifulSoup object or None on failure.
        """
        for attempt in range(retries):
            try:
                polite_sleep(1.5, 4.0)
                response = self.session.get(
                    url,
                    headers=get_headers(),
                    proxies=self.proxies,
                    timeout=15,
                )

                # Amazon sometimes returns a CAPTCHA page instead of content
                if "captcha" in response.text.lower() or response.status_code == 503:
                    log.warning(f"CAPTCHA or 503 detected on attempt {attempt+1}. Waiting longer...")
                    time.sleep(random.uniform(15, 30))
                    continue

                if response.status_code == 200:
                    return BeautifulSoup(response.content, "lxml")

                log.warning(f"HTTP {response.status_code} on {url}")

            except requests.RequestException as e:
                log.error(f"Request failed (attempt {attempt+1}): {e}")
                time.sleep(5)

        return None  # All retries exhausted

    def _parse_price(self, text):
        """Extract a float price from strings like '₹4,299' or '4,299.00'."""
        if not text:
            return None
        clean = re.sub(r"[₹,\s]", "", text.strip())
        try:
            return float(clean)
        except ValueError:
            return None

    def search_brand(self, brand, pages=3):
        """
        Search Amazon India for a brand and collect product metadata.

        Args:
            brand:  Brand name key from BRAND_QUERIES
            pages:  Number of result pages to scrape (each has ~20 products)

        Returns:
            List of product dicts
        """
        query = BRAND_QUERIES.get(brand, brand.replace(" ", "+"))
        products = []

        for page in range(1, pages + 1):
            url = f"{BASE_URL}/s?k={query}&page={page}&ref=sr_pg_{page}"
            log.info(f"  Searching {brand} — page {page}: {url}")

            soup = self._get(url)
            if not soup:
                log.warning(f"  Skipping page {page} for {brand} (no response)")
                continue

            # Amazon search results are wrapped in data-component-type="s-search-result"
            cards = soup.select('[data-component-type="s-search-result"]')
            log.info(f"  Found {len(cards)} product cards on page {page}")

            for card in cards:
                product = self._parse_product_card(card, brand)
                if product and product["asin"] not in self.scraped_asins:
                    products.append(product)
                    self.scraped_asins.add(product["asin"])

        log.info(f"  ✓ {brand}: collected {len(products)} products")
        return products

    def _parse_product_card(self, card, brand):
        """Extract product data from a single search result card."""
        try:
            asin = card.get("data-asin", "").strip()
            if not asin:
                return None

            # Title
            title_el = card.select_one("h2 a span")
            title = title_el.get_text(strip=True) if title_el else ""

            # Selling price
            price_whole = card.select_one(".a-price-whole")
            price_text = price_whole.get_text(strip=True) if price_whole else ""
            price = self._parse_price(price_text)

            # Strike-through / list price (MRP)
            list_price_el = card.select_one(".a-text-price .a-offscreen")
            list_price = self._parse_price(list_price_el.get_text() if list_price_el else "")

            # Discount badge
            discount_el = card.select_one(".s-coupon-unclipped .a-color-base")
            if not discount_el:
                discount_el = card.select_one(".savingsPercentage")
            discount_text = discount_el.get_text(strip=True) if discount_el else ""
            discount_pct = None
            if discount_text:
                m = re.search(r"(\d+)%", discount_text)
                if m:
                    discount_pct = float(m.group(1))
            elif price and list_price and list_price > price:
                discount_pct = round(((list_price - price) / list_price) * 100, 1)

            # Star rating
            rating_el = card.select_one(".a-icon-alt")
            rating = None
            if rating_el:
                m = re.match(r"([\d.]+)", rating_el.get_text())
                if m:
                    rating = float(m.group(1))

            # Review count
            review_count_el = card.select_one('[aria-label*="ratings"]') or card.select_one(".a-size-base.s-underline-text")
            review_count = None
            if review_count_el:
                rc_text = review_count_el.get_text(strip=True).replace(",", "")
                m = re.search(r"(\d+)", rc_text)
                if m:
                    review_count = int(m.group(1))

            # Product URL
            link_el = card.select_one("h2 a")
            url = BASE_URL + link_el["href"] if link_el and link_el.get("href") else ""

            return {
                "product_id": asin,
                "asin": asin,
                "brand": brand,
                "title": title,
                "price": price,
                "list_price": list_price,
                "discount_pct": discount_pct,
                "rating": rating,
                "review_count": review_count,
                "url": url,
                "scraped_at": datetime.now().isoformat(),
            }

        except Exception as e:
            log.debug(f"Error parsing card: {e}")
            return None

    def get_reviews(self, asin, brand, max_pages=5):
        """
        Scrape customer reviews for a product ASIN.

        Amazon's review URL pattern:
            /product-reviews/{ASIN}?pageNumber={N}

        Args:
            asin:       Amazon product ASIN
            brand:      Brand name (for tagging)
            max_pages:  Number of review pages to scrape (10 reviews/page)

        Returns:
            List of review dicts
        """
        reviews = []

        for page in range(1, max_pages + 1):
            url = f"{BASE_URL}/product-reviews/{asin}?reviewerType=all_reviews&pageNumber={page}"
            log.info(f"    Fetching reviews for {asin} — page {page}")

            soup = self._get(url)
            if not soup:
                break

            review_divs = soup.select('[data-hook="review"]')
            if not review_divs:
                log.info(f"    No more reviews found at page {page}")
                break

            for div in review_divs:
                review = self._parse_review(div, asin, brand)
                if review:
                    reviews.append(review)

        log.info(f"    ✓ {asin}: collected {len(reviews)} reviews")
        return reviews

    def _parse_review(self, div, product_id, brand):
        """Parse a single review div into a structured dict."""
        try:
            review_id = div.get("id", f"rev-{random.randint(1000, 9999)}")

            # Star rating from the aria-label like "4.0 out of 5 stars"
            rating_el = div.select_one('[data-hook="review-star-rating"] .a-icon-alt')
            if not rating_el:
                rating_el = div.select_one('[data-hook="cmps-review-star-rating"] .a-icon-alt')
            rating = None
            if rating_el:
                m = re.match(r"([\d.]+)", rating_el.get_text())
                if m:
                    rating = float(m.group(1))

            # Review title
            title_el = div.select_one('[data-hook="review-title"] span:not(.a-icon-alt)')
            title = title_el.get_text(strip=True) if title_el else ""
            # Remove "Reviewed in India on..." from some title elements
            title = re.sub(r"Reviewed in.*", "", title).strip()

            # Review body
            body_el = div.select_one('[data-hook="review-body"] span')
            body = body_el.get_text(strip=True) if body_el else ""
            body = body.replace("Read more", "").strip()

            # Review date
            date_el = div.select_one('[data-hook="review-date"]')
            date_text = date_el.get_text(strip=True) if date_el else ""
            # "Reviewed in India on 15 March 2024" → extract the date part
            date_match = re.search(r"(\d+\s+\w+\s+\d{4})", date_text)
            review_date = date_match.group(1) if date_match else date_text

            # Verified purchase flag
            verified_el = div.select_one('[data-hook="avp-badge"]')
            verified = verified_el is not None

            # Helpful votes
            helpful_el = div.select_one('[data-hook="helpful-vote-statement"]')
            helpful_votes = 0
            if helpful_el:
                m = re.search(r"(\d+)", helpful_el.get_text())
                if m:
                    helpful_votes = int(m.group(1))

            return {
                "review_id": review_id,
                "product_id": product_id,
                "brand": brand,
                "rating": rating,
                "title": title,
                "body": body,
                "date": review_date,
                "verified_purchase": verified,
                "helpful_votes": helpful_votes,
            }

        except Exception as e:
            log.debug(f"Error parsing review: {e}")
            return None


def save_to_csv(data, filepath):
    """Save a list of dicts to CSV."""
    if not data:
        log.warning(f"No data to save to {filepath}")
        return
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=data[0].keys())
        writer.writeheader()
        writer.writerows(data)
    log.info(f"Saved {len(data)} rows → {filepath}")


def run_scraper(brands=None, product_pages=2, review_pages=4, proxy=None):
    """
    Main entry point for the scraper.

    Args:
        brands:         List of brand names to scrape (default: all)
        product_pages:  How many search result pages per brand
        review_pages:   How many review pages per product
        proxy:          Optional HTTP proxy URL
    """
    scraper = AmazonScraper(proxy=proxy)
    if brands is None:
        brands = list(BRAND_QUERIES.keys())

    all_products = []
    all_reviews = []

    for brand in brands:
        log.info(f"\n━━━ Scraping {brand} ━━━")

        # 1. Collect products from search results
        products = scraper.search_brand(brand, pages=product_pages)
        all_products.extend(products)

        # 2. For each product, scrape reviews
        for product in products[:10]:  # Limit to 10 products per brand to be polite
            asin = product["asin"]
            if not asin:
                continue
            reviews = scraper.get_reviews(asin, brand, max_pages=review_pages)
            all_reviews.extend(reviews)
            polite_sleep(2, 6)  # Extra pause between products

    # 3. Save raw data
    save_to_csv(all_products, "data/raw/products_raw.csv")
    save_to_csv(all_reviews, "data/raw/reviews_raw.csv")

    log.info(f"\n✅ Scraping complete: {len(all_products)} products, {len(all_reviews)} reviews")
    return all_products, all_reviews


if __name__ == "__main__":
    run_scraper()
