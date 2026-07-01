"""Standings page — division table + visual GB chart."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import pandas as pd

import web_data as db
import sidebar as sb
from config import TEAM_BY_ID, ORG_TEAMS

st.set_page_config(page_title="Standings · Phillies Org", page_icon="🏆", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

season, team_id = sb.render("Standings")

# Standings are per-league; pick the league from the selected team or show all
if team_id:
    team_info   = TEAM_BY_ID[team_id]
    league_id   = team_info["league_id"]
    team_name   = team_info["team_name"]
    level_label = f"{team_info['level']} — {team_name}"
else:
    league_id   = None
    level_label = "All Levels"

st.title(f"🏆 Standings — {level_label} · {season}")

# Build standings: if a league is selected fetch just that; otherwise show all org leagues
if league_id:
    df = db.standings(season=season, league_id=league_id)
    _tabs = [(level_label, df, team_id)]
else:
    all_tabs = []
    for t in ORG_TEAMS:
        s = db.standings(season=season, league_id=t["league_id"])
        all_tabs.append((f"{t['level']} — {t['team_name']}", s, t["team_id"]))
    _tabs = all_tabs

def _render_standings(df: pd.DataFrame, highlight_team_id: int | None):
    if df.empty:
        st.info("No standings data for this league/season.")
        return

    df = df.sort_values("league_rank").reset_index(drop=True)
    df["Record"] = df["wins"].astype(str) + "–" + df["losses"].astype(str)
    df["Win%"]   = df["pct"].round(3)

    display = df[[
        "league_rank","team_name","Record","Win%",
        "games_back","wc_games_back","streak",
        "home_wins","home_losses","away_wins","away_losses",
        "last_10_wins","last_10_losses",
    ]].copy()

    display["Home"]    = display["home_wins"].astype(str)    + "–" + display["home_losses"].astype(str)
    display["Away"]    = display["away_wins"].astype(str)    + "–" + display["away_losses"].astype(str)
    display["Last 10"] = display["last_10_wins"].astype(str) + "–" + display["last_10_losses"].astype(str)

    display = display[[
        "league_rank","team_name","Record","Win%",
        "games_back","wc_games_back","Home","Away","Last 10","streak"
    ]].rename(columns={
        "league_rank":"Rank","team_name":"Team",
        "games_back":"GB","wc_games_back":"WC GB","streak":"Streak",
    })

    st.subheader("League Standings")
    st.dataframe(
        display.reset_index(drop=True),
        use_container_width=True, hide_index=True,
        column_config={
            "Win%": st.column_config.NumberColumn(format="%.3f"),
            "Rank": st.column_config.NumberColumn(format="%d"),
        },
        height=min(60 + len(display) * 35, 500),
    )

    # Highlight label for our team
    if highlight_team_id:
        hl_name = TEAM_BY_ID[highlight_team_id]["team_name"].split()[0]  # first word
    else:
        hl_name = None

    st.divider()
    st.subheader("Games Behind Leader")

    gb_df = df[df["games_back"] != "-"].copy()
    gb_df["GB_num"] = pd.to_numeric(gb_df["games_back"], errors="coerce").fillna(0)
    gb_df["is_ours"] = gb_df["team_name"].str.contains(hl_name, na=False) if hl_name else False

    if not gb_df.empty:
        fig = px.bar(
            gb_df.sort_values("GB_num", ascending=False),
            x="GB_num", y="team_name", orientation="h",
            color="is_ours",
            color_discrete_map={True: "#8B0000", False: "#3a3a5a"},
            labels={"GB_num": "Games Behind", "team_name": ""},
            text="GB_num",
            hover_data={"Record": True, "Win%": ":.3f"},
        )
        fig.update_traces(texttemplate="%{text:.1f}", textposition="outside")
        fig.update_layout(
            showlegend=False,
            height=max(300, len(gb_df) * 45),
            margin=dict(t=10, l=160, r=60),
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
            font_color="#ccc", yaxis_title="",
        )
        st.plotly_chart(fig, use_container_width=True)

    st.subheader("Win % by Team")
    fig2 = px.bar(
        df.sort_values("Win%"),
        x="Win%", y="team_name", orientation="h",
        color=df.sort_values("Win%")["team_name"].str.contains(hl_name, na=False) if hl_name else "Win%",
        color_discrete_map={True:"#8B0000", False:"#3a3a5a"} if hl_name else None,
        labels={"Win%": "Win %", "team_name": ""},
        text="Win%",
    )
    fig2.update_traces(texttemplate="%{text:.3f}", textposition="outside")
    fig2.add_vline(x=0.5, line_dash="dash", line_color="#555", annotation_text=".500")
    fig2.update_layout(
        showlegend=False,
        height=max(300, len(df) * 45),
        margin=dict(t=10, l=160, r=80),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
        xaxis=dict(tickformat=".0%", range=[0, max(df["Win%"].max() + 0.05, 0.7)]),
    )
    st.plotly_chart(fig2, use_container_width=True)

    st.subheader("Home vs Away Record — All Teams")
    ha_df = df[["team_name","home_wins","home_losses","away_wins","away_losses"]].copy()
    ha_df["home_wp"] = (ha_df["home_wins"] / (ha_df["home_wins"] + ha_df["home_losses"])).round(3)
    ha_df["away_wp"] = (ha_df["away_wins"] / (ha_df["away_wins"] + ha_df["away_losses"])).round(3)
    ha_df = ha_df.sort_values("home_wp", ascending=False).reset_index(drop=True)

    fig3 = go.Figure()
    fig3.add_bar(
        x=ha_df["team_name"], y=ha_df["home_wp"],
        name="Home Win%", marker_color="#8B0000", opacity=0.85,
        hovertemplate="%{x}<br>Home: %{y:.3f}<extra></extra>",
    )
    fig3.add_bar(
        x=ha_df["team_name"], y=ha_df["away_wp"],
        name="Away Win%", marker_color="#1a4a8B", opacity=0.85,
        hovertemplate="%{x}<br>Away: %{y:.3f}<extra></extra>",
    )
    fig3.add_hline(y=0.5, line_dash="dash", line_color="#555")
    fig3.update_layout(
        barmode="group",
        yaxis=dict(title="Win %", tickformat=".0%"),
        height=360, margin=dict(t=10, b=80),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig3, use_container_width=True)


if len(_tabs) == 1:
    _render_standings(_tabs[0][1], _tabs[0][2])
else:
    tab_labels = [t[0] for t in _tabs]
    tabs = st.tabs(tab_labels)
    for tab_obj, (label, df_tab, tid) in zip(tabs, _tabs):
        with tab_obj:
            _render_standings(df_tab, tid)
