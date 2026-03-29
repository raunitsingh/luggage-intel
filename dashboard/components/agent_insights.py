import plotly.express as px
import pandas as pd
import numpy as np
import streamlit as st

from analysis.insights import generate_insights

BRAND_COLORS = {
    "Safari":             "#7c6ff7",
    "Skybags":            "#f59e0b",
    "American Tourister": "#34d399",
    "Vip":                "#f87171",
    "Aristocrat":         "#a78bfa",
    "Nasher Miles":       "#22d3ee",
}

_D    = dict(paper_bgcolor="#1a1d27", plot_bgcolor="#1a1d27",
             font=dict(color="#cbd5e1"), margin=dict(l=10,r=40,t=10,b=10))
_GRID = dict(gridcolor="#2d3148", linecolor="#2d3148", zerolinecolor="#2d3148")

def bc(b): return BRAND_COLORS.get(b, "#64748b")


def render_insight_card(insight):
    cat_colors = {
        "Value":"#34d399","Quality":"#f87171",
        "Pricing":"#f59e0b","Market":"#7c6ff7","Trend":"#22d3ee"
    }
    color = cat_colors.get(insight.get("category",""), "#a78bfa")
    st.markdown(
        f"""<div style="
            border-left:4px solid {color};
            background:linear-gradient(to right,{color}18,#1a1d27);
            border-radius:8px;padding:14px 18px;margin:10px 0;">
            <div style="font-size:16px;font-weight:700;color:#e2e8f0;margin-bottom:6px;">
                {insight.get('title','')}
            </div>
            <div style="font-size:14px;color:#94a3b8;line-height:1.6;">
                {insight.get('body','')}
            </div>
            <div style="margin-top:8px;">
                <span style="background:{color}22;color:{color};border-radius:12px;
                padding:2px 10px;font-size:12px;font-weight:600;">
                {insight.get('category','')}</span>
            </div></div>""",
        unsafe_allow_html=True
    )


def render_anomaly_card(anomaly):
    sev_colors = {"High":"#f87171","Medium":"#f59e0b","Low":"#34d399"}
    color = sev_colors.get(anomaly.get("severity","Low"), "#64748b")
    st.markdown(
        f"""<div style="border:1.5px solid {color};border-radius:8px;
            padding:14px 18px;margin:8px 0;background:{color}10;">
            <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:6px;">
                <span style="font-size:15px;font-weight:700;color:#e2e8f0;">
                    ⚡ {anomaly.get('brand','')} — {anomaly.get('type','')}
                </span>
                <span style="background:{color};color:#0f1117;border-radius:12px;
                padding:2px 10px;font-size:12px;font-weight:700;">
                {anomaly.get('severity','')} Risk</span>
            </div>
            <div style="font-size:14px;color:#94a3b8;line-height:1.6;">
                {anomaly.get('description','')}
            </div></div>""",
        unsafe_allow_html=True
    )


