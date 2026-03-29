import random
import json
import csv
import os
import uuid
from datetime import datetime, timedelta

# ── Seed for reproducibility ──────────────────────────────────────────────────
random.seed(42)

# ── Brand profiles: realistic price bands, quality signals, and quirks ────────
BRAND_PROFILES = {
    "Safari": {
        "price_range": (2800, 9500),
        "list_price_multiplier": (1.15, 1.45),   # MRP is 15–45% above selling price
        "avg_rating": 4.1,
        "rating_std": 0.4,
        "review_volume": (120, 600),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Trolley Set"],
        "positive_themes": [
            "sturdy build quality", "smooth spinner wheels", "great value for money",
            "lightweight", "TSA approved lock", "good zipper quality",
            "perfect for domestic travel", "hard shell feels premium"
        ],
        "negative_themes": [
            "handle wobbles after few months", "scratches easily",
            "zipper pull broke", "color faded after first wash",
            "instructions unclear"
        ],
        "complaint_rate": 0.22,
        "segment": "mid-range",
    },
    "Skybags": {
        "price_range": (1800, 6500),
        "list_price_multiplier": (1.20, 1.60),
        "avg_rating": 3.9,
        "rating_std": 0.5,
        "review_volume": (200, 900),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Backpack"],
        "positive_themes": [
            "very affordable price", "attractive design", "lightweight body",
            "multiple compartments", "good for short trips", "trendy colors",
            "fits overhead cabin bin"
        ],
        "negative_themes": [
            "wheels broke within 3 months", "zipper quality poor",
            "plastic feels cheap", "handle not smooth", "not durable for rough travel",
            "color not as shown in photo", "stitching came off"
        ],
        "complaint_rate": 0.31,
        "segment": "budget",
    },
    "American Tourister": {
        "price_range": (4500, 16000),
        "list_price_multiplier": (1.10, 1.35),
        "avg_rating": 4.3,
        "rating_std": 0.35,
        "review_volume": (300, 1200),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Trolley Set", "Spinner"],
        "positive_themes": [
            "excellent build quality", "wheels glide perfectly", "durable hard shell",
            "warranty service great", "premium feel", "survived international travel",
            "lock is very secure", "lightweight for its size", "looks premium"
        ],
        "negative_themes": [
            "expensive", "zipper stiff initially", "minor scratch on delivery",
            "slightly heavy compared to competitors"
        ],
        "complaint_rate": 0.14,
        "segment": "premium",
    },
    "VIP": {
        "price_range": (2500, 8000),
        "list_price_multiplier": (1.25, 1.55),
        "avg_rating": 4.0,
        "rating_std": 0.45,
        "review_volume": (100, 500),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Soft Trolley"],
        "positive_themes": [
            "trusted Indian brand", "good capacity", "strong frame",
            "value for money", "easy to carry", "classic design"
        ],
        "negative_themes": [
            "looks outdated", "wheels not as smooth as modern brands",
            "handle could be better", "not water resistant enough",
            "packaging could be improved"
        ],
        "complaint_rate": 0.25,
        "segment": "mid-range",
    },
    "Aristocrat": {
        "price_range": (1200, 4500),
        "list_price_multiplier": (1.30, 1.70),
        "avg_rating": 3.7,
        "rating_std": 0.55,
        "review_volume": (80, 350),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Duffle Bag"],
        "positive_themes": [
            "cheapest option available", "decent for occasional use",
            "lightweight", "good for budget travel", "multiple pockets"
        ],
        "negative_themes": [
            "very cheap plastic", "broke after 2 trips", "zipper failed",
            "wheels cracked", "not worth even the low price",
            "poor stitching", "handle broke off"
        ],
        "complaint_rate": 0.38,
        "segment": "budget",
    },
    "Nasher Miles": {
        "price_range": (3200, 10000),
        "list_price_multiplier": (1.15, 1.40),
        "avg_rating": 4.2,
        "rating_std": 0.38,
        "review_volume": (150, 700),
        "categories": ["Cabin (20\")", "Medium (24\")", "Large (28\")", "Spinner Set"],
        "positive_themes": [
            "modern design", "double spinner wheels excellent", "hard shell strong",
            "TSA lock included", "good for international travel", "stylish look",
            "lightweight polycarbonate", "great zipper quality", "size perfectly legal for cabin"
        ],
        "negative_themes": [
            "price is high for Indian brand", "customer support slow",
            "limited availability in stores", "minor dent on corner"
        ],
        "complaint_rate": 0.17,
        "segment": "mid-range",
    },
}

