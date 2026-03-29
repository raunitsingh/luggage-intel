import plotly.express as px
import pandas as pd
import streamlit as st

from analysis.themes import product_theme_summary

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


def render_star_rating(rating):
    full  = int(rating)
    half  = 1 if rating - full >= 0.5 else 0
    empty = 5 - full - half
    return "⭐" * full + "✨" * half + "☆" * empty


def render_product_drilldown(products_df, reviews_df, themes_by_brand):
    st.subheader("🔍 Product Deep Dive")

    # ── Selectors ─────────────────────────────────────────────────────────────
    col1, col2, col3 = st.columns([1.5, 1.5, 1])

    with col1:
        selected_brand = st.selectbox("Select Brand", sorted(products_df["brand"].unique()))

    with col2:
        bp = products_df[products_df["brand"] == selected_brand]
        labels = {
            pid: (row["title"][:55]+"...") if len(row["title"]) > 55 else row["title"]
            for pid, row in bp.set_index("product_id").iterrows()
        }
        selected_pid = st.selectbox("Select Product", options=bp["product_id"].tolist(),
                                    format_func=lambda p: labels.get(p, p))

    with col3:
        sort_by = st.selectbox("Sort Reviews By",
                               ["Most Recent","Highest Rating","Lowest Rating","Most Helpful"])

    product = products_df[products_df["product_id"] == selected_pid].iloc[0]
    pr = reviews_df[reviews_df["product_id"] == selected_pid].copy()

    if sort_by == "Most Recent" and "date" in pr.columns:
        pr = pr.sort_values("date", ascending=False)
    elif sort_by == "Highest Rating":
        pr = pr.sort_values("rating", ascending=False)
    elif sort_by == "Lowest Rating":
        pr = pr.sort_values("rating", ascending=True)
    elif sort_by == "Most Helpful":
        pr = pr.sort_values("helpful_votes", ascending=False)

    st.divider()

    # ── Product card ──────────────────────────────────────────────────────────
    color = bc(product["brand"])
    left, right = st.columns([3, 2])

    with left:
        st.markdown(
            f"<div style='border-left:4px solid {color};padding-left:14px;'>"
            f"<h3 style='color:#e2e8f0;margin:0;'>{product['title']}</h3></div>",
            unsafe_allow_html=True
        )
        st.markdown(
            f"<span class='brand-badge'>{product['brand']}</span>"
            f"<span class='brand-badge'>{product.get('category','N/A')}</span>",
            unsafe_allow_html=True
        )
        st.markdown(f"**Rating:** {render_star_rating(product['rating'])} ({product['rating']:.1f}/5)")

    with right:
        ca, cb = st.columns(2)
        ca.metric("Selling Price", f"₹{product['price']:,.0f}")
        cb.metric("MRP",           f"₹{product['list_price']:,.0f}")
        ca.metric("Discount",      f"{product['discount_pct']:.1f}%")
        cb.metric("You Save",      f"₹{product['list_price']-product['price']:,.0f}")

    st.divider()

    # ── Review stats ──────────────────────────────────────────────────────────
    if not pr.empty:
        st.markdown("#### 📊 Review Analytics")
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Reviews",     f"{len(pr):,}")
        c2.metric("Avg Sentiment",
                  f"{pr['compound_score'].mean():.2f}" if "compound_score" in pr.columns else "N/A")
        c3.metric("Verified",    f"{pr['verified_purchase'].sum():,}")
        c4.metric("% Positive",  f"{(pr['rating']>=4).sum()/len(pr)*100:.0f}%")

        # Rating bar breakdown
        counts = pr["rating"].value_counts().sort_index(ascending=False)
        total  = len(pr)
        st.markdown("**Rating Breakdown**")
        for star in [5, 4, 3, 2, 1]:
            count   = counts.get(star, 0)
            pct     = count / total * 100
            bar_w   = int(pct * 2.4)
            bar_col = color
            st.markdown(
                f"<div style='display:flex;align-items:center;gap:10px;margin:3px 0;'>"
                f"<span style='color:#94a3b8;width:20px;text-align:right;'>{star}★</span>"
                f"<div style='flex:1;max-width:240px;background:#2d3148;border-radius:4px;height:10px;'>"
                f"<div style='background:{bar_col};border-radius:4px;width:{bar_w}%;height:10px;'></div></div>"
                f"<span style='color:#64748b;font-size:13px;'>{count} ({pct:.0f}%)</span>"
                f"</div>",
                unsafe_allow_html=True
            )

    st.divider()

    # ── Themes ────────────────────────────────────────────────────────────────
    st.markdown("#### 🗣️ What Customers Are Saying")
    themes = product_theme_summary(reviews_df, selected_pid)
    col_pos, col_neg = st.columns(2)

    with col_pos:
        st.markdown("##### ✅ Top Praise")
        for item in themes.get("top_positives", [])[:6]:
            st.markdown(
                f"<div style='background:#0d2b1e;border-left:3px solid #34d399;"
                f"padding:8px 12px;border-radius:6px;margin:5px 0;'>"
                f"<b style='color:#6ee7b7;'>{item['theme']}</b>"
                f"<span style='color:#475569;font-size:12px;'> — {item['pct']}% of reviews</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        if not themes.get("top_positives"):
            st.info("No recurring praise found.")

    with col_neg:
        st.markdown("##### ❌ Top Complaints")
        for item in themes.get("top_negatives", [])[:6]:
            st.markdown(
                f"<div style='background:#2b0d0d;border-left:3px solid #f87171;"
                f"padding:8px 12px;border-radius:6px;margin:5px 0;'>"
                f"<b style='color:#fca5a5;'>{item['theme']}</b>"
                f"<span style='color:#475569;font-size:12px;'> — {item['pct']}% of reviews</span>"
                f"</div>",
                unsafe_allow_html=True
            )
        if not themes.get("top_negatives"):
            st.success("No recurring complaints. 🎉")

    st.divider()

    # ── Sentiment timeline ────────────────────────────────────────────────────
    if "date" in pr.columns and "compound_score" in pr.columns:
        st.markdown("#### 📈 Sentiment Over Time")
        tl = pr.copy()
        tl["date"] = pd.to_datetime(tl["date"], errors="coerce")
        tl = tl.dropna(subset=["date"]).sort_values("date")
        if len(tl) > 5:
            tl["rolling"] = tl["compound_score"].rolling(10, min_periods=3).mean()
            fig = px.line(tl, x="date", y="rolling",
                          color_discrete_sequence=[color],
                          labels={"date":"Review Date","rolling":"Sentiment (10-review rolling avg)"})
            fig.add_hline(y=0, line_dash="dot", line_color="#475569")
            fig.update_layout(**_D, height=250, xaxis=_GRID, yaxis=_GRID)
            st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Reviews browser ───────────────────────────────────────────────────────
    st.markdown("#### 💬 Customer Reviews")
    sent_filter = st.radio("Show", ["All","Positive Only","Negative Only"], horizontal=True)

    display = pr.copy()
    if sent_filter == "Positive Only" and "sentiment_label" in display.columns:
        display = display[display["sentiment_label"] == "Positive"]
    elif sent_filter == "Negative Only" and "sentiment_label" in display.columns:
        display = display[display["sentiment_label"] == "Negative"]

    for _, rev in display.head(15).iterrows():
        label = rev.get("sentiment_label","")
        lc = "#34d399" if label=="Positive" else "#f87171" if label=="Negative" else "#64748b"
        date_str  = str(rev.get("date",""))[:10] if pd.notna(rev.get("date")) else ""
        verified  = "✓ Verified" if rev.get("verified_purchase") else ""
        stars     = "⭐" * int(rev["rating"])

        st.markdown(
            f"<div style='border:1px solid #2d3148;border-radius:8px;"
            f"padding:12px 16px;margin:8px 0;background:#1a1d27;'>"
            f"<div style='display:flex;justify-content:space-between;align-items:center;'>"
            f"<span style='font-weight:600;color:#e2e8f0;'>{rev.get('title','')}</span>"
            f"<span style='color:{lc};font-size:12px;font-weight:600;'>● {label}</span></div>"
            f"<div style='color:#64748b;font-size:13px;margin:3px 0;'>"
            f"{stars} &nbsp; {date_str} &nbsp;"
            f"<span style='color:#34d399;'>{verified}</span></div>"
            f"<div style='color:#94a3b8;margin-top:8px;line-height:1.5;'>{rev.get('body','')}</div>"
            f"</div>",
            unsafe_allow_html=True
        )

    if len(display) > 15:
        st.caption(f"Showing 15 of {len(display)} reviews.")