def render_agent_insights(products_df, reviews_df, brand_sentiment_df, themes_by_brand, anomalies):
    st.subheader("🤖 Agent Insights")
    st.caption("Automatically generated, data-driven conclusions — not just charts. Each insight is actionable.")

    # ── Key conclusions ────────────────────────────────────────────────────────
    with st.spinner("Generating insights..."):
        insights = generate_insights(products_df, reviews_df, brand_sentiment_df, themes_by_brand)

    st.markdown("### 💡 Key Conclusions")
    for insight in insights:
        render_insight_card(insight)

    st.divider()

    # ── Anomalies ─────────────────────────────────────────────────────────────
    st.markdown("### ⚡ Anomalies & Red Flags")
    st.caption("Unusual patterns: quality issues, fake review signals, or strategic missteps.")

    active_brands = products_df["brand"].unique()
    shown = [a for a in anomalies if a.get("brand") in active_brands]
    if shown:
        for a in shown:
            render_anomaly_card(a)
    else:
        st.success("✅ No significant anomalies detected.")

    st.divider()

    # ── Value-for-money index ──────────────────────────────────────────────────
    st.markdown("### 💰 Value-for-Money Index")
    st.caption("Sentiment score adjusted per rupee — high sentiment at low price wins.")

    agg = products_df.groupby("brand").agg(avg_price=("price","mean")).reset_index()
    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        agg = agg.merge(brand_sentiment_df[["brand","avg_sentiment_score"]], on="brand", how="left")
        agg["value_index"] = agg.apply(
            lambda r: (r["avg_sentiment_score"] / np.log10(r["avg_price"])) * 10
            if r["avg_price"] > 0 else 0, axis=1
        ).round(3)
        agg = agg.sort_values("value_index", ascending=True)

        fig = px.bar(
            agg, x="value_index", y="brand", orientation="h",
            color="value_index",
            color_continuous_scale=["#f87171","#f59e0b","#34d399"],
            text=agg["value_index"].apply(lambda x: f"{x:.2f}"),
            labels={"value_index":"Value Index","brand":""},
        )
        fig.update_traces(textposition="outside", textfont_color="#e2e8f0")
        fig.update_layout(**_D, showlegend=False, coloraxis_showscale=False,
                          height=280, xaxis=_GRID, yaxis=_GRID)
        st.plotly_chart(fig, use_container_width=True)

    st.divider()

    # ── Aspect winners ─────────────────────────────────────────────────────────
    st.markdown("### 🏆 Aspect-Level Winners")
    st.caption("Which brand wins on each product dimension?")

    if brand_sentiment_df is not None:
        acols = [c for c in brand_sentiment_df.columns if c.startswith("aspect_")]
        if acols:
            winners = {}
            for col in acols:
                aspect = col.replace("aspect_","").title()
                idx = brand_sentiment_df[col].idxmax()
                if pd.notna(idx):
                    winners[aspect] = {
                        "brand": brand_sentiment_df.loc[idx,"brand"],
                        "score": brand_sentiment_df.loc[idx, col],
                    }
            if winners:
                cols = st.columns(min(len(winners), 4))
                for i, (aspect, data) in enumerate(winners.items()):
                    color = bc(data["brand"])
                    with cols[i % 4]:
                        st.markdown(
                            f"""<div style="border:1.5px solid {color};border-radius:10px;
                                padding:12px;text-align:center;margin:4px 0;background:#13151f;">
                                <div style="font-size:12px;color:#64748b;">{aspect}</div>
                                <div style="font-size:15px;font-weight:700;color:{color};margin:4px 0;">
                                    {data['brand']}</div>
                                <div style="font-size:12px;color:#475569;">
                                    score: {data['score']:.2f}</div>
                            </div>""",
                            unsafe_allow_html=True
                        )

    st.divider()

    # ── Trust signals ─────────────────────────────────────────────────────────
    st.markdown("### 🛡️ Review Trust Signals")
    st.caption("High 5★% + low 1★% + short reviews = possible review inflation.")

    trust_rows = []
    for brand, grp in reviews_df.groupby("brand"):
        if brand not in active_brands:
            continue
        verified_pct  = grp["verified_purchase"].mean() * 100
        five_star_pct = (grp["rating"] == 5).sum() / len(grp) * 100
        one_star_pct  = (grp["rating"] == 1).sum() / len(grp) * 100
        avg_words     = grp["word_count"].mean() if "word_count" in grp.columns else 0
        signal = ("🔴 Suspicious" if five_star_pct > 75 and one_star_pct < 2
                  else "🟡 Borderline" if five_star_pct > 65 else "🟢 Normal")
        trust_rows.append({
            "Brand": brand,
            "Verified %": f"{verified_pct:.0f}%",
            "5★ %": f"{five_star_pct:.0f}%",
            "1★ %": f"{one_star_pct:.0f}%",
            "Avg Review Length": f"{avg_words:.0f} words",
            "Trust Signal": signal,
        })

    if trust_rows:
        st.dataframe(pd.DataFrame(trust_rows), hide_index=True, use_container_width=True)

    st.divider()

    # ── Decision recommendation ────────────────────────────────────────────────
    st.markdown("### 🧭 Decision Recommendation")

    if brand_sentiment_df is not None and not brand_sentiment_df.empty:
        m = products_df.groupby("brand").agg(
            avg_price=("price","mean"), avg_discount=("discount_pct","mean")
        ).reset_index().merge(brand_sentiment_df, on="brand", how="left")

        best_overall = m.loc[m["avg_sentiment_score"].idxmax(), "brand"]
        budget_df    = m[m["avg_price"] < 3500]
        best_budget  = budget_df.loc[budget_df["avg_sentiment_score"].idxmax(),"brand"] \
                       if not budget_df.empty else "N/A"
        least_disc   = m.loc[m["avg_discount"].idxmin(), "brand"]

        c1, c2, c3 = st.columns(3)
        c1.markdown(
            f"<div style='background:#0d2b1e;border:1px solid #34d399;border-radius:8px;"
            f"padding:16px;text-align:center;'>"
            f"<div style='color:#6ee7b7;font-size:12px;'>🏆 BEST OVERALL</div>"
            f"<div style='color:#34d399;font-size:20px;font-weight:700;margin:8px 0;'>{best_overall}</div>"
            f"<div style='color:#475569;font-size:12px;'>Highest sentiment across all price points</div>"
            f"</div>", unsafe_allow_html=True
        )
        c2.markdown(
            f"<div style='background:#131b2e;border:1px solid #7c6ff7;border-radius:8px;"
            f"padding:16px;text-align:center;'>"
            f"<div style='color:#a5b4fc;font-size:12px;'>💰 BEST BUDGET</div>"
            f"<div style='color:#7c6ff7;font-size:20px;font-weight:700;margin:8px 0;'>{best_budget}</div>"
            f"<div style='color:#475569;font-size:12px;'>Top satisfaction under ₹3,500</div>"
            f"</div>", unsafe_allow_html=True
        )
        c3.markdown(
            f"<div style='background:#2b1a0d;border:1px solid #f59e0b;border-radius:8px;"
            f"padding:16px;text-align:center;'>"
            f"<div style='color:#fcd34d;font-size:12px;'>💎 STRONGEST BRAND</div>"
            f"<div style='color:#f59e0b;font-size:20px;font-weight:700;margin:8px 0;'>{least_disc}</div>"
            f"<div style='color:#475569;font-size:12px;'>Lowest discount dependency — sells itself</div>"
            f"</div>", unsafe_allow_html=True
        )
