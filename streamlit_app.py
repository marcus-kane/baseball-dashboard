"""
Reading Fightin Phils — Baseball Analytics Dashboard
Main entry point (Home / Team Overview page)
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import web_data as db

# ── Page config ───────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Reading Fightin Phils Analytics",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Global CSS ────────────────────────────────────────────────────────────────
st.markdown("""
<style>
    /* Sidebar team branding */
    [data-testid="stSidebar"] { background-color: #1a0a0a; }
    [data-testid="stSidebar"] * { color: #f0e0d0 !important; }

    /* Metric cards */
    [data-testid="stMetric"] {
        background: #1e1e2e;
        border: 1px solid #8B0000;
        border-radius: 8px;
        padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { color: #FF6B6B !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #aaa !important; }
    [data-testid="stMetricDelta"] { font-size: 0.85rem !important; }

    /* Section headers */
    h2 { border-left: 4px solid #8B0000; padding-left: 10px; }

    /* Dataframe */
    [data-testid="stDataFrame"] { border: 1px solid #333; border-radius: 6px; }
</style>
""", unsafe_allow_html=True)

# ── Sidebar ───────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## ⚾ Reading Fightin Phils")
    st.markdown("**Double-A Northeast · 2025**")
    st.markdown("*Phillies Affiliate*")
    st.divider()
    st.markdown("**Navigation**")
    st.markdown("""
    - 🏠 **Home** ← you are here
    - ⚡ Batting
    - 🎯 Pitching
    - 📅 Game Log
    - 🏆 Standings
    - 🔄 Transactions
    """)
    st.divider()
    st.caption("Data: MLB Stats API · Updated on pipeline run")

# ── Load data ─────────────────────────────────────────────────────────────────
games_df    = db.games()
batting_df  = db.batting()
pitching_df = db.pitching()

wins   = int(games_df["win"].sum())
losses = int((1 - games_df["win"]).sum())
gp     = wins + losses
win_pct = wins / gp if gp else 0

rs = games_df["team_score"].sum()
ra = games_df["opp_score"].sum()
run_diff = int(rs - ra)

exp = 1.83
pyth = (rs ** exp) / (rs ** exp + ra ** exp) if (rs and ra) else None

# Team pitching ERA
ip_total = pitching_df["ip"].fillna(0).sum()
er_total = pitching_df["earned_runs"].fillna(0).sum()
team_era = round(er_total * 9 / ip_total, 2) if ip_total else None
hits_p   = pitching_df["hits"].fillna(0).sum()
bb_p     = pitching_df["bb"].fillna(0).sum()
team_whip = round((hits_p + bb_p) / ip_total, 2) if ip_total else None

qual_bat = batting_df[batting_df["pa"].fillna(0) >= 50]
team_ops = round(qual_bat["ops"].mean(), 3) if not qual_bat.empty else None
team_avg = round(qual_bat["avg"].mean(), 3) if not qual_bat.empty else None

# ── Header ────────────────────────────────────────────────────────────────────
st.title("Reading Fightin Phils — 2025 Season")
st.caption("Double-A Northeast  ·  Philadelphia Phillies affiliate  ·  FirstEnergy Stadium")
st.divider()

# ── KPI row ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5, c6, c7 = st.columns(7)
c1.metric("Record",     f"{wins}–{losses}")
c2.metric("Win %",      f"{win_pct:.3f}",    delta=f"Pyth: {pyth:.3f}" if pyth else None)
c3.metric("Run Diff",   f"{run_diff:+d}")
c4.metric("Runs Scored",f"{int(rs)}")
c5.metric("Team OPS",   f"{team_ops}" if team_ops else "—")
c6.metric("Team ERA",   f"{team_era}" if team_era else "—")
c7.metric("Team WHIP",  f"{team_whip}" if team_whip else "—")

st.divider()

# ── Charts row 1: Win/Loss timeline + Cumulative run diff ─────────────────────
col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Game-by-Game Results")
    fig = go.Figure()
    colors = ["#2ECC71" if w == 1 else "#E74C3C" for w in games_df["win"]]
    fig.add_bar(
        x=games_df["game_num"],
        y=games_df["run_differential"],
        marker_color=colors,
        name="Run Diff",
        hovertemplate=(
            "Game %{x}<br>"
            "%{customdata[0]} vs %{customdata[1]}<br>"
            "Score: %{customdata[2]}–%{customdata[3]}<br>"
            "Run diff: %{y}<extra></extra>"
        ),
        customdata=list(zip(
            games_df["result"],
            games_df["opponent_name"].fillna(""),
            games_df["team_score"].fillna(0).astype(int),
            games_df["opp_score"].fillna(0).astype(int),
        )),
    )
    fig.add_scatter(
        x=games_df["game_num"], y=games_df["roll_win_10"],
        mode="lines", name="10-game win%",
        yaxis="y2", line=dict(color="#FFD700", width=2),
        hovertemplate="10-game win%: %{y:.1%}<extra></extra>",
    )
    fig.update_layout(
        yaxis=dict(title="Run Differential", zeroline=True, zerolinecolor="#555"),
        yaxis2=dict(title="10-game Win%", overlaying="y", side="right",
                    tickformat=".0%", range=[0, 1]),
        legend=dict(orientation="h", y=1.1),
        hovermode="x unified",
        height=350,
        margin=dict(t=10, b=40),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#ccc",
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Cumulative Run Differential")
    fig2 = go.Figure()
    pos = games_df["cum_run_diff"].clip(lower=0)
    neg = games_df["cum_run_diff"].clip(upper=0)
    fig2.add_scatter(x=games_df["game_num"], y=pos, fill="tozeroy",
                     fillcolor="rgba(46,204,113,0.25)", line=dict(color="#2ECC71", width=1.5),
                     name="Positive", hovertemplate="Game %{x}<br>+%{y}<extra></extra>")
    fig2.add_scatter(x=games_df["game_num"], y=neg, fill="tozeroy",
                     fillcolor="rgba(231,76,60,0.25)", line=dict(color="#E74C3C", width=1.5),
                     name="Negative", hovertemplate="Game %{x}<br>%{y}<extra></extra>")
    fig2.add_scatter(x=games_df["game_num"], y=games_df["cum_run_diff"],
                     line=dict(color="#8B0000", width=2.5), name="Cumulative",
                     hovertemplate="Game %{x}<br>Cumulative: %{y}<extra></extra>")
    fig2.add_hline(y=0, line_dash="dash", line_color="#555")
    fig2.update_layout(
        yaxis_title="Cumulative Run Diff",
        xaxis_title="Game #",
        height=350,
        margin=dict(t=10, b=40),
        hovermode="x unified",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Charts row 2: Rolling win% + Monthly record ───────────────────────────────
col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Rolling Win %")
    fig3 = go.Figure()
    fig3.add_scatter(x=games_df["game_num"], y=games_df["roll_win_5"],
                     name="5-game", line=dict(color="#E74C3C", width=1.5),
                     hovertemplate="5-game: %{y:.1%}<extra></extra>")
    fig3.add_scatter(x=games_df["game_num"], y=games_df["roll_win_10"],
                     name="10-game", line=dict(color="#FFD700", width=2),
                     hovertemplate="10-game: %{y:.1%}<extra></extra>")
    fig3.add_scatter(x=games_df["game_num"], y=games_df["cum_win_pct"],
                     name="Season", line=dict(color="#8B0000", width=2, dash="dot"),
                     hovertemplate="Season: %{y:.1%}<extra></extra>")
    fig3.add_hline(y=0.5, line_dash="dash", line_color="#555",
                   annotation_text=".500", annotation_position="right")
    fig3.update_layout(
        yaxis=dict(title="Win %", tickformat=".0%", range=[0, 1]),
        xaxis_title="Game #",
        height=330,
        margin=dict(t=10, b=40),
        hovermode="x unified",
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Monthly Record")
    games_df["month"]      = games_df["game_date"].dt.month
    games_df["month_name"] = games_df["game_date"].dt.strftime("%b")
    monthly = (games_df.groupby(["month", "month_name"])
               .agg(wins=("win", "sum"), games=("win", "count"))
               .reset_index()
               .sort_values("month"))
    monthly["losses"]  = monthly["games"] - monthly["wins"]
    monthly["win_pct"] = (monthly["wins"] / monthly["games"]).round(3)

    fig4 = go.Figure()
    fig4.add_bar(x=monthly["month_name"], y=monthly["wins"],   name="Wins",
                 marker_color="#2ECC71", opacity=0.85,
                 hovertemplate="%{x}: %{y} W<extra></extra>")
    fig4.add_bar(x=monthly["month_name"], y=monthly["losses"], name="Losses",
                 marker_color="#E74C3C", opacity=0.85,
                 hovertemplate="%{x}: %{y} L<extra></extra>")
    fig4.update_layout(
        barmode="group",
        yaxis_title="Games",
        height=330,
        margin=dict(t=10, b=40),
        plot_bgcolor="#0e1117",
        paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Quick leaderboards ────────────────────────────────────────────────────────
st.divider()
st.subheader("Quick Leaders")

ql1, ql2, ql3 = st.columns(3)

with ql1:
    st.markdown("**Top 5 OPS** *(min 50 PA)*")
    top_bat = (qual_bat.nlargest(5, "ops")
               [["player_name", "pa", "avg", "obp", "slg", "ops"]]
               .rename(columns={"player_name": "Player", "pa": "PA",
                                "avg": "AVG", "obp": "OBP", "slg": "SLG", "ops": "OPS"})
               .reset_index(drop=True))
    top_bat.index += 1
    st.dataframe(top_bat, use_container_width=True)

with ql2:
    st.markdown("**Top 5 ERA** *(min 20 IP)*")
    qual_pit = pitching_df[pitching_df["ip"].fillna(0) >= 20]
    top_pit = (qual_pit.nsmallest(5, "era")
               [["player_name", "ip", "era", "whip", "k9", "fip"]]
               .rename(columns={"player_name": "Player", "ip": "IP",
                                "era": "ERA", "whip": "WHIP", "k9": "K/9", "fip": "FIP"})
               .reset_index(drop=True))
    top_pit["IP"] = top_pit["IP"].round(1)
    top_pit.index += 1
    st.dataframe(top_pit, use_container_width=True)

with ql3:
    st.markdown("**HR Leaders**")
    top_hr = (batting_df.nlargest(5, "hr")
              [["player_name", "hr", "rbi", "ops"]]
              .rename(columns={"player_name": "Player", "hr": "HR",
                               "rbi": "RBI", "ops": "OPS"})
              .reset_index(drop=True))
    top_hr.index += 1
    st.dataframe(top_hr, use_container_width=True)

# ── Season narrative ──────────────────────────────────────────────────────────
st.divider()
st.subheader("Season Summary")

best_bat_row = qual_bat.nlargest(1, "ops").iloc[0] if not qual_bat.empty else None
best_pit_row = qual_pit.nsmallest(1, "era").iloc[0] if not qual_pit.empty else None

home_g = games_df[games_df["home_away"] == "home"]
away_g = games_df[games_df["home_away"] == "away"]
home_wp = home_g["win"].mean() if not home_g.empty else 0
away_wp = away_g["win"].mean() if not away_g.empty else 0

col_narr, col_flags = st.columns([2, 1])

with col_narr:
    narrative = f"""
The **{wins}–{losses}** record put Reading on a rebuilding pace in 2025.
{'Their run differential of **' + str(run_diff) + '** was outpaced by their Pythagorean expectation (' + f'{pyth:.1%}' + '), meaning they lost more close games than expected.' if pyth and win_pct < pyth - 0.01 else ''}

**{best_bat_row["player_name"]}** was the offensive standout, slashing
**.{str(round(best_bat_row["avg"], 3))[2:]} / .{str(round(best_bat_row["obp"], 3))[2:]} / .{str(round(best_bat_row["slg"], 3))[2:]}**
with a **.{str(round(best_bat_row["ops"], 3))[2:]}** OPS.

On the mound, **{best_pit_row["player_name"]}** led qualified pitchers with a **{best_pit_row["era"]:.2f} ERA**.

The team was notably {'stronger at home' if home_wp > away_wp else 'stronger on the road'} —
**{home_g["win"].sum():.0f}–{(1-home_g["win"]).sum():.0f}** at home vs
**{away_g["win"].sum():.0f}–{(1-away_g["win"]).sum():.0f}** on the road.
"""
    st.markdown(narrative)

with col_flags:
    st.markdown("**Key Stats at a Glance**")
    total_hr = int(batting_df["hr"].fillna(0).sum())
    total_sb = int(batting_df["sb"].fillna(0).sum())
    total_k_bat = int(batting_df["so"].fillna(0).sum())
    total_k_pit = int(pitching_df["so"].fillna(0).sum())
    st.markdown(f"""
| Stat | Value |
|------|-------|
| Team HR | {total_hr} |
| Team SB | {total_sb} |
| Batter K | {total_k_bat} |
| Pitcher K | {total_k_pit} |
| Home W% | {home_wp:.1%} |
| Away W% | {away_wp:.1%} |
""")
