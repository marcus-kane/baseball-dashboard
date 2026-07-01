"""Phillies org-wide overview — all three levels side by side."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

import web_data as db
from config import ORG_TEAMS

st.set_page_config(page_title="Org Overview · Phillies", page_icon="⚾", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #C41632; padding-left: 10px; }
.level-mlb  { color: #E41134; font-weight: bold; }
.level-aaa  { color: #FFD700; font-weight: bold; }
.level-aa   { color: #8B0000; font-weight: bold; }
</style>
""", unsafe_allow_html=True)

LEVEL_COLORS = {"MLB": "#E41134", "AAA": "#FFD700", "AA": "#8B0000"}

with st.sidebar:
    st.markdown("## Philadelphia Phillies")
    st.markdown("**Full Organization**")
    st.divider()
    seasons = db.seasons_available()
    season  = st.selectbox("Season", seasons, index=0)
    st.divider()
    st.caption("Data: MLB Stats API")

st.title("Philadelphia Phillies Organization")
st.caption(f"MLB · AAA · AA  —  {season} Season")
st.divider()

bat_sum = db.org_batting_summary(season)
pit_sum = db.org_pitching_summary(season)

# ── Level header cards ────────────────────────────────────────────────────────
cols = st.columns(3)
for i, team in enumerate(ORG_TEAMS):
    level = team["level"]
    color = LEVEL_COLORS[level]
    b = bat_sum[bat_sum["org_level"] == level]
    p = pit_sum[pit_sum["org_level"] == level]

    b_ops  = f"{b['avg_ops'].iloc[0]:.3f}"  if not b.empty and b["avg_ops"].notna().any()  else "—"
    b_avg  = f"{b['avg_avg'].iloc[0]:.3f}"  if not b.empty and b["avg_avg"].notna().any()  else "—"
    p_era  = f"{p['team_era'].iloc[0]:.2f}" if not p.empty and p["team_era"].notna().any() else "—"
    p_whip = f"{p['team_whip'].iloc[0]:.2f}"if not p.empty and p["team_whip"].notna().any()else "—"
    total_hr = int(b["total_hr"].iloc[0]) if not b.empty and b["total_hr"].notna().any() else 0
    total_k  = int(p["total_k"].iloc[0])  if not p.empty and p["total_k"].notna().any()  else 0

    with cols[i]:
        st.markdown(f"<h3 style='color:{color};text-align:center'>{level}</h3>", unsafe_allow_html=True)
        st.markdown(f"<p style='text-align:center;color:#aaa;font-size:0.85rem'>{team['team_name']}</p>",
                    unsafe_allow_html=True)
        m1, m2 = st.columns(2)
        m1.metric("OPS",  b_ops)
        m2.metric("AVG",  b_avg)
        m3, m4 = st.columns(2)
        m3.metric("ERA",  p_era)
        m4.metric("WHIP", p_whip)
        m5, m6 = st.columns(2)
        m5.metric("HR",   total_hr)
        m6.metric("K",    total_k)

st.divider()

# ── Side-by-side batting comparison ───────────────────────────────────────────
st.subheader("Batting — Org Comparison")