# ── Realistic review templates ─────────────────────────────────────────────────
POSITIVE_OPENERS = [
    "Really happy with this purchase!",
    "Exceeded my expectations.",
    "Worth every rupee.",
    "Great product, highly recommend.",
    "Bought this for my trip and loved it.",
    "Amazing quality at this price point.",
    "My go-to luggage now.",
    "Superb build quality.",
    "Five stars without hesitation.",
    "Absolutely love this bag.",
]

NEGATIVE_OPENERS = [
    "Very disappointed.",
    "Not worth the money.",
    "Would not recommend.",
    "Poor quality control.",
    "Stopped working after 2 uses.",
    "Regret buying this.",
    "Total waste of money.",
    "Expected much better.",
    "Quality is a joke.",
]

NEUTRAL_OPENERS = [
    "Decent product for the price.",
    "It's okay, nothing special.",
    "Average quality.",
    "Gets the job done.",
    "Mixed feelings about this.",
]


def random_date(start_months_ago=18):
    """Return a random datetime within the last N months."""
    days_ago = random.randint(0, start_months_ago * 30)
    return datetime.now() - timedelta(days=days_ago)


def generate_review_text(brand, rating, profile):
    """Generate a humanized review based on brand profile and star rating."""
    is_complaint = rating <= 2
    is_mixed = rating == 3
    is_positive = rating >= 4

    parts = []

    if is_positive:
        parts.append(random.choice(POSITIVE_OPENERS))
        # Pick 2–4 positive themes
        themes = random.sample(profile["positive_themes"], min(3, len(profile["positive_themes"])))
        for theme in themes:
            parts.append(f"The {theme}.")
        # Sometimes add a minor gripe
        if random.random() < 0.3 and profile["negative_themes"]:
            gripe = random.choice(profile["negative_themes"])
            parts.append(f"Only minor issue: {gripe}. But overall very happy.")

    elif is_complaint:
        parts.append(random.choice(NEGATIVE_OPENERS))
        themes = random.sample(profile["negative_themes"], min(3, len(profile["negative_themes"])))
        for theme in themes:
            parts.append(f"The {theme}.")
        parts.append("Would not buy again.")

    else:  # Mixed / 3 stars
        parts.append(random.choice(NEUTRAL_OPENERS))
        pos = random.choice(profile["positive_themes"])
        neg = random.choice(profile["negative_themes"])
        parts.append(f"Good thing: {pos}.")
        parts.append(f"Bad thing: {neg}.")
        parts.append("Maybe okay for occasional use.")

    return " ".join(parts)


def generate_review_title(rating):
    """Short headline matching the star rating."""
    if rating == 5:
        return random.choice(["Excellent!", "Love it!", "Perfect buy", "Highly recommend", "Great product"])
    elif rating == 4:
        return random.choice(["Good value", "Quite good", "Worth it", "Happy with purchase", "Nice bag"])
    elif rating == 3:
        return random.choice(["Average", "Okay for the price", "Decent", "Mixed feelings", "So-so"])
    elif rating == 2:
        return random.choice(["Disappointing", "Could be better", "Not worth it", "Below expectations"])
    else:
        return random.choice(["Terrible", "Waste of money", "Very poor quality", "Do not buy"])


