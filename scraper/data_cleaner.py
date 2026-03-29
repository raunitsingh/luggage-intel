import re
import pandas as pd


# Luggage category keywords → canonical category names
CATEGORY_RULES = [
    (r"\bcabin\b|\b20[\"\s]|\bhand\s*carry\b|\bcarry.?on\b", "Cabin (20\")"),
    (r"\bmedium\b|\b24[\"\s]", "Medium (24\")"),
    (r"\blarge\b|\b28[\"\s]", "Large (28\")"),
    (r"\b30[\"\s]|\bextra.?large\b|\bxl\b", "Extra Large (30\")"),
    (r"\bset\b|\bcombo\b|\b2.?pc\b|\b3.?pc\b", "Trolley Set"),
    (r"\bduffle\b|\bsoftside\b|\bsoft.?bag\b", "Soft Bag"),
    (r"\bbackpack\b|\brucksack\b", "Backpack"),
]


def infer_category(title: str) -> str:
    """Infer luggage category from product title using regex rules."""
    title_lower = title.lower()
    for pattern, category in CATEGORY_RULES:
        if re.search(pattern, title_lower):
            return category
    return "Other"


def infer_size(category: str) -> str:
    """Extract size in inches from category string."""
    m = re.search(r"(\d+)\"", category)
    return m.group(1) if m else "N/A"


def clean_products(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and enrich the raw products DataFrame.

    Steps:
      1. Drop rows with no price (can't analyze without it)
      2. Compute discount_pct where missing
      3. Infer category from title
      4. Deduplicate by product_id / ASIN
      5. Add pricing segment column
    """
    df = df.copy()

    # ── 1. Drop rows with no usable price ─────────────────────────────────────
    df = df.dropna(subset=["price"])
    df["price"] = pd.to_numeric(df["price"], errors="coerce")
    df = df[df["price"] > 0]

    # ── 2. Fill in list_price if missing (assume 20% markup) ──────────────────
    df["list_price"] = pd.to_numeric(df["list_price"], errors="coerce")
    df["list_price"] = df["list_price"].fillna(df["price"] * 1.20)

    # ── 3. Recompute discount_pct cleanly ─────────────────────────────────────
    df["discount_pct"] = (
        ((df["list_price"] - df["price"]) / df["list_price"]) * 100
    ).round(1).clip(lower=0)

    # ── 4. Infer category and size from title ─────────────────────────────────
    if "category" not in df.columns or df["category"].isna().all():
        df["category"] = df["title"].apply(infer_category)
    df["size_inches"] = df["category"].apply(infer_size)

    # ── 5. Clean rating and review_count ──────────────────────────────────────
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").clip(1, 5)
    df["review_count"] = pd.to_numeric(df["review_count"], errors="coerce").fillna(0).astype(int)

    # ── 6. Add price segment label ────────────────────────────────────────────
    df["segment"] = pd.cut(
        df["price"],
        bins=[0, 2500, 5000, 10000, float("inf")],
        labels=["Budget (<₹2.5K)", "Value (₹2.5–5K)", "Mid (₹5–10K)", "Premium (>₹10K)"]
    )

    # ── 7. Deduplicate ────────────────────────────────────────────────────────
    if "product_id" in df.columns:
        df = df.drop_duplicates(subset="product_id")

    # ── 8. Normalize brand names ──────────────────────────────────────────────
    df["brand"] = df["brand"].str.strip().str.title()

    return df.reset_index(drop=True)


def clean_reviews(df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean and normalize the raw reviews DataFrame.

    Steps:
      1. Drop rows missing body text or rating
      2. Normalize text (strip HTML, extra whitespace)
      3. Standardize date format
      4. Add word_count column (useful for filtering very short reviews)
      5. Cast dtypes properly
    """
    df = df.copy()

    # ── 1. Drop incomplete rows ───────────────────────────────────────────────
    df = df.dropna(subset=["body", "rating"])
    df = df[df["body"].str.strip() != ""]

    # ── 2. Clean text ─────────────────────────────────────────────────────────
    def clean_text(text):
        if not isinstance(text, str):
            return ""
        text = re.sub(r"<[^>]+>", " ", text)          # strip HTML tags
        text = re.sub(r"\s+", " ", text)               # collapse whitespace
        text = text.strip()
        return text

    df["body"] = df["body"].apply(clean_text)
    df["title"] = df["title"].apply(clean_text)

    # ── 3. Normalize ratings ──────────────────────────────────────────────────
    df["rating"] = pd.to_numeric(df["rating"], errors="coerce").clip(1, 5)
    df = df.dropna(subset=["rating"])
    df["rating"] = df["rating"].astype(float)

    # ── 4. Word count ─────────────────────────────────────────────────────────
    df["word_count"] = df["body"].str.split().str.len()

    # ── 5. Verified purchase flag ─────────────────────────────────────────────
    df["verified_purchase"] = df["verified_purchase"].astype(bool)

    # ── 6. Helpful votes ─────────────────────────────────────────────────────
    df["helpful_votes"] = pd.to_numeric(df["helpful_votes"], errors="coerce").fillna(0).astype(int)

    # ── 7. Parse dates ────────────────────────────────────────────────────────
    df["date"] = pd.to_datetime(df["date"], errors="coerce")

    # ── 8. Normalize brand names ──────────────────────────────────────────────
    df["brand"] = df["brand"].str.strip().str.title()

    # ── 9. Drop reviews that are just 1–2 words (spam/noise) ─────────────────
    df = df[df["word_count"] >= 3]

    return df.reset_index(drop=True)


def load_and_clean(products_path: str, reviews_path: str):
    """
    Convenience function: load CSVs, clean both, return (products_df, reviews_df).
    """
    products_df = clean_products(pd.read_csv(products_path))
    reviews_df = clean_reviews(pd.read_csv(reviews_path))
    return products_df, reviews_df
