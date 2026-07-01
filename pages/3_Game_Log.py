"""Game log page — full schedule table + score timeline + opponent breakdown."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

import web_data as db
import sidebar as sb
from config import TEAM_BY_ID

st.set_page_config(page_title="Game Log · Phillies Org", page_icon="📅", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

season, team_id = sb.render("Game Log")

# Game log requires a specific team; default to Reading (AA) if All Levels chosen
display_team_id = team_id or 522
df = db.games(season=season, team_id=display_team_id)

team_label = TEAM_BY_ID.get(display_team_id, {}).get("team_name", "Team")

with st.sidebar:
    st.divider()
    st.markdown("**Filters**")

    result_filter = st.radio("Result", ["All", "Wins", "Losses"])
    ha_filter     = st.radio("Home / Away", ["All", "Home", "Away"])

    opponents = sorted(df["opponent_name"].dropna().unique().tolist()) if not df.empty else []
    opp_filter = st.selectbox("Opponent", ["All"] + opponents)

    if not df.empty:
        months = sorted(df["game_date"].dt.month.unique().tolist())
        month_names = {3:"March",4:"April",5:"May",6:"June",7:"July",8:"August",9:"September",10:"October"}
        month_opts  = ["All"] + [month_names.get(m, str(m)) for m in months]
    else:
        month_opts = ["All"]
        month_names = {}
    month_filter = st.selectbox("Month", month_opts)

    if not team_id:
        st.info("Showing Reading (AA) · select a specific level for other teams")

st.title(f"📅 Game Log — {team_label} {season}")

if df.empty:
    st.warning("No game data found. Run `py main.py` or choose a different team/season.")
    st.stop()

# Apply filters
fdf = df.copy()
if result_filter == "Wins":
    fdf = fdf[fdf["win"] == 1]
elif result_filter == "Losses":
    fdf = fdf[fdf["win"] == 0]
if ha_filter != "All":
    fdf = fdf[fdf["home_away"] == ha_filter.lower()]
if opp_filter != "All":
    fdf = fdf[fdf["opponent_name"] == opp_filter]
if month_filter != "All":
    m_num = {v: k for k, v in month_names.items()}.get(month_filter)
    if m_num:
        fdf = fdf[fdf["game_date"].dt.month == m_num]

st.caption(f"Showing {len(fdf)} of {len(df)} games")

# ── KPI row ───────────────────────────────────────────────────────────────────
wins_shown   = int(fdf["win"].sum())
losses_shown = int((1 - fdf["win"]).sum())
rs = fdf["team_score"].sum()
ra = fdf["opp_score"].sum()
rd = int(rs - ra) if not (pd.isna(rs) or pd.isna(ra)) else 0
avg_rs = fdf["team_score"].mean()
avg_ra = fdf["opp_score"].mean()

c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Record",       f"{wins_shown}–{losses_shown}")
c2.metric("Win %",        f"{wins_shown/(wins_shown+losses_shown):.3f}" if (wins_shown+losses_shown) else "—")
c3.metric("Run Diff",     f"{rd:+d}")
c4.metric("Avg Runs/G",   f"{avg_rs:.1f}" if pd.notna(avg_rs) else "—")
c5.metric("Avg Allow/G",  f"{avg_ra:.1f}" if pd.notna(avg_ra) else "—")

st.divider()

# ── Score timeline ─────────────────────────────────────────────────────────────
st.subheader("Score Timeline")

if not fdf.empty:
    fig = go.Figure()
    hover_text = [
        f"{'W' if w==1 else 'L'} {int(ts)}-{int(os_)}<br>{opp}<br>{ha.capitalize()}"
        for w, ts, os_, opp, ha in zip(
            fdf["win"],
            fdf["team_score"].fillna(0),
            fdf["opp_score"].fillna(0),
            fdf["opponent_name"].fillna(""),
            fdf["home_away"],
        )
    ]
    fig.add_bar(
        x=fdf["game_date"], y=fdf["team_score"],
        name="Runs Scored", marker_color="#2ECC71", opacity=0.7,
        hovertext=hover_text, hoverinfo="text+x",
    )
    fig.add_bar(
        x=fdf["game_date"], y=-fdf["opp_score"],
        name="Runs Allowed", marker_color="#E74C3C", opacity=0.7,
        hovertext=hover_text, hoverinfo="text+x",
    )
    fig.add_hline(y=0, line_color="#555", line_width=1)
    fig.update_layout(
        barmode="overlay",
        yaxis=dict(title="Runs (positive=scored, negative=allowed)"),
        xaxis_title="Date",
        height=320, margin=dict(t=10, b=40),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Full game table ────────────────────────────────────────────────────────────
st.subheader("Full Game Log")

available = [c for c in [
    "game_date","home_away","opponent_name","result",
    "team_score","opp_score","run_differential",
    "team_hits","team_errors","opp_hits","opp_errors",
    "winning_pitcher","losing_pitcher","save_pitcher",
    "attendance","venue_name",
] if c in fdf.columns]

table = fdf[available].copy()
table["game_date"]  = table["game_date"].dt.strftime("%Y-%m-%d")
table["home_away"]  = table["home_away"].str.capitalize()
if "attendance" in table.columns:
    table["attendance"] = table["attendance"].fillna(0).astype(int)
if "run_differential" in table.columns:
    table["run_differential"] = table["run_differential"].fillna(0).astype(int)

rename = {
    "game_date":"Date","home_away":"H/A","opponent_name":"Opponent",
    "result":"W/L","team_score":"R","opp_score":"RA","run_differential":"Diff",
    "team_hits":"H","team_errors":"E","opp_hits":"OppH","opp_errors":"OppE",
    "winning_pitcher":"WP","losing_pitcher":"LP","save_pitcher":"SV",
    "attendance":"Att","venue_name":"Venue",
}
table = table.rename(columns={k:v for k,v in rename.items() if k in table.columns})

st.dataframe(
    table.reset_index(drop=True),
    use_container_width=True,
    height=440,
    column_config={
        "W/L":  st.column_config.TextColumn(),
        "Att":  st.column_config.NumberColumn(format="%d"),
        "Diff": st.column_config.NumberColumn(format="%+d"),
    },
    hide_index=True,
)

st.divider()

# ── Opponent breakdown ─────────────────────────────────────────────────────────
st.subheader("Record by Opponent")

opp_summary = (
    df.groupby("opponent_name")
    .agg(G=("win","count"), W=("win","sum"),
         RS=("team_score","sum"), RA=("opp_score","sum"))
    .reset_index()
)
opp_summary["L"]       = opp_summary["G"] - opp_summary["W"]
opp_summary["Win%"]    = (opp_summary["W"] / opp_summary["G"]).round(3)
opp_summary["RunDiff"] = (opp_summary["RS"] - opp_summary["RA"]).astype(int)
opp_summary = opp_summary.sort_values("Win%", ascending=False).reset_index(drop=True)
opp_summary = opp_summary[["opponent_name","G","W","L","Win%","RS","RA","RunDiff"]]
opp_summary = opp_summary.rename(columns={"opponent_name": "Opponent"})

col_tbl, col_bar = st.columns([1, 1])

with col_tbl:
    st.dataframe(
        opp_summary, use_container_width=True, height=360,
        column_config={
            "Win%":    st.column_config.NumberColumn(format="%.3f"),
            "RunDiff": st.column_config.NumberColumn(format="%+d"),
        },
        hide_index=True,
    )

with col_bar:
    fig2 = px.bar(
        opp_summary.sort_values("Win%"),
        x="Win%", y="Opponent", orientation="h",
        color="Win%",
        color_continuous_scale=["#E74C3C","#F39C12","#2ECC71"],
        text="Win%",
        labels={"Win%": "Win %", "Opponent": ""},
        hover_data={"W": True, "L": True, "RunDiff": True},
    )
    fig2.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig2.add_vline(x=0.5, line_dash="dash", line_color="#555", annotation_text=".500")
    fig2.update_layout(
        coloraxis_showscale=False,
        height=380, margin=dict(t=10, l=140, r=60),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Home vs Away splits ────────────────────────────────────────────────────────
st.subheader("Home / Away Splits")

ha = (
    df.groupby("home_away")
    .agg(G=("win","count"), W=("win","sum"),
         RS=("team_score","sum"), RA=("opp_score","sum"))
    .reset_index()
)
ha["L"]       = ha["G"] - ha["W"]
ha["Win%"]    = (ha["W"] / ha["G"]).round(3)
ha["RunDiff"] = (ha["RS"] - ha["RA"]).astype(int)
ha["AvgRS"]   = (ha["RS"] / ha["G"]).round(2)
ha["AvgRA"]   = (ha["RA"] / ha["G"]).round(2)
ha["home_away"] = ha["home_away"].str.capitalize()
ha = ha.rename(columns={"home_away":"Split","W":"Wins","L":"Losses"})

st.dataframe(
    ha[["Split","G","Wins","Losses","Win%","RS","RA","RunDiff","AvgRS","AvgRA"]],
    use_container_width=True, hide_index=True,
    column_config={
        "Win%":    st.column_config.NumberColumn(format="%.3f"),
        "RunDiff": st.column_config.NumberColumn(format="%+d"),
        "AvgRS":   st.column_config.NumberColumn(format="%.2f"),
        "AvgRA":   st.column_config.NumberColumn(format="%.2f"),
    },
)
