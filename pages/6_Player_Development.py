"""
Player development tracker — search any player and see their full stat arc
across every level and season they appear in the database.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

import web_data as db

st.set_page_config(page_title="Player Development · Phillies", page_icon="📈", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #C41632; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

LEVEL_COLORS = {"MLB": "#E41134", "AAA": "#FFD700", "AA": "#8B0000"}
LEVEL_ORDER  = {"MLB": 0, "AAA": 1, "AA": 2}

with st.sidebar:
    st.markdown("## Player Development")
    st.markdown("**Phillies Organization**")
    st.divider()
    st.caption("Shows stats for every season and level the player appears in the database.")

st.title("📈 Player Development Tracker")
st.caption("Select any player to see their full statistical arc across levels and seasons.")

# ── Player search ─────────────────────────────────────────────────────────────
all_players = db.all_players_with_stats()

if all_players.empty:
    st.warning("No player stats found. Run `py main.py` to populate the database.")
    st.stop()

# Sort by name; let user type to filter
player_names = all_players["player_name"].sort_values().tolist()
selected_name = st.selectbox("Search player", player_names, index=0)

player_row = all_players[all_players["player_name"] == selected_name].iloc[0]
player_id  = int(player_row["player_id"])
position   = str(player_row["position"])

is_pitcher = position in ("P", "SP", "RP", "CL")

st.divider()

# ── Load career data ──────────────────────────────────────────────────────────
career_bat = db.player_career_batting(player_id)
career_pit = db.player_career_pitching(player_id)
career_tx  = db.player_transactions(player_id)

# Determine which view to show (prefer whichever has more data)
show_bat = not career_bat.empty
show_pit = not career_pit.empty

# ── Header ────────────────────────────────────────────────────────────────────
st.subheader(f"{selected_name}  ·  {position}")

if not career_bat.empty:
    latest = career_bat.sort_values(["season","org_level"]).iloc[-1]
    cols = st.columns(6)
    cols[0].metric("Current Level", str(latest.get("org_level","—")))
    cols[1].metric("Team", str(latest.get("team_name","—")))
    cols[2].metric("OPS",  f"{latest['ops']:.3f}" if pd.notna(latest.get("ops")) else "—")
    cols[3].metric("AVG",  f"{latest['avg']:.3f}" if pd.notna(latest.get("avg")) else "—")
    cols[4].metric("HR",   int(latest["hr"]) if pd.notna(latest.get("hr")) else "—")
    cols[5].metric("RBI",  int(latest["rbi"]) if pd.notna(latest.get("rbi")) else "—")
elif not career_pit.empty:
    latest = career_pit.sort_values(["season","org_level"]).iloc[-1]
    cols = st.columns(6)
    cols[0].metric("Current Level", str(latest.get("org_level","—")))
    cols[1].metric("Team", str(latest.get("team_name","—")))
    cols[2].metric("ERA",  f"{latest['era']:.2f}" if pd.notna(latest.get("era")) else "—")
    cols[3].metric("WHIP", f"{latest['whip']:.2f}" if pd.notna(latest.get("whip")) else "—")
    cols[4].metric("K/9",  f"{latest['k9']:.2f}"  if pd.notna(latest.get("k9"))  else "—")
    cols[5].metric("IP",   f"{latest['ip']:.1f}"  if pd.notna(latest.get("ip"))  else "—")

st.divider()

# ── Batting arc ───────────────────────────────────────────────────────────────
if show_bat:
    st.subheader("Batting — Season-by-Season Arc")

    # Label each row with level for chart
    career_bat["label"] = career_bat["season"].astype(str) + " · " + career_bat["org_level"].fillna("?")
    career_bat["_lvl_order"] = career_bat["org_level"].map(LEVEL_ORDER).fillna(99)
    career_bat = career_bat.sort_values(["season","_lvl_order"])

    # OPS / AVG / OBP / SLG line chart
    fig = go.Figure()
    for metric, color, label in [
        ("ops",  "#FF6B6B", "OPS"),
        ("obp",  "#FFD700", "OBP"),
        ("slg",  "#4ECDC4", "SLG"),
        ("avg",  "#aaaaaa", "AVG"),
    ]:
        if metric in career_bat.columns:
            fig.add_scatter(
                x=career_bat["label"], y=career_bat[metric],
                mode="lines+markers+text",
                name=label,
                line=dict(width=2),
                marker=dict(size=8, color=color),
                text=career_bat[metric].apply(lambda v: f"{v:.3f}" if pd.notna(v) else ""),
                textposition="top center",
                textfont=dict(size=9),
            )
    fig.update_layout(
        height=360,
        xaxis_title="Season · Level",
        yaxis=dict(title="Rate", range=[0, max(career_bat["ops"].max() * 1.15, 0.1) if "ops" in career_bat else 1]),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        margin=dict(t=20, b=60),
    )
    # Add level-change annotations
    for _, row in career_bat.iterrows():
        level = row.get("org_level","")
        color = LEVEL_COLORS.get(level, "#888")
        fig.add_vline(
            x=row["label"], line_dash="dot",
            line_color=color, opacity=0.4,
        )
    st.plotly_chart(fig, use_container_width=True)

    # Full stat table
    st.markdown("**Full Batting Stats by Season/Level**")
    bat_display = career_bat[[
        "season","org_level","team_name","games","pa","ab","hits",
        "hr","rbi","sb","bb","so","avg","obp","slg","ops","babip","doubles","triples"
    ]].rename(columns={
        "season":"Year","org_level":"Level","team_name":"Team",
        "games":"G","pa":"PA","ab":"AB","hits":"H",
        "hr":"HR","rbi":"RBI","sb":"SB","bb":"BB","so":"K",
        "avg":"AVG","obp":"OBP","slg":"SLG","ops":"OPS","babip":"BABIP",
        "doubles":"2B","triples":"3B",
    })
    st.dataframe(
        bat_display.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "AVG":   st.column_config.NumberColumn(format="%.3f"),
            "OBP":   st.column_config.NumberColumn(format="%.3f"),
            "SLG":   st.column_config.NumberColumn(format="%.3f"),
            "OPS":   st.column_config.NumberColumn(format="%.3f"),
            "BABIP": st.column_config.NumberColumn(format="%.3f"),
        },
    )

# ── Pitching arc ──────────────────────────────────────────────────────────────
if show_pit:
    st.subheader("Pitching — Season-by-Season Arc")

    career_pit["label"]     = career_pit["season"].astype(str) + " · " + career_pit["org_level"].fillna("?")
    career_pit["_lvl_order"]= career_pit["org_level"].map(LEVEL_ORDER).fillna(99)
    career_pit = career_pit.sort_values(["season","_lvl_order"])

    fig2 = go.Figure()
    # ERA on left axis, K/9 on right
    fig2.add_scatter(
        x=career_pit["label"], y=career_pit["era"],
        mode="lines+markers+text", name="ERA",
        line=dict(color="#FF6B6B", width=2),
        marker=dict(size=8),
        text=career_pit["era"].apply(lambda v: f"{v:.2f}" if pd.notna(v) else ""),
        textposition="top center", textfont=dict(size=9),
    )
    fig2.add_scatter(
        x=career_pit["label"], y=career_pit["whip"],
        mode="lines+markers", name="WHIP",
        line=dict(color="#FFD700", width=2, dash="dash"),
        marker=dict(size=8),
    )
    fig2.add_scatter(
        x=career_pit["label"], y=career_pit["k9"],
        mode="lines+markers", name="K/9",
        yaxis="y2", line=dict(color="#4ECDC4", width=2),
        marker=dict(size=8),
    )
    fig2.update_layout(
        height=360,
        xaxis_title="Season · Level",
        yaxis=dict(title="ERA / WHIP"),
        yaxis2=dict(title="K/9", overlaying="y", side="right"),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        margin=dict(t=20, b=60),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.markdown("**Full Pitching Stats by Season/Level**")
    pit_display = career_pit[[
        "season","org_level","team_name","games","games_started","ip",
        "wins","losses","saves","era","whip","so","bb","hr","k9","bb9","opp_avg"
    ]].rename(columns={
        "season":"Year","org_level":"Level","team_name":"Team",
        "games":"G","games_started":"GS","ip":"IP",
        "wins":"W","losses":"L","saves":"SV",
        "era":"ERA","whip":"WHIP","so":"K","bb":"BB","hr":"HR",
        "k9":"K/9","bb9":"BB/9","opp_avg":"OppAVG",
    })
    st.dataframe(
        pit_display.reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
        column_config={
            "ERA":    st.column_config.NumberColumn(format="%.2f"),
            "WHIP":   st.column_config.NumberColumn(format="%.2f"),
            "K/9":    st.column_config.NumberColumn(format="%.2f"),
            "BB/9":   st.column_config.NumberColumn(format="%.2f"),
            "OppAVG": st.column_config.NumberColumn(format="%.3f"),
            "IP":     st.column_config.NumberColumn(format="%.1f"),
        },
    )

# ── Transaction timeline ──────────────────────────────────────────────────────
if not career_tx.empty:
    st.divider()
    st.subheader("Transaction History")
    career_tx["date"] = pd.to_datetime(career_tx["date"]).dt.strftime("%Y-%m-%d")
    career_tx["from_team"] = career_tx["from_team"].fillna("—")
    career_tx["to_team"]   = career_tx["to_team"].fillna("—")
    st.dataframe(
        career_tx.rename(columns={
            "date":"Date","type_desc":"Type",
            "from_team":"From","to_team":"To","description":"Description"
        }).reset_index(drop=True),
        use_container_width=True,
        hide_index=True,
    )

if not show_bat and not show_pit:
    st.info("No stats found for this player. They may only appear on the roster without recorded stats yet.")
