import re
import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

# Initialize VADER once (it loads a lexicon from disk)
_analyzer = SentimentIntensityAnalyzer()


ASPECT_KEYWORDS = {
    "Wheels":     ["wheel", "wheels", "spinner", "rollers", "rolling", "rolls", "glide", "smooth"],
    "Handle":     ["handle", "handles", "grip", "trolley handle", "telescopic", "retractable", "pull"],
    "Zipper":     ["zipper", "zip", "zippers", "closure", "lock", "locks", "locking"],
    "Material":   ["material", "plastic", "polycarbonate", "abs", "shell", "fabric", "hard", "soft", "texture"],
    "Durability": ["durable", "durability", "strong", "sturdy", "broke", "broken", "cracked", "quality", "build"],
    "Size":       ["size", "capacity", "spacious", "fits", "large", "small", "cabin", "weight", "lightweight"],
    "Value":      ["price", "value", "money", "worth", "expensive", "cheap", "afford", "cost", "budget"],
}


def get_sentiment_label(compound: float) -> str:
    """Convert VADER compound score to a human-readable label."""
    if compound >= 0.05:
        return "Positive"
    elif compound <= -0.05:
        return "Negative"
    else:
        return "Neutral"


def analyze_review(text: str) -> dict:
    """
    Run VADER sentiment analysis on a single review text.

    Returns:
        {
          "compound": float,     # overall sentiment (-1 to 1)
          "pos": float,          # proportion of positive words
          "neu": float,          # proportion of neutral words
          "neg": float,          # proportion of negative words
          "label": str,          # "Positive" / "Neutral" / "Negative"
        }
    """
    if not isinstance(text, str) or not text.strip():
        return {"compound": 0.0, "pos": 0.0, "neu": 1.0, "neg": 0.0, "label": "Neutral"}

    scores = _analyzer.polarity_scores(text)
    scores["label"] = get_sentiment_label(scores["compound"])
    return scores


def analyze_aspects(text: str) -> dict:
    """
    Perform aspect-level sentiment analysis on review text.

    Strategy:
      1. Tokenize text into sentences.
      2. For each sentence, check if any aspect keyword appears.
      3. If yes, run VADER on that sentence and attribute the score to the aspect.
      4. Average across all sentences mentioning the aspect.

    Returns:
        dict mapping aspect_name → compound_score (or None if not mentioned)
    """
    if not isinstance(text, str):
        return {asp: None for asp in ASPECT_KEYWORDS}

    text_lower = text.lower()
    # Split into sentences
    sentences = re.split(r"[.!?]+", text_lower)
    sentences = [s.strip() for s in sentences if s.strip()]

    aspect_scores = {asp: [] for asp in ASPECT_KEYWORDS}

    for sentence in sentences:
        words = sentence.split()
        for aspect, keywords in ASPECT_KEYWORDS.items():
            # Check if any keyword appears in this sentence
            if any(kw in sentence for kw in keywords):
                score = _analyzer.polarity_scores(sentence)["compound"]
                aspect_scores[aspect].append(score)

    # Average scores per aspect; return None if aspect wasn't mentioned
    return {
        asp: (sum(scores) / len(scores)) if scores else None
        for asp, scores in aspect_scores.items()
    }


def enrich_reviews_df(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add sentiment columns to the reviews DataFrame.

    New columns added:
      - compound_score
      - sentiment_label
      - aspect_Wheels, aspect_Handle, etc. (one column per aspect)
    """
    df = reviews_df.copy()

    # ── Overall sentiment ─────────────────────────────────────────────────────
    sentiments = df["body"].apply(analyze_review)
    df["compound_score"] = sentiments.apply(lambda x: x["compound"])
    df["sentiment_label"] = sentiments.apply(lambda x: x["label"])

    # ── Aspect-level sentiment ────────────────────────────────────────────────
    aspects = df["body"].apply(analyze_aspects)
    for aspect in ASPECT_KEYWORDS:
        col_name = f"aspect_{aspect.lower()}"
        df[col_name] = aspects.apply(lambda x: x.get(aspect))

    return df


def brand_sentiment_summary(reviews_df: pd.DataFrame) -> pd.DataFrame:
    """
    Aggregate per-review sentiment into per-brand summary stats.

    Returns a DataFrame with one row per brand, columns:
      - avg_sentiment_score
      - pct_positive
      - pct_neutral
      - pct_negative
      - total_reviews
      - aspect_* columns (avg per aspect)
    """
    df = reviews_df.copy()

    # Make sure we have the needed columns
    if "compound_score" not in df.columns:
        df = enrich_reviews_df(df)

    brand_groups = df.groupby("brand")

    records = []
    for brand, group in brand_groups:
        total = len(group)
        pct_pos = round((group["sentiment_label"] == "Positive").sum() / total * 100, 1)
        pct_neu = round((group["sentiment_label"] == "Neutral").sum() / total * 100, 1)
        pct_neg = round((group["sentiment_label"] == "Negative").sum() / total * 100, 1)

        record = {
            "brand": brand,
            "avg_sentiment_score": round(group["compound_score"].mean(), 3),
            "pct_positive": pct_pos,
            "pct_neutral": pct_neu,
            "pct_negative": pct_neg,
            "total_reviews_analyzed": total,
        }

        # Average aspect scores (skip NaN)
        for aspect in ASPECT_KEYWORDS:
            col = f"aspect_{aspect.lower()}"
            if col in group.columns:
                valid = group[col].dropna()
                record[f"aspect_{aspect.lower()}"] = round(valid.mean(), 3) if len(valid) > 0 else None

        records.append(record)

    return pd.DataFrame(records)
