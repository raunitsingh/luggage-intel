import plotly.graph_objects as go
import plotly.express as px
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

_D    = dict(paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
             font=dict(color="#cbd5e1"), margin=dict(l=10,r=10,t=10,b=10))
_GRID = dict(gridcolor="#2d3148", linecolor="#2d3148", zerolinecolor="#2d3148")

def bc(b): return BRAND_COLORS.get(b, "#64748b")


def render_brand_comparison(products_df, reviews_df, brand_sentiment_df, themes_by_brand):
    st.subheader("🏷️ Brand Benchmarking")

    # ── Scorecard table ────────────────────────────────────────────────────────
    st.markdown("#### 📋 Full Brand Scorecard")
    agg = products_df.groupby("brand").agg(
        Products=("product_id","count"),
        Avg_Price=("price","mean"),
        Avg_Discount=("discount_pct","mean"),
        Avg_Rating=("rating","mean"),
        Total_Reviews=("review_count","sum"),
    ).reset_index()
    agg.columns = ["Brand","Products","Avg Price (₹)","Avg Discount %","Avg Rating ★","Total Reviews"]
    agg["Avg Price (₹)"]    = agg["Avg Price (₹)"].apply(lambda x: f"₹{x:,.0f}")
    agg["Avg Discount %"]   = agg["Avg Discount %"].apply(lambda x: f"{x:.1f}%")
    agg["Avg Rating ★"]     = agg["Avg Rating ★"].apply(lambda x: f"{x:.2f}")
    agg["Total Reviews"]    = agg["Total Reviews"].apply(lambda x: f"{x:,}")

    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        sm = brand_sentiment_df.set_index("brand")[["avg_sentiment_score","pct_positive","pct_negative"]].to_dict("index")
        agg["Sentiment"] = agg["Brand"].apply(lambda b: f"{sm.get(b,{}).get('avg_sentiment_score',0):.2f}")
        agg["% Positive"] = agg["Brand"].apply(lambda b: f"{sm.get(b,{}).get('pct_positive',0):.0f}%")
        agg["% Negative"] = agg["Brand"].apply(lambda b: f"{sm.get(b,{}).get('pct_negative',0):.0f}%")

    st.dataframe(agg, hide_index=True, use_container_width=True)
    st.divider()

    # ── Radar chart ───────────────────────────────────────────────────────────
    st.markdown("#### 🕸️ Multi-Metric Brand Radar")
    st.caption("Normalised 0–1. Larger area = stronger overall brand performance.")

    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        nums = products_df.groupby("brand").agg(
            avg_price=("price","mean"),
            avg_discount=("discount_pct","mean"),
            avg_rating=("rating","mean"),
            total_reviews=("review_count","sum"),
        ).reset_index().merge(
            brand_sentiment_df[["brand","avg_sentiment_score","pct_positive"]], on="brand", how="left"
        )

        def norm(s):
            r = s.max() - s.min()
            return (s - s.min()) / r if r > 0 else s * 0

        metrics = ["avg_rating","avg_sentiment_score","pct_positive","total_reviews"]
        labels  = ["Avg Rating","Sentiment","% Positive","Review Volume"]
        nums["discount_inv"] = 1 - norm(nums["avg_discount"])
        metrics.append("discount_inv"); labels.append("Brand Strength")

        for m in metrics:
            nums[m+"_n"] = norm(nums[m])

        fig = go.Figure()
        for _, row in nums.iterrows():
            vals = [row[m+"_n"] for m in metrics] + [row[metrics[0]+"_n"]]
            fig.add_trace(go.Scatterpolar(
                r=vals, theta=labels+[labels[0]],
                fill="toself", name=row["brand"],
                line=dict(color=bc(row["brand"]), width=2),
                fillcolor=bc(row["brand"]), opacity=0.2,
            ))
        fig.update_layout(
            **_D, height=480,
            polar=dict(
                bgcolor="#1a1d27",
                radialaxis=dict(visible=True, range=[0,1],
                                gridcolor="#2d3148", linecolor="#2d3148",
                                tickfont=dict(color="#64748b"), color="#64748b"),
                angularaxis=dict(gridcolor="#2d3148", linecolor="#2d3148",
                                 tickfont=dict(color="#cbd5e1")),
            ),
            legend=dict(bgcolor="#1a1d27", bordercolor="#2d3148", font=dict(color="#cbd5e1")),
        )
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Price gap + Discount bars ──────────────────────────────────────────────
    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### 💸 Selling Price vs MRP")
        pdf = products_df.groupby("brand").agg(
            selling=("price","mean"), mrp=("list_price","mean")
        ).reset_index()
        fig = go.Figure()
        fig.add_bar(x=pdf["brand"], y=pdf["mrp"], name="MRP",
                    marker_color="#2d3148",
                    text=[f"₹{v:,.0f}" for v in pdf["mrp"]], textposition="outside",
                    textfont=dict(color="#94a3b8"))
        fig.add_bar(x=pdf["brand"], y=pdf["selling"], name="Selling Price",
                    marker_color=[bc(b) for b in pdf["brand"]],
                    text=[f"₹{v:,.0f}" for v in pdf["selling"]], textposition="outside",
                    textfont=dict(color="#e2e8f0"))
        fig.update_layout(**_D, barmode="overlay", showlegend=True, height=320,
                          yaxis={**_GRID,"tickprefix":"₹"}, xaxis=_GRID)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown("#### 🎟️ Average Discount % by Brand")
        dd = products_df.groupby("brand")["discount_pct"].mean().reset_index().sort_values("discount_pct",ascending=False)
        fig = px.bar(dd, x="brand", y="discount_pct",
                     color="brand", color_discrete_map=BRAND_COLORS,
                     text=dd["discount_pct"].apply(lambda x: f"{x:.1f}%"),
                     labels={"discount_pct":"Avg Discount %","brand":""})
        fig.update_traces(textposition="outside", textfont_color="#e2e8f0")
        fig.update_layout(**_D, showlegend=False, height=320,
                          yaxis={**_GRID,"ticksuffix":"%"}, xaxis=_GRID)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Sentiment stacked bar ─────────────────────────────────────────────────
    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        st.markdown("#### 😊 Sentiment Distribution by Brand")
        fig = go.Figure()
        fig.add_bar(x=brand_sentiment_df["brand"], y=brand_sentiment_df["pct_positive"],
                    name="Positive", marker_color="#34d399",
                    text=[f"{v:.0f}%" for v in brand_sentiment_df["pct_positive"]],
                    textposition="inside", textfont=dict(color="#0f1117"))
        fig.add_bar(x=brand_sentiment_df["brand"], y=brand_sentiment_df["pct_neutral"],
                    name="Neutral",  marker_color="#475569",
                    text=[f"{v:.0f}%" for v in brand_sentiment_df["pct_neutral"]],
                    textposition="inside", textfont=dict(color="#e2e8f0"))
        fig.add_bar(x=brand_sentiment_df["brand"], y=brand_sentiment_df["pct_negative"],
                    name="Negative", marker_color="#f87171",
                    text=[f"{v:.0f}%" for v in brand_sentiment_df["pct_negative"]],
                    textposition="inside", textfont=dict(color="#0f1117"))
        fig.update_layout(**_D, barmode="stack", showlegend=True, height=320,
                          yaxis={**_GRID,"ticksuffix":"%","range":[0,100]}, xaxis=_GRID,
                          legend=dict(bgcolor="#1a1d27",bordercolor="#2d3148"))
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Themes ────────────────────────────────────────────────────────────────
    st.markdown("#### 🗣️ Top Themes per Brand")
    brands = sorted(themes_by_brand.keys())
    cols   = st.columns(min(len(brands), 3))
    for i, brand in enumerate(brands):
        themes = themes_by_brand.get(brand, {})
        with cols[i % 3]:
            color = bc(brand)
            st.markdown(
                f"<div style='border-left:3px solid {color};padding-left:10px;margin-bottom:8px;'>"
                f"<b style='color:{color};font-size:15px;'>{brand}</b></div>",
                unsafe_allow_html=True
            )
            st.markdown("✅ **Praise**")
            for item in themes.get("top_positives", [])[:3]:
                st.markdown(
                    f"<div style='background:#0d2b1e;border-left:2px solid #34d399;"
                    f"padding:6px 10px;border-radius:4px;margin:3px 0;font-size:13px;color:#a7f3d0;'>"
                    f"{item['theme']} <code style='background:#1a3a2e;color:#6ee7b7;'>{item['pct']}%</code></div>",
                    unsafe_allow_html=True
                )
            st.markdown("❌ **Complaints**")
            for item in themes.get("top_negatives", [])[:3]:
                st.markdown(
                    f"<div style='background:#2b0d0d;border-left:2px solid #f87171;"
                    f"padding:6px 10px;border-radius:4px;margin:3px 0;font-size:13px;color:#fca5a5;'>"
                    f"{item['theme']} <code style='background:#3b1515;color:#f87171;'>{item['pct']}%</code></div>",
                    unsafe_allow_html=True
                )
            st.markdown("---")

    st.divider()

    # ── Aspect heatmap ────────────────────────────────────────────────────────
    st.markdown("#### 🔬 Aspect-Level Sentiment Heatmap")
    st.caption("Green = positive, Red = negative, Grey = rarely mentioned.")

    if brand_sentiment_df is not None:
        acols = [c for c in brand_sentiment_df.columns if c.startswith("aspect_")]
        if acols:
            hm = brand_sentiment_df[["brand"]+acols].set_index("brand")
            hm.columns = [c.replace("aspect_","").title() for c in hm.columns]
            fig = px.imshow(
                hm,
                color_continuous_scale=["#f87171","#1a1d27","#34d399"],
                range_color=[-0.5, 0.8],
                aspect="auto", text_auto=".2f",
                labels=dict(color="Sentiment"),
            )
            fig.update_layout(**_D, height=300,
                              coloraxis_colorbar=dict(
                                  title="Score", tickfont=dict(color="#cbd5e1"),
                                  titlefont=dict(color="#cbd5e1")
                              ))
            fig.update_traces(textfont=dict(color="#e2e8f0"))
            st.plotly_chart(fig, use_container_width=True)
