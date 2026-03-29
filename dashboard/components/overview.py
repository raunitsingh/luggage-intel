import plotly.express as px
import plotly.graph_objects as go
import pandas as pd
import streamlit as st

BRAND_COLORS = {
    "Safari":             "#7c6ff7",
    "Skybags":            "#f59e0b",
    "American Tourister": "#34d399",
    "Vip":                "#f87171",
    "Aristocrat":         "#a78bfa",
    "Nasher Miles":       "#22d3ee",
}

# Dark chart base — applied to every figure
_D = dict(
    paper_bgcolor="#1a1d27",
    plot_bgcolor ="#1a1d27",
    font=dict(color="#cbd5e1", family="Inter, Arial, sans-serif"),
    margin=dict(l=10, r=30, t=10, b=10),
)
_GRID = dict(gridcolor="#2d3148", linecolor="#2d3148", zerolinecolor="#2d3148")


def bc(brand):
    return BRAND_COLORS.get(brand, "#64748b")


def render_overview(products_df, reviews_df, brand_sentiment_df):
    st.subheader("📊 Market Snapshot")

    # ── KPIs ──────────────────────────────────────────────────────────────────
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.metric("🏷️ Brands",          products_df["brand"].nunique())
    c2.metric("📦 Products",         f"{len(products_df):,}")
    c3.metric("💬 Reviews",          f"{len(reviews_df):,}")
    c4.metric("💸 Avg Price",        f"₹{products_df['price'].mean():,.0f}")
    c5.metric("🎟️ Avg Discount",     f"{products_df['discount_pct'].mean():.1f}%")

    st.divider()

    # ── Price + Sentiment bars ─────────────────────────────────────────────────
    left, right = st.columns(2)

    with left:
        st.markdown("#### Average Selling Price by Brand")
        df = products_df.groupby("brand")["price"].mean().reset_index().sort_values("price")
        fig = px.bar(
            df, x="price", y="brand", orientation="h",
            color="brand", color_discrete_map=BRAND_COLORS,
            text=df["price"].apply(lambda x: f"₹{x:,.0f}"),
            labels={"price": "Avg Price (₹)", "brand": ""},
        )
        fig.update_traces(textposition="outside", textfont_color="#e2e8f0")
        fig.update_layout(**_D, showlegend=False, height=280,
                          xaxis={**_GRID, "tickprefix": "₹"},
                          yaxis=_GRID)
        st.plotly_chart(fig, use_container_width=True)

    with right:
        st.markdown("#### Sentiment Score by Brand")
        if brand_sentiment_df is not None and not brand_sentiment_df.empty:
            df = brand_sentiment_df.sort_values("avg_sentiment_score")
            fig = px.bar(
                df, x="avg_sentiment_score", y="brand", orientation="h",
                color="avg_sentiment_score",
                color_continuous_scale=["#f87171", "#fbbf24", "#34d399"],
                range_color=[-0.5, 0.8],
                text=df["avg_sentiment_score"].apply(lambda x: f"{x:.2f}"),
                labels={"avg_sentiment_score": "Sentiment", "brand": ""},
            )
            fig.update_traces(textposition="outside", textfont_color="#e2e8f0")
            fig.update_layout(**_D, showlegend=False, coloraxis_showscale=False,
                              height=280, xaxis={**_GRID, "range": [-0.1, 0.9]},
                              yaxis=_GRID)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Positioning scatter ────────────────────────────────────────────────────
    st.markdown("#### 🎯 Brand Positioning Map — Price vs. Sentiment vs. Volume")
    st.caption("Bubble size = review volume. Top-right = premium with strong sentiment.")

    agg = products_df.groupby("brand").agg(
        avg_price=("price","mean"),
        avg_discount=("discount_pct","mean"),
        avg_rating=("rating","mean"),
        total_reviews=("review_count","sum"),
    ).reset_index()

    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        agg = agg.merge(brand_sentiment_df[["brand","avg_sentiment_score"]], on="brand", how="left")
    else:
        agg["avg_sentiment_score"] = agg["avg_rating"] / 5.0

    fig = px.scatter(
        agg, x="avg_price", y="avg_sentiment_score",
        size="total_reviews", color="brand",
        color_discrete_map=BRAND_COLORS,
        text="brand", size_max=60,
        labels={"avg_price":"Avg Price (₹)","avg_sentiment_score":"Sentiment Score"},
        hover_data={"avg_price":":,.0f","avg_sentiment_score":":.2f",
                    "avg_rating":":.1f","avg_discount":":.1f","total_reviews":":,"},
    )
    mid_p = agg["avg_price"].median()
    mid_s = agg["avg_sentiment_score"].median()
    fig.add_vline(x=mid_p, line_dash="dot", line_color="#3d4268", opacity=0.8)
    fig.add_hline(y=mid_s, line_dash="dot", line_color="#3d4268", opacity=0.8)
    fig.add_annotation(x=agg["avg_price"].max()*1.0, y=agg["avg_sentiment_score"].max()*0.98,
                       text="Premium ⭐", showarrow=False, font=dict(color="#34d399", size=11))
    fig.add_annotation(x=agg["avg_price"].min()*0.9, y=agg["avg_sentiment_score"].max()*0.98,
                       text="Best Value 💰", showarrow=False, font=dict(color="#7c6ff7", size=11))
    fig.update_traces(textposition="top center", textfont=dict(color="#e2e8f0"))
    fig.update_layout(**_D, showlegend=False, height=420,
                      xaxis={**_GRID,"tickprefix":"₹"},
                      yaxis=_GRID)
    st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Discount vs rating ─────────────────────────────────────────────────────
    st.markdown("#### 🏷️ Discount Dependency vs. Customer Rating")
    st.caption("High discount + low rating = using price cuts to mask quality problems.")

    fig2 = px.scatter(
        agg, x="avg_discount", y="avg_rating",
        size="total_reviews", color="brand",
        color_discrete_map=BRAND_COLORS,
        text="brand", size_max=50,
        labels={"avg_discount":"Avg Discount %","avg_rating":"Avg Star Rating"},
    )
    fig2.update_traces(textposition="top center", textfont=dict(color="#e2e8f0"))
    fig2.update_layout(**_D, showlegend=False, height=350,
                       xaxis={**_GRID,"ticksuffix":"%"},
                       yaxis={**_GRID,"range":[1,5.5]})
    st.plotly_chart(fig2, use_container_width=True)

    st.divider()

    # ── Violin ────────────────────────────────────────────────────────────────
    st.markdown("#### 📦 Product Rating Distribution by Brand")
    st.caption("Wide sections = many products at that rating level.")

    fig3 = go.Figure()
    for brand in sorted(products_df["brand"].unique()):
        sub = products_df[products_df["brand"] == brand]
        fig3.add_trace(go.Violin(
            x=[brand]*len(sub), y=sub["rating"],
            name=brand, box_visible=True, meanline_visible=True,
            fillcolor=bc(brand), opacity=0.75, line_color="#2d3148",
        ))
    fig3.update_layout(**_D, showlegend=False, height=320,
                       yaxis={**_GRID,"range":[0.5,5.5],"title":"Star Rating"},
                       xaxis={**_GRID})
    st.plotly_chart(fig3, use_container_width=True)
