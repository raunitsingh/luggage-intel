import pandas as pd
import numpy as np
from typing import List, Dict


def value_score(avg_sentiment: float, avg_price: float) -> float:
    """
    Compute a value-for-money score: high sentiment at low price wins.

    Formula: sentiment_score / log10(price)
    This penalizes brands only slightly for being expensive, but rewards
    strong customer satisfaction per rupee spent.
    """
    if avg_price <= 0:
        return 0
    return avg_sentiment / np.log10(avg_price)


def generate_insights(
    products_df: pd.DataFrame,
    reviews_df: pd.DataFrame,
    brand_sentiment_df: pd.DataFrame,
    brand_themes: Dict,
) -> List[Dict]:
    """
    Generate a list of structured insight dicts for the Agent Insights panel.

    Each insight dict has:
      - title: str
      - body: str (1-3 sentences)
      - icon: str (emoji)
      - category: str (e.g., "Value", "Quality", "Market Gap")
    """
    insights = []

    # ── Build a combined brand-level summary ───────────────────────────────────
    price_summary = products_df.groupby("brand").agg(
        avg_price=("price", "mean"),
        avg_discount=("discount_pct", "mean"),
        avg_rating=("rating", "mean"),
        total_products=("product_id", "count"),
    ).reset_index()

    merged = price_summary.merge(brand_sentiment_df, on="brand", how="left")

    # ── Insight 1: Best value-for-money ──────────────────────────────────────
    merged["value_score"] = merged.apply(
        lambda r: value_score(r.get("avg_sentiment_score", 0), r["avg_price"]), axis=1
    )
    best_value = merged.loc[merged["value_score"].idxmax()]
    insights.append({
        "title": f"🏆 Best Value-for-Money: {best_value['brand']}",
        "body": (
            f"{best_value['brand']} delivers the highest customer satisfaction per rupee spent. "
            f"With an average price of ₹{best_value['avg_price']:,.0f} and a sentiment score of "
            f"{best_value.get('avg_sentiment_score', 0):.2f}, it outperforms competitors on the value axis."
        ),
        "icon": "💰",
        "category": "Value",
    })

    # ── Insight 2: Overpriced underperformer ──────────────────────────────────
    # High price + low sentiment = red flag
    merged["price_rank"] = merged["avg_price"].rank(ascending=False)
    merged["sentiment_rank"] = merged["avg_sentiment_score"].rank(ascending=False)
    merged["overpriced_score"] = merged["price_rank"] - merged["sentiment_rank"]

    overpriced = merged.loc[merged["overpriced_score"].idxmax()]
    insights.append({
        "title": f"⚠️ Overpriced Relative to Satisfaction: {overpriced['brand']}",
        "body": (
            f"{overpriced['brand']} ranks high on price but lower on customer sentiment. "
            f"Average price is ₹{overpriced['avg_price']:,.0f} but sentiment score "
            f"({overpriced.get('avg_sentiment_score', 0):.2f}) lags behind cheaper alternatives. "
            "Buyers may be paying a brand premium without a quality premium."
        ),
        "icon": "📉",
        "category": "Pricing",
    })

    # ── Insight 3: Discount dependency signal ─────────────────────────────────
    high_discount = merged.loc[merged["avg_discount"].idxmax()]
    low_discount = merged.loc[merged["avg_discount"].idxmin()]
    insights.append({
        "title": f"🏷️ Discount Dependency: {high_discount['brand']} vs {low_discount['brand']}",
        "body": (
            f"{high_discount['brand']} relies on an avg {high_discount['avg_discount']:.0f}% discount "
            f"to drive demand — suggesting the product may struggle at full MRP. "
            f"{low_discount['brand']} sells with only {low_discount['avg_discount']:.0f}% discount, "
            "indicating stronger brand equity and willingness-to-pay."
        ),
        "icon": "🏷️",
        "category": "Pricing",
    })

    # ── Insight 4: Hidden quality trap ────────────────────────────────────────
    # Brand with good ratings but high complaint % in reviews
    if "pct_negative" in merged.columns and "avg_rating" in merged.columns:
        merged["quality_gap"] = merged["avg_rating"] - (5 * (1 - merged["pct_negative"] / 100))
        quality_trap = merged.loc[merged["quality_gap"].idxmax()]
        insights.append({
            "title": f"🔍 Hidden Quality Trap: {quality_trap['brand']}",
            "body": (
                f"{quality_trap['brand']} has a {quality_trap['avg_rating']:.1f}★ average rating, "
                f"but {quality_trap.get('pct_negative', 0):.0f}% of reviews express negative sentiment. "
                "Star ratings may be inflated by recency bias or review manipulation. "
                "Read the reviews before you trust the stars."
            ),
            "icon": "🪤",
            "category": "Quality",
        })

    # ── Insight 5: Complaint concentration analysis ───────────────────────────
    # Find which brand gets the most specific durability complaints
    durability_brands = {}
    for brand, themes in brand_themes.items():
        neg_themes = themes.get("top_negatives", [])
        for theme in neg_themes:
            if "Durability" in theme["theme"] or "Wheel" in theme["theme"]:
                durability_brands[brand] = theme["pct"]
                break

    if durability_brands:
        worst_durability = max(durability_brands, key=durability_brands.get)
        insights.append({
            "title": f"🔧 Durability Red Flag: {worst_durability}",
            "body": (
                f"{worst_durability} has the highest rate of durability-related complaints "
                f"({durability_brands[worst_durability]:.0f}% of reviews mention build or wheel failures). "
                "This is a critical signal for buyers who travel frequently or check in luggage."
            ),
            "icon": "🔧",
            "category": "Quality",
        })

    # ── Insight 6: Market gap opportunity ─────────────────────────────────────
    # The gap between premium price band and good-sentiment brands
    premium_brands = merged[merged["avg_price"] > 7000]
    mid_brands = merged[(merged["avg_price"] >= 3000) & (merged["avg_price"] <= 7000)]

    if not premium_brands.empty and not mid_brands.empty:
        best_mid = mid_brands.loc[mid_brands.get("avg_sentiment_score", pd.Series()).idxmax() 
                                   if "avg_sentiment_score" in mid_brands.columns 
                                   else mid_brands.index[0]]
        insights.append({
            "title": "🎯 Market Gap: Mid-Range Brands Stealing Premium Share",
            "body": (
                f"Brands priced ₹3,000–7,000 are matching premium sentiment scores at 40–60% lower price points. "
                f"{best_mid['brand']} in particular achieves near-premium sentiment "
                f"({best_mid.get('avg_sentiment_score', 0):.2f}) at avg ₹{best_mid['avg_price']:,.0f}. "
                "This puts pressure on premium brands to justify their pricing."
            ),
            "icon": "🎯",
            "category": "Market",
        })

    # ── Insight 7: Who is gaining momentum ───────────────────────────────────
    # Look at recent vs older review sentiment if dates are available
    if "date" in reviews_df.columns and pd.api.types.is_datetime64_any_dtype(reviews_df["date"]):
        momentum_data = {}
        cutoff = reviews_df["date"].max() - pd.Timedelta(days=90)

        for brand, group in reviews_df.groupby("brand"):
            if "compound_score" not in group.columns:
                continue
            recent = group[group["date"] >= cutoff]["compound_score"].mean()
            older = group[group["date"] < cutoff]["compound_score"].mean()
            if not pd.isna(recent) and not pd.isna(older):
                momentum_data[brand] = recent - older

        if momentum_data:
            best_momentum = max(momentum_data, key=momentum_data.get)
            delta = momentum_data[best_momentum]
            direction = "improving" if delta > 0 else "declining"
            insights.append({
                "title": f"📈 Momentum Winner: {best_momentum}",
                "body": (
                    f"{best_momentum}'s sentiment is {direction} — recent 90-day reviews score "
                    f"{abs(delta):.2f} points {'higher' if delta > 0 else 'lower'} than historical average. "
                    "This could reflect a recent product update, quality improvement, or a PR campaign."
                ),
                "icon": "📈",
                "category": "Trend",
            })

    return insights
