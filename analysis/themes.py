import re
from collections import defaultdict
from typing import List, Dict

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

_analyzer = SentimentIntensityAnalyzer()

# ── Positive theme definitions ─────────────────────────────────────────────────
POSITIVE_THEMES = {
    "Smooth Wheels":       ["smooth wheel", "wheels smooth", "spinner wheel", "glide well", "rolls smoothly", "great wheels"],
    "Sturdy Build":        ["sturdy", "strong build", "solid", "well built", "durable", "robust", "tough"],
    "Lightweight":         ["lightweight", "light weight", "very light", "easy to carry", "not heavy"],
    "Good Value":          ["value for money", "worth the price", "affordable", "good price", "great deal", "budget friendly"],
    "Good Capacity":       ["good capacity", "spacious", "fits a lot", "enough space", "large space", "good size"],
    "Premium Look":        ["looks premium", "stylish", "attractive", "beautiful design", "good looking", "elegant"],
    "TSA Lock":            ["tsa lock", "secure lock", "lock works", "combination lock", "good lock"],
    "Warranty Service":    ["good warranty", "great service", "after sales", "customer support helpful"],
    "Easy to Handle":      ["easy to handle", "comfortable grip", "smooth handle", "telescopic handle works"],
    "International Travel": ["international travel", "airline approved", "passed security", "flights", "airport"],
}

# ── Negative theme definitions ─────────────────────────────────────────────────
NEGATIVE_THEMES = {
    "Wheel Issues":        ["wheel broke", "wheels broke", "wheel cracked", "wheel stuck", "bad wheels", "wheel wobble"],
    "Zipper Problems":     ["zipper broke", "zipper failed", "zip broke", "zipper stuck", "poor zipper", "zipper quality"],
    "Handle Broke":        ["handle broke", "handle loose", "handle wobble", "retractable handle", "stuck handle"],
    "Cheap Plastic":       ["cheap plastic", "feels cheap", "poor quality plastic", "flimsy", "thin plastic"],
    "Durability Issues":   ["broke after", "didn't last", "fell apart", "poor durability", "not durable", "cracked"],
    "Color Mismatch":      ["color not as shown", "color faded", "different color", "not as pictured"],
    "Delivery Damage":     ["damaged on arrival", "dent on delivery", "scratched box", "arrived damaged"],
    "Poor Packaging":      ["poor packaging", "badly packed", "packaging damaged"],
    "Expensive":           ["overpriced", "too expensive", "not worth the price", "costly"],
    "Customer Support":    ["customer support bad", "no response", "support unhelpful", "warranty not honored"],
}


def _count_theme_mentions(reviews: List[str], theme_dict: Dict) -> Dict[str, int]:
    """
    Count how many reviews mention each theme.

    Args:
        reviews:    List of review body strings
        theme_dict: Dict of theme_name → list of keyword phrases

    Returns:
        Dict of theme_name → mention_count
    """
    counts = defaultdict(int)
    for review in reviews:
        if not isinstance(review, str):
            continue
        review_lower = review.lower()
        for theme, keywords in theme_dict.items():
            if any(kw in review_lower for kw in keywords):
                counts[theme] += 1
    return dict(counts)


def extract_themes_for_brand(reviews: List[str], top_n: int = 5) -> Dict:
    """
    Extract top positive and negative themes from a list of review texts.

    Returns:
        {
          "top_positives": [{"theme": str, "count": int, "pct": float}, ...],
          "top_negatives": [{"theme": str, "count": int, "pct": float}, ...],
        }
    """
    total = len(reviews)
    if total == 0:
        return {"top_positives": [], "top_negatives": []}

    pos_counts = _count_theme_mentions(reviews, POSITIVE_THEMES)
    neg_counts = _count_theme_mentions(reviews, NEGATIVE_THEMES)

    def top_themes(counts_dict, n):
        sorted_items = sorted(counts_dict.items(), key=lambda x: x[1], reverse=True)
        return [
            {
                "theme": theme,
                "count": count,
                "pct": round(count / total * 100, 1),
            }
            for theme, count in sorted_items[:n]
            if count > 0
        ]

    return {
        "top_positives": top_themes(pos_counts, top_n),
        "top_negatives": top_themes(neg_counts, top_n),
    }