if not bat_sum.empty:
    metrics = ["avg_ops", "avg_avg", "avg_obp", "avg_slg"]
    labels  = {"avg_ops":"OPS","avg_avg":"AVG","avg_obp":"OBP","avg_slg":"SLG"}

    fig = go.Figure()
    for _, row in bat_sum.iterrows():
        level = str(row.get("org_level", ""))
        color = LEVEL_COLORS.get(level, "#888")
        vals  = [row.get(m, 0) or 0 for m in metrics]
        fig.add_bar(
            name=level,
            x=[labels[m] for m in metrics],
            y=vals,
            marker_color=color,
            text=[f"{v:.3f}" for v in vals],
            textposition="outside",
        )
    fig.update_layout(
        barmode="group",
        height=350,
        margin=dict(t=10, b=40),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
        yaxis=dict(range=[0, max(bat_sum["avg_ops"].max() * 1.15, 0.1)]),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Side-by-side pitching comparison ─────────────────────────────────────────
st.subheader("Pitching — Org Comparison")

if not pit_sum.empty:
    col_p1, col_p2 = st.columns(2)
    with col_p1:
        fig2 = go.Figure()
        for _, row in pit_sum.iterrows():
            level = str(row.get("org_level", ""))
            color = LEVEL_COLORS.get(level, "#888")
            fig2.add_bar(
                name=level, x=[level], y=[row.get("team_era", 0) or 0],
                marker_color=color,
                text=[f"{row.get('team_era',0):.2f}"],
                textposition="outside",
            )
        fig2.add_hline(y=4.0, line_dash="dash", line_color="#555", annotation_text="4.00 ERA")
        fig2.update_layout(
            title="Team ERA by Level", showlegend=False,
            height=300, margin=dict(t=40, b=10),
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
            yaxis_title="ERA",
        )
        st.plotly_chart(fig2, use_container_width=True)

    with col_p2:
        fig3 = go.Figure()
        for _, row in pit_sum.iterrows():
            level = str(row.get("org_level", ""))
            color = LEVEL_COLORS.get(level, "#888")
            fig3.add_bar(
                name=level, x=[level], y=[row.get("k9", 0) or 0],
                marker_color=color,
                text=[f"{row.get('k9',0):.2f}"],
                textposition="outside",
            )
        fig3.update_layout(
            title="K/9 by Level", showlegend=False,
            height=300, margin=dict(t=40, b=10),
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
            yaxis_title="K/9",
        )
        st.plotly_chart(fig3, use_container_width=True)

st.divider()

# ── Top performers across org ─────────────────────────────────────────────────
st.subheader("Top Performers Across the Org")

all_bat = db.batting(season=season)
all_pit = db.pitching(season=season)

col_b, col_p = st.columns(2)

with col_b:
    st.markdown("**OPS Leaders — All Levels** *(min 50 PA)*")
    qual = all_bat[all_bat["pa"].fillna(0) >= 50].nlargest(10, "ops")
    if not qual.empty:
        display = qual[["player_name","org_level","team_name","pa","avg","ops","hr","rbi"]].copy()
        display = display.rename(columns={
            "player_name":"Player","org_level":"Level","team_name":"Team",
            "pa":"PA","avg":"AVG","ops":"OPS","hr":"HR","rbi":"RBI"
        }).reset_index(drop=True)
        display.index += 1
        st.dataframe(display, use_container_width=True, hide_index=False,
                     column_config={
                         "AVG": st.column_config.NumberColumn(format="%.3f"),
                         "OPS": st.column_config.NumberColumn(format="%.3f"),
                     })

with col_p:
    st.markdown("**ERA Leaders — All Levels** *(min 20 IP)*")
    qual_p = all_pit[all_pit["ip"].fillna(0) >= 20].nsmallest(10, "era")
    if not qual_p.empty:
        display_p = qual_p[["player_name","org_level","team_name","ip","era","whip","k9","fip"]].copy()
        display_p = display_p.rename(columns={
            "player_name":"Player","org_level":"Level","team_name":"Team",
            "ip":"IP","era":"ERA","whip":"WHIP","k9":"K/9","fip":"FIP"
        }).reset_index(drop=True)
        display_p["IP"] = display_p["IP"].round(1)
        display_p.index += 1
        st.dataframe(display_p, use_container_width=True, hide_index=False,
                     column_config={
                         "ERA":  st.column_config.NumberColumn(format="%.2f"),
                         "WHIP": st.column_config.NumberColumn(format="%.2f"),
                         "FIP":  st.column_config.NumberColumn(format="%.2f"),
                         "K/9":  st.column_config.NumberColumn(format="%.2f"),
                     })

# ── OPS scatter across org ────────────────────────────────────────────────────
st.divider()
st.subheader("OPS vs PA — Full Org")

scatter_df = all_bat[all_bat["pa"].fillna(0) >= 20].copy()
if not scatter_df.empty:
    scatter_df["org_level"] = scatter_df["org_level"].fillna("Unknown")
    fig4 = px.scatter(
        scatter_df,
        x="pa", y="ops",
        color="org_level",
        color_discrete_map=LEVEL_COLORS,
        size=scatter_df["hr"].clip(lower=1),
        size_max=25,
        hover_name="player_name",
        hover_data={"pa":True,"ops":":.3f","avg":":.3f","hr":True,"team_name":True},
        labels={"pa":"Plate Appearances","ops":"OPS","org_level":"Level"},
    )
    fig4.update_layout(
        height=420,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
        legend=dict(title="Level", orientation="h", y=1.05),
    )
    st.plotly_chart(fig4, use_container_width=True)