def generate_products(brand, profile, count=12):
    """Generate a list of product dicts for a brand."""
    products = []
    categories = profile["categories"]

    for i in range(count):
        category = categories[i % len(categories)]
        price = round(random.uniform(*profile["price_range"]), -1)  # round to nearest 10
        multiplier = random.uniform(*profile["list_price_multiplier"])
        list_price = round(price * multiplier, -1)
        discount_pct = round(((list_price - price) / list_price) * 100, 1)

        # Rating: use brand average with some variance, clamp to 1–5
        rating = round(random.gauss(profile["avg_rating"], profile["rating_std"]), 1)
        rating = max(1.0, min(5.0, rating))

        review_count = random.randint(*profile["review_volume"])

        size_inches = category.split("(")[-1].replace("\")", "").strip() if "(" in category else "N/A"

        product = {
            "product_id": f"{brand[:3].upper()}-{uuid.uuid4().hex[:8].upper()}",
            "brand": brand,
            "title": f"{brand} {category} Hard Trolley Bag - {random.choice(['Black', 'Blue', 'Red', 'Grey', 'Navy'])}",
            "category": category,
            "size_inches": size_inches,
            "price": price,
            "list_price": list_price,
            "discount_pct": discount_pct,
            "rating": rating,
            "review_count": review_count,
            "segment": profile["segment"],
            "url": f"https://www.amazon.in/dp/B{uuid.uuid4().hex[:9].upper()}",
        }
        products.append(product)

    return products


def generate_reviews(product, profile, count=60):
    """Generate realistic reviews for a product."""
    reviews = []

    for _ in range(count):
        # Rating distribution influenced by brand avg_rating and complaint_rate
        is_complaint = random.random() < profile["complaint_rate"]

        if is_complaint:
            rating = random.choices([1, 2], weights=[0.4, 0.6])[0]
        else:
            # Bias toward 4–5 stars for good brands
            base = round(profile["avg_rating"])
            if base >= 4:
                rating = random.choices([3, 4, 5], weights=[0.15, 0.35, 0.5])[0]
            else:
                rating = random.choices([2, 3, 4, 5], weights=[0.15, 0.25, 0.35, 0.25])[0]

        review_date = random_date()

        review = {
            "review_id": f"REV-{uuid.uuid4().hex[:10].upper()}",
            "product_id": product["product_id"],
            "brand": product["brand"],
            "rating": rating,
            "title": generate_review_title(rating),
            "body": generate_review_text(product["brand"], rating, profile),
            "date": review_date.strftime("%Y-%m-%d"),
            "verified_purchase": random.random() > 0.15,  # 85% verified
            "helpful_votes": random.randint(0, 45),
        }
        reviews.append(review)

    return reviews


def save_csv(data, filepath, fieldnames):
    """Write a list of dicts to a CSV file."""
    os.makedirs(os.path.dirname(filepath), exist_ok=True)
    with open(filepath, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(data)
    print(f"  ✓ Saved {len(data):,} rows → {filepath}")


def main():
    print("\n🧳 Generating synthetic Amazon India luggage data...\n")

    all_products = []
    all_reviews = []

    for brand, profile in BRAND_PROFILES.items():
        print(f"  Building data for {brand}...")
        products = generate_products(brand, profile, count=12)
        all_products.extend(products)

        for product in products:
            # Reviews per product: 50–80
            count = random.randint(50, 80)
            reviews = generate_reviews(product, profile, count=count)
            all_reviews.extend(reviews)

    # ── Save products ─────────────────────────────────────────────────────────
    product_fields = [
        "product_id", "brand", "title", "category", "size_inches",
        "price", "list_price", "discount_pct", "rating", "review_count",
        "segment", "url"
    ]
    save_csv(all_products, "data/cleaned/products.csv", product_fields)

    # ── Save reviews ──────────────────────────────────────────────────────────
    review_fields = [
        "review_id", "product_id", "brand", "rating", "title",
        "body", "date", "verified_purchase", "helpful_votes"
    ]
    save_csv(all_reviews, "data/cleaned/reviews.csv", review_fields)

    print(f"\n✅ Done! Generated {len(all_products)} products and {len(all_reviews):,} reviews.")
    print("   Run `streamlit run dashboard/app.py` to launch the dashboard.\n")


if __name__ == "__main__":
    main()