def brand_theme_summary(reviews_df: pd.DataFrame) -> Dict:
    """
    Run theme extraction for every brand in the DataFrame.

    Returns:
        Dict of brand_name → {"top_positives": [...], "top_negatives": [...]}
    """
    results = {}
    for brand, group in reviews_df.groupby("brand"):
        texts = group["body"].tolist()
        results[brand] = extract_themes_for_brand(texts)
    return results


def product_theme_summary(reviews_df: pd.DataFrame, product_id: str) -> Dict:
    """Get themes for a single product."""
    subset = reviews_df[reviews_df["product_id"] == product_id]
    return extract_themes_for_brand(subset["body"].tolist())


def detect_anomalies(reviews_df: pd.DataFrame, products_df: pd.DataFrame) -> List[Dict]:
    """
    Detect non-obvious anomalies in the data that a decision-maker should know about.

    Examples of anomalies we look for:
      A) High-rated product with many durability complaints
         → Rating may be inflated; the product has long-tail quality issues
      B) Brand with high discount % but low sentiment
         → Discounts are masking fundamental product problems
      C) Brand with high review count but low verified purchase %
         → Possible fake review activity
      D) Sudden rating drop in recent reviews vs. older reviews

    Returns:
        List of anomaly dicts: {"brand", "type", "description", "severity"}
    """
    anomalies = []

    for brand, group in reviews_df.groupby("brand"):
        # ── Anomaly A: High rating but many durability complaints ──────────────
        brand_products = products_df[products_df["brand"] == brand]
        avg_rating = brand_products["rating"].mean()

        durability_keywords = NEGATIVE_THEMES.get("Durability Issues", [])
        durability_mention_count = group["body"].str.lower().apply(
            lambda x: any(kw in x for kw in durability_keywords) if isinstance(x, str) else False
        ).sum()
        durability_pct = durability_mention_count / len(group) * 100 if len(group) > 0 else 0

        if avg_rating >= 4.0 and durability_pct >= 10:
            anomalies.append({
                "brand": brand,
                "type": "Rating-Quality Mismatch",
                "description": (
                    f"{brand} has an avg rating of {avg_rating:.1f}★ but "
                    f"{durability_pct:.0f}% of reviews mention durability issues. "
                    "The high rating may not reflect long-term quality."
                ),
                "severity": "High" if durability_pct >= 20 else "Medium",
            })

        # ── Anomaly B: High discount but negative sentiment ───────────────────
        avg_discount = brand_products["discount_pct"].mean()
        if group.get("compound_score") is not None:
            avg_sentiment = group["compound_score"].mean() if "compound_score" in group.columns else 0
        else:
            avg_sentiment = 0

        if avg_discount >= 35 and avg_sentiment < 0.1:
            anomalies.append({
                "brand": brand,
                "type": "Discount-Masking Strategy",
                "description": (
                    f"{brand} offers avg {avg_discount:.0f}% discount but sentiment score is low ({avg_sentiment:.2f}). "
                    "Heavy discounting may be compensating for poor product satisfaction."
                ),
                "severity": "High",
            })

        # ── Anomaly C: Very recent rating drop ────────────────────────────────
        if "date" in group.columns and pd.api.types.is_datetime64_any_dtype(group["date"]):
            cutoff = group["date"].max() - pd.Timedelta(days=90)
            recent = group[group["date"] >= cutoff]
            older = group[group["date"] < cutoff]

            if len(recent) >= 10 and len(older) >= 10:
                recent_avg = recent["rating"].mean()
                older_avg = older["rating"].mean()
                if older_avg - recent_avg >= 0.4:
                    anomalies.append({
                        "brand": brand,
                        "type": "Declining Recent Ratings",
                        "description": (
                            f"{brand}'s recent 90-day rating ({recent_avg:.1f}★) is "
                            f"{older_avg - recent_avg:.1f} stars lower than historical avg ({older_avg:.1f}★). "
                            "Quality may have declined or a bad batch shipped."
                        ),
                        "severity": "Medium",
                    })

    return anomalies
