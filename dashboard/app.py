import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if ROOT not in sys.path:
    sys.path.insert(0, ROOT)

PRODUCTS_PATH = os.path.join(ROOT, "data", "cleaned", "products.csv")
REVIEWS_PATH  = os.path.join(ROOT, "data", "cleaned", "reviews.csv")

import streamlit as st
import pandas as pd

from scraper.data_cleaner import clean_products, clean_reviews
from analysis.sentiment import enrich_reviews_df, brand_sentiment_summary
from analysis.themes import brand_theme_summary, detect_anomalies
from analysis.insights import generate_insights

from dashboard.components.overview import render_overview
from dashboard.components.brand_comparison import render_brand_comparison
from dashboard.components.product_drilldown import render_product_drilldown
from dashboard.components.agent_insights import render_agent_insights

st.set_page_config(
    page_title="Luggage Intel — Amazon India",
    page_icon="🧳",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Dark theme CSS ─────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* ── Page background ── */
    .stApp { background-color: #0f1117; }
    .main .block-container {
        padding-top: 1.5rem;
        padding-bottom: 2rem;
        background-color: #0f1117;
    }

    /* ── Metric cards ── */
    [data-testid="metric-container"] {
        background: #1a1d27;
        border: 1px solid #2d3148;
        border-radius: 10px;
        padding: 12px 16px;
    }
    [data-testid="metric-container"] label  { color: #94a3b8 !important; }
    [data-testid="metric-container"] div[data-testid="metric-value"] {
        color: #e2e8f0 !important;
    }

    /* ── Tabs ── */
    .stTabs [data-baseweb="tab-list"] {
        gap: 6px;
        background-color: #1a1d27;
        border-radius: 10px;
        padding: 4px;
    }
    .stTabs [data-baseweb="tab"] {
        background-color: transparent;
        border-radius: 8px;
        padding: 8px 22px;
        color: #94a3b8;
        font-weight: 500;
        border: none;
    }
    .stTabs [aria-selected="true"] {
        background: linear-gradient(135deg, #7c6ff7, #5b54d4);
        color: #ffffff !important;
        font-weight: 600;
    }

    /* ── Sidebar ── */
    [data-testid="stSidebar"] {
        background-color: #13151f !important;
        border-right: 1px solid #2d3148;
    }
    [data-testid="stSidebar"] * { color: #cbd5e1 !important; }

    /* ── DataFrames / tables ── */
    [data-testid="stDataFrame"] { background-color: #1a1d27; border-radius: 8px; }

    /* ── Divider ── */
    hr { border-color: #2d3148 !important; }

    /* ── Selectbox / Multiselect ── */
    .stSelectbox > div > div,
    .stMultiSelect > div > div {
        background-color: #1a1d27 !important;
        border-color: #2d3148 !important;
        color: #e2e8f0 !important;
    }

    /* ── Slider ── */
    .stSlider [data-baseweb="slider"] { background-color: #2d3148; }

    /* ── Info / success / warning boxes ── */
    .stAlert { background-color: #1a1d27 !important; border-radius: 8px; }

    /* ── Brand badge ── */
    .brand-badge {
        display: inline-block;
        background: #2d3148;
        color: #a5b4fc;
        border-radius: 20px;
        padding: 3px 12px;
        font-size: 13px;
        font-weight: 600;
        margin: 2px;
    }

    /* ── Review cards ── */
    .review-card {
        border: 1px solid #2d3148;
        border-radius: 8px;
        padding: 12px 16px;
        margin: 8px 0;
        background: #1a1d27;
    }

    /* ── General text ── */
    h1, h2, h3, h4 { color: #e2e8f0 !important; }
    p, li, span     { color: #cbd5e1; }
    .stCaption, [data-testid="stCaptionContainer"] { color: #64748b !important; }

    /* ── Spinner ── */
    .stSpinner > div { color: #7c6ff7; }

    /* ── Radio buttons ── */
    .stRadio label { color: #cbd5e1 !important; }
</style>
""", unsafe_allow_html=True)


# ── Dark chart layout shared across all components ────────────────────────────
# Exported so every component can import and apply it to their Plotly figures.
DARK_LAYOUT = dict(
    paper_bgcolor = "#1a1d27",
    plot_bgcolor  = "#1a1d27",
    font          = dict(color="#cbd5e1", family="Inter, Arial, sans-serif"),
    xaxis         = dict(gridcolor="#2d3148", linecolor="#2d3148", zerolinecolor="#2d3148"),
    yaxis         = dict(gridcolor="#2d3148", linecolor="#2d3148", zerolinecolor="#2d3148"),
    legend        = dict(bgcolor="#1a1d27", bordercolor="#2d3148"),
    margin        = dict(l=10, r=10, t=10, b=10),
)


def ensure_data_exists():
    if not os.path.exists(PRODUCTS_PATH) or not os.path.exists(REVIEWS_PATH):
        st.info("⏳ First run — generating dataset (~10 seconds)...")
        try:
            import importlib.util
            spec = importlib.util.spec_from_file_location(
                "generate_data", os.path.join(ROOT, "generate_data.py")
            )
            gen = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(gen)
            gen.main()
            st.success(" Dataset ready!")
            st.rerun()
        except Exception as e:
            st.error(f"Failed to generate data: {e}")
            st.stop()


@st.cache_data(ttl=3600, show_spinner=False)
def load_data():
    products_df      = clean_products(pd.read_csv(PRODUCTS_PATH))
    reviews_df       = clean_reviews(pd.read_csv(REVIEWS_PATH))
    reviews_enriched = enrich_reviews_df(reviews_df)
    brand_sentiment  = brand_sentiment_summary(reviews_enriched)
    themes_by_brand  = brand_theme_summary(reviews_enriched)
    anomalies        = detect_anomalies(reviews_enriched, products_df)
    return products_df, reviews_enriched, brand_sentiment, themes_by_brand, anomalies


def render_sidebar(products_df):
    st.sidebar.image("https://img.icons8.com/fluency/48/luggage.png", width=40)
    st.sidebar.title("🧳 Luggage Intel")
    st.sidebar.caption("Amazon India Competitive Dashboard")
    st.sidebar.divider()

    all_brands = sorted(products_df["brand"].unique().tolist())
    selected_brands = st.sidebar.multiselect(
        "Select Brands", options=all_brands, default=all_brands
    )
    min_price = int(products_df["price"].min())
    max_price = int(products_df["price"].max())
    price_range = st.sidebar.slider(
        "Price Range (₹)", min_value=min_price, max_value=max_price,
        value=(min_price, max_price), step=500, format="₹%d"
    )
    min_rating = st.sidebar.select_slider(
        "Minimum Rating", options=[1.0, 2.0, 3.0, 3.5, 4.0, 4.5],
        value=1.0, format_func=lambda x: f"{x}★"
    )
    all_cats = ["All"] + sorted(products_df["category"].unique().tolist()) \
        if "category" in products_df.columns else ["All"]
    selected_category = st.sidebar.selectbox("Luggage Category", all_cats)

    st.sidebar.divider()
    st.sidebar.caption("Built for Moonshot AI Agent Internship")
    return selected_brands, price_range, min_rating, selected_category


def apply_filters(products_df, reviews_df, brands, price_range, min_rating, category):
    mask = (
        products_df["brand"].isin(brands) &
        (products_df["price"] >= price_range[0]) &
        (products_df["price"] <= price_range[1]) &
        (products_df["rating"] >= min_rating)
    )
    if category != "All" and "category" in products_df.columns:
        mask &= products_df["category"] == category
    filtered_products = products_df[mask]
    filtered_reviews  = reviews_df[
        reviews_df["brand"].isin(brands) &
        reviews_df["product_id"].isin(filtered_products["product_id"].tolist())
    ]
    return filtered_products, filtered_reviews


def main():
    ensure_data_exists()

    with st.spinner("Loading and analyzing data..."):
        products_df, reviews_df, brand_sentiment, themes_by_brand, anomalies = load_data()

    selected_brands, price_range, min_rating, selected_category = render_sidebar(products_df)

    if not selected_brands:
        st.warning("Select at least one brand from the sidebar.")
        st.stop()

    filtered_products, filtered_reviews = apply_filters(
        products_df, reviews_df, selected_brands, price_range, min_rating, selected_category
    )
    filtered_sentiment = brand_sentiment[brand_sentiment["brand"].isin(selected_brands)] \
        if brand_sentiment is not None else None
    filtered_themes = {k: v for k, v in themes_by_brand.items() if k in selected_brands} \
        if themes_by_brand else {}

    st.title("🧳 Luggage Brand Intelligence Dashboard")
    st.caption(
        f"Tracking **{len(selected_brands)} brands** · "
        f"**{len(filtered_products):,} products** · "
        f"**{len(filtered_reviews):,} reviews** · Amazon India"
    )

    tab1, tab2, tab3, tab4 = st.tabs([
        "📊 Overview", "🏷️ Brand Comparison",
        "🔍 Product Drilldown", "🤖 Agent Insights",
    ])

    with tab1:
        render_overview(filtered_products, filtered_reviews, filtered_sentiment)
    with tab2:
        render_brand_comparison(filtered_products, filtered_reviews, filtered_sentiment, filtered_themes)
    with tab3:
        render_product_drilldown(filtered_products, filtered_reviews, themes_by_brand)
    with tab4:
        render_agent_insights(
            filtered_products, filtered_reviews,
            filtered_sentiment, filtered_themes, anomalies or []
        )


if __name__ == "__main__":
    main()
