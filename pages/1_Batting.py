"""Batting stats page — sortable table + interactive charts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import web_data as db

st.set_page_config(page_title="Batting · Reading", page_icon="⚡", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚾ Reading Fightin Phils")
    st.markdown("**2025 · Double-A Northeast**")
    st.divider()

    st.markdown("**Filters**")
    min_pa = st.slider("Minimum Plate Appearances", 0, 400, 30, step=10)
    pos_options = ["All"] + sorted(db.batting()["position"].dropna().unique().tolist())
    pos_filter  = st.selectbox("Position", pos_options)
    bats_filter = st.radio("Bats", ["All", "L", "R", "S"])

st.title("⚡ Batting Stats — 2025")
st.caption("All regular-season stats via MLB Stats API · FIP constant = 3.10")

df = db.batting()

# Apply filters
df = df[df["pa"].fillna(0) >= min_pa]
if pos_filter != "All":
    df = df[df["position"] == pos_filter]
if bats_filter != "All":
    df = df[df["bats"] == bats_filter]

# ── Summary metrics ───────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Players shown", len(df))
c2.metric("Avg OPS",  f"{df['ops'].mean():.3f}"  if not df.empty else "—")
c3.metric("Avg AVG",  f"{df['avg'].mean():.3f}"  if not df.empty else "—")
c4.metric("Total HR", int(df["hr"].fillna(0).sum()) if not df.empty else 0)
c5.metric("Total SB", int(df["sb"].fillna(0).sum()) if not df.empty else 0)

st.divider()

# ── Stat table ────────────────────────────────────────────────────────────────
st.subheader("Full Batting Table")
st.caption("Click any column header to sort")

display_cols = {
    "player_name": "Player", "position": "Pos", "bats": "B",
    "games": "G", "pa": "PA", "ab": "AB", "runs": "R",
    "hits": "H", "doubles": "2B", "triples": "3B", "hr": "HR",
    "rbi": "RBI", "bb": "BB", "so": "K", "sb": "SB", "cs": "CS",
    "avg": "AVG", "obp": "OBP", "slg": "SLG", "ops": "OPS",
    "babip": "BABIP", "iso": "ISO", "bb_pct": "BB%", "k_pct": "K%",
    "xbh": "XBH", "gdp": "GDP",
}
table = df[list(display_cols.keys())].rename(columns=display_cols)

st.dataframe(
    table.reset_index(drop=True),
    use_container_width=True,
    height=420,
    column_config={
        "AVG":   st.column_config.NumberColumn(format="%.3f"),
        "OBP":   st.column_config.NumberColumn(format="%.3f"),
        "SLG":   st.column_config.NumberColumn(format="%.3f"),
        "OPS":   st.column_config.NumberColumn(format="%.3f"),
        "BABIP": st.column_config.NumberColumn(format="%.3f"),
        "ISO":   st.column_config.NumberColumn(format="%.3f"),
        "BB%":   st.column_config.NumberColumn(format="%.1%"),
        "K%":    st.column_config.NumberColumn(format="%.1%"),
    },
    hide_index=True,
)

st.divider()

# ── Charts ────────────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("OPS Leaders")
    top = df.nlargest(min(15, len(df)), "ops")
    fig = px.bar(
        top.sort_values("ops"),
        x="ops", y="player_name",
        orientation="h",
        color="ops",
        color_continuous_scale=["#4a0000", "#8B0000", "#FF6B6B"],
        labels={"ops": "OPS", "player_name": ""},
        hover_data={"avg": ":.3f", "obp": ":.3f", "slg": ":.3f", "hr": True, "rbi": True},
        text="ops",
    )
    fig.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        height=460,
        margin=dict(t=10, l=130, r=60),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("HR Leaders")
    top_hr = df.nlargest(min(15, len(df)), "hr")
    fig2 = px.bar(
        top_hr.sort_values("hr"),
        x="hr", y="player_name",
        orientation="h",
        color="hr",
        color_continuous_scale=["#0a0a2e", "#1a1a8e", "#4444FF"],
        labels={"hr": "Home Runs", "player_name": ""},
        hover_data={"rbi": True, "avg": ":.3f", "ops": ":.3f"},
        text="hr",
    )
    fig2.update_traces(texttemplate="%{text}", textposition="outside")
    fig2.update_layout(
        coloraxis_showscale=False,
        height=460,
        margin=dict(t=10, l=130, r=60),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Scatter: OPS vs PA ────────────────────────────────────────────────────────
st.subheader("OPS vs Plate Appearances")
st.caption("Bubble size = HR · Color = ISO (isolated power)")

scatter_df = df[df["pa"].fillna(0) > 10].copy()
if not scatter_df.empty:
    fig3 = px.scatter(
        scatter_df,
        x="pa", y="ops",
        size=scatter_df["hr"].clip(lower=1),
        color="iso",
        color_continuous_scale="RdYlGn",
        hover_name="player_name",
        hover_data={
            "pa": True, "ops": ":.3f", "avg": ":.3f",
            "hr": True, "rbi": True, "iso": ":.3f",
        },
        labels={"pa": "Plate Appearances", "ops": "OPS", "iso": "ISO"},
        size_max=30,
    )
    fig3.update_layout(
        height=420,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        coloraxis_colorbar=dict(title="ISO"),
    )
    # Label top 5 by OPS
    top5 = scatter_df.nlargest(5, "ops")
    for _, row in top5.iterrows():
        fig3.add_annotation(
            x=row["pa"], y=row["ops"],
            text=row["player_name"].split()[-1],
            showarrow=False, yshift=12,
            font=dict(size=10, color="#FFD700"),
        )
    st.plotly_chart(fig3, use_container_width=True)

# ── BB% vs K% quadrant ───────────────────────────────────────────────────────
st.subheader("Plate Discipline: Walk % vs Strikeout %")
st.caption("Top-left = best discipline (high BB%, low K%)")

disc_df = df[df["pa"].fillna(0) >= 30].dropna(subset=["bb_pct", "k_pct"])
if not disc_df.empty:
    avg_bb = disc_df["bb_pct"].mean()
    avg_k  = disc_df["k_pct"].mean()

    fig4 = px.scatter(
        disc_df,
        x="k_pct", y="bb_pct",
        color="ops",
        color_continuous_scale="RdYlGn",
        hover_name="player_name",
        hover_data={"k_pct": ":.1%", "bb_pct": ":.1%", "ops": ":.3f", "pa": True},
        labels={"k_pct": "Strikeout %", "bb_pct": "Walk %"},
    )
    fig4.add_vline(x=avg_k,  line_dash="dash", line_color="#555",
                   annotation_text="Avg K%", annotation_position="top right")
    fig4.add_hline(y=avg_bb, line_dash="dash", line_color="#555",
                   annotation_text="Avg BB%", annotation_position="right")
    fig4.update_layout(
        height=400,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        xaxis=dict(tickformat=".0%"),
        yaxis=dict(tickformat=".0%"),
    )
    top3 = disc_df.nlargest(3, "bb_pct")
    for _, row in top3.iterrows():
        fig4.add_annotation(
            x=row["k_pct"], y=row["bb_pct"],
            text=row["player_name"].split()[-1],
            showarrow=False, yshift=12,
            font=dict(size=10, color="#FFD700"),
        )
    st.plotly_chart(fig4, use_container_width=True)
