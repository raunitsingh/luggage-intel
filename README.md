# 🧳 Luggage Intel — Amazon India Competitive Intelligence Dashboard

> Built for the **Moonshot AI Agent Internship Assignment**

An interactive competitive intelligence dashboard that tracks, analyzes, and compares major luggage brands on Amazon India — powered by VADER sentiment analysis, aspect-level NLP, and AI-generated insights.

---

## 🚀 Quick Start (2 minutes)

```bash
# 1. Clone / unzip the project
cd luggage-intel

# 2. Install dependencies
pip install -r requirements.txt

# 3. Download NLTK data (one-time)
python -c "import nltk; nltk.download('punkt'); nltk.download('stopwords')"

# 4. Generate synthetic data (or run the real scraper — see below)
python generate_data.py

# 5. Launch the dashboard
streamlit run dashboard/app.py
```

The dashboard opens at **http://localhost:8501**

---

## 📁 File Structure

```
luggage-intel/
│
├── generate_data.py              # Synthetic data generator (demo / fallback)
├── requirements.txt
├── README.md
│
├── scraper/
│   ├── amazon_scraper.py         # Live Amazon India scraper (requests + BS4)
│   └── data_cleaner.py           # Cleaning & standardization pipeline
│
├── analysis/
│   ├── sentiment.py              # VADER sentiment + aspect-level analysis
│   ├── themes.py                 # Theme extraction + anomaly detection
│   └── insights.py               # Agent Insights generator
│
├── dashboard/
│   ├── app.py                    # Main Streamlit app entry point
│   └── components/
│       ├── overview.py           # Tab 1: Market Snapshot
│       ├── brand_comparison.py   # Tab 2: Brand Benchmarking
│       ├── product_drilldown.py  # Tab 3: Per-product deep dive
│       └── agent_insights.py     # Tab 4: AI-generated conclusions
│
└── data/
    ├── raw/                      # Raw scraped CSVs (if using live scraper)
    └── cleaned/
        ├── products.csv          # Cleaned product data
        └── reviews.csv           # Cleaned review data
```

---

## 📊 Dashboard Features

### Tab 1 — Overview
- Total brands / products / reviews tracked
- Average price and discount across brands
- **Market positioning scatter** (Price vs. Sentiment vs. Volume)
- Rating distribution violin plots
- Discount dependency chart

### Tab 2 — Brand Comparison
- Sortable scorecard table
- **Multi-metric spider/radar chart**
- MRP vs. selling price grouped bars
- Sentiment distribution (positive / neutral / negative stacked)
- **Aspect-level sentiment heatmap** (wheels, handle, zipper, material, durability, size, value)
- Top themes per brand (praise and complaints)

### Tab 3 — Product Drilldown
- Full product card (price, discount, rating)
- Rating distribution bar
- Top praise and complaint themes
- **Sentiment timeline** (rolling average)
- Individual reviews with sentiment labels

### Tab 4 — Agent Insights
- 5–7 non-obvious AI-generated conclusions
- Anomaly detection (rating-quality mismatch, discount masking, review decline)
- **Value-for-money index** (sentiment adjusted per rupee)
- Aspect-level winners table
- **Review trust signals** (fake review heuristics)
- Decision recommendation panel

---

## 🔧 Running the Live Scraper

The real scraper fetches actual Amazon India data. Amazon uses bot detection, so:

```bash
# Basic usage (may get blocked without a proxy)
python scraper/amazon_scraper.py

# With a proxy (recommended for production)
python -c "
from scraper.amazon_scraper import run_scraper
run_scraper(
    brands=['Safari', 'Skybags', 'American Tourister'],
    product_pages=3,
    review_pages=5,
    proxy='http://your-proxy:port'
)
"
```

After scraping, copy files and clean:
```bash
cp data/raw/products_raw.csv data/cleaned/products.csv
cp data/raw/reviews_raw.csv data/cleaned/reviews.csv
```

---

## 🧠 Sentiment Methodology

**Engine:** VADER (Valence Aware Dictionary and sEntiment Reasoner)

**Why VADER?**
- Purpose-built for short-form, informal product reviews
- Handles capitalization ("TERRIBLE"), punctuation ("!!"), and emoticons
- No training data or GPU required — works out of the box
- Produces a compound score from -1.0 (most negative) to +1.0 (most positive)

**Labels:**
- `compound >= 0.05` → Positive
- `compound <= -0.05` → Negative
- Otherwise → Neutral

**Aspect-level sentiment:**
Each sentence in a review is checked for aspect keywords (wheels, handle, zipper, etc.). When a keyword is found, VADER scores that sentence and the score is attributed to the aspect. Final aspect score = mean of all sentence scores mentioning that aspect.

---

## 📦 Dataset Schema

### products.csv
| Column | Type | Description |
|--------|------|-------------|
| product_id | string | Unique product ID / ASIN |
| brand | string | Brand name |
| title | string | Product title |
| category | string | Cabin / Medium / Large / Set |
| price | float | Selling price (₹) |
| list_price | float | MRP (₹) |
| discount_pct | float | Discount percentage |
| rating | float | Avg star rating (1–5) |
| review_count | int | Total reviews on Amazon |
| segment | string | Budget / Value / Mid / Premium |

### reviews.csv
| Column | Type | Description |
|--------|------|-------------|
| review_id | string | Unique review ID |
| product_id | string | Links to products.csv |
| brand | string | Brand name |
| rating | float | Star rating (1–5) |
| title | string | Review headline |
| body | string | Review text |
| date | date | Review date |
| verified_purchase | bool | Amazon verified badge |
| helpful_votes | int | Helpful upvotes |

---

## ⚠️ Known Limitations

1. **Scraper:** Amazon actively blocks scrapers. Without a proxy, you'll see CAPTCHAs after a few pages. The synthetic data generator provides a fully functional demo.

2. **Sentiment:** VADER doesn't understand sarcasm well ("Oh great, the wheel broke on day 1 😍"). A transformer model (e.g., RoBERTa) would improve accuracy at the cost of ~10x slower inference.

3. **Review count:** Amazon shows total reviews but only exposes ~10 per page. For high-volume products (1000+ reviews), we sample the most recent pages.

4. **Price volatility:** Amazon prices change daily. The dataset represents a point-in-time snapshot.

---

## 🎯 Brands Covered

| Brand | Segment | Avg Price |
|-------|---------|-----------|
| Safari | Mid-range | ₹4,500–6,500 |
| Skybags | Budget | ₹2,500–4,000 |
| American Tourister | Premium | ₹7,000–12,000 |
| VIP | Mid-range | ₹4,000–6,000 |
| Aristocrat | Budget | ₹2,000–3,500 |
| Nasher Miles | Mid-range | ₹5,000–7,500 |

---

## 🏗️ Architecture

```
[Amazon India] → [Scraper] → [Raw CSVs]
                                  ↓
                           [Data Cleaner]
                                  ↓
                    ┌─────────────┴─────────────┐
              [Sentiment Engine]         [Theme Extractor]
              (VADER + Aspects)          (Keyword Clustering)
                    └─────────────┬─────────────┘
                                  ↓
                          [Insights Engine]
                          (generate_insights)
                                  ↓
                      [Streamlit Dashboard]
                    ┌────────┬────────┬────────┐
                 Overview Comparison Drilldown Insights
```

---

