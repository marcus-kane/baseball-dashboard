"""
Philadelphia Phillies Org Analytics — Home / Team Overview
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

import web_data as db
import sidebar as sb

st.set_page_config(
    page_title="Phillies Org Analytics",
    page_icon="⚾",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.markdown("""
<style>
    [data-testid="stSidebar"] { background-color: #1a0a0a; }
    [data-testid="stSidebar"] * { color: #f0e0d0 !important; }
    [data-testid="stMetric"] {
        background: #1e1e2e; border: 1px solid #8B0000;
        border-radius: 8px; padding: 12px 16px;
    }
    [data-testid="stMetricValue"] { color: #FF6B6B !important; font-size: 1.8rem !important; }
    [data-testid="stMetricLabel"] { color: #aaa !important; }
    h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

season, team_id = sb.render("Home")

# Default to Reading if no team selected (home page = AA focus for 2025 data)
display_team_id = team_id or 522

games_df    = db.games(season=season)
batting_df  = db.batting(season=season, team_id=display_team_id if team_id else None)
pitching_df = db.pitching(season=season, team_id=display_team_id if team_id else None)

# Determine display name
from config import TEAM_BY_ID
team_info = TEAM_BY_ID.get(display_team_id, {"team_name": "Phillies Org", "level": ""})
display_name = team_info["team_name"] if team_id else "Phillies Organization"

if games_df.empty:
    st.title(f"⚾ {display_name} — {season}")
    st.info("No game data found for this season. Run `py main.py` or click Refresh in the sidebar.")
    st.stop()

wins   = int(games_df["win"].sum())
losses = int((1 - games_df["win"]).sum())
gp     = wins + losses
win_pct = wins / gp if gp else 0
rs = games_df["team_score"].sum()
ra = games_df["opp_score"].sum()
run_diff = int(rs - ra) if not (pd.isna(rs) or pd.isna(ra)) else 0
exp  = 1.83
pyth = (rs ** exp) / (rs ** exp + ra ** exp) if (rs and ra) else None

ip_total  = pitching_df["ip"].fillna(0).sum()
er_total  = pitching_df["earned_runs"].fillna(0).sum()
team_era  = round(er_total * 9 / ip_total, 2) if ip_total else None
team_whip = round((pitching_df["hits"].fillna(0).sum() + pitching_df["bb"].fillna(0).sum()) / ip_total, 2) if ip_total else None

qual_bat  = batting_df[batting_df["pa"].fillna(0) >= 50]
team_ops  = round(qual_bat["ops"].mean(), 3) if not qual_bat.empty else None

st.title(f"⚾ {display_name} — {season}")
st.caption("Philadelphia Phillies organization · Data: MLB Stats API")
st.divider()

c1,c2,c3,c4,c5,c6,c7 = st.columns(7)
c1.metric("Record",      f"{wins}–{losses}")
c2.metric("Win %",       f"{win_pct:.3f}", delta=f"Pyth {pyth:.3f}" if pyth else None)
c3.metric("Run Diff",    f"{run_diff:+d}")
c4.metric("Runs Scored", f"{int(rs)}")
c5.metric("Team OPS",    f"{team_ops}" if team_ops else "—")
c6.metric("Team ERA",    f"{team_era}" if team_era else "—")
c7.metric("Team WHIP",   f"{team_whip}" if team_whip else "—")
st.divider()

col_a, col_b = st.columns(2)

with col_a:
    st.subheader("Game-by-Game Results")
    colors = ["#2ECC71" if w==1 else "#E74C3C" for w in games_df["win"]]
    fig = go.Figure()
    fig.add_bar(
        x=games_df["game_num"], y=games_df["run_differential"],
        marker_color=colors, name="Run Diff",
        hovertemplate="Game %{x}<br>%{customdata[0]} vs %{customdata[1]}<br>%{customdata[2]}–%{customdata[3]}<extra></extra>",
        customdata=list(zip(
            games_df["result"], games_df["opponent_name"].fillna(""),
            games_df["team_score"].fillna(0).astype(int),
            games_df["opp_score"].fillna(0).astype(int),
        )),
    )
    fig.add_scatter(
        x=games_df["game_num"], y=games_df["roll_win_10"],
        mode="lines", name="10-game win%", yaxis="y2",
        line=dict(color="#FFD700", width=2),
    )
    fig.update_layout(
        yaxis=dict(title="Run Diff", zeroline=True, zerolinecolor="#555"),
        yaxis2=dict(title="10g Win%", overlaying="y", side="right",
                    tickformat=".0%", range=[0,1]),
        height=330, margin=dict(t=10,b=40), hovermode="x unified",
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig, use_container_width=True)

with col_b:
    st.subheader("Cumulative Run Differential")
    pos = games_df["cum_run_diff"].clip(lower=0)
    neg = games_df["cum_run_diff"].clip(upper=0)
    fig2 = go.Figure()
    fig2.add_scatter(x=games_df["game_num"], y=pos, fill="tozeroy",
                     fillcolor="rgba(46,204,113,0.25)", line=dict(color="#2ECC71",width=1.5), name="+")
    fig2.add_scatter(x=games_df["game_num"], y=neg, fill="tozeroy",
                     fillcolor="rgba(231,76,60,0.25)", line=dict(color="#E74C3C",width=1.5), name="-")
    fig2.add_scatter(x=games_df["game_num"], y=games_df["cum_run_diff"],
                     line=dict(color="#8B0000",width=2.5), name="Cumulative")
    fig2.add_hline(y=0, line_dash="dash", line_color="#555")
    fig2.update_layout(
        height=330, margin=dict(t=10,b=40), hovermode="x unified",
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
        yaxis_title="Cumulative Run Diff", xaxis_title="Game #",
        legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig2, use_container_width=True)

col_c, col_d = st.columns(2)

with col_c:
    st.subheader("Rolling Win %")
    fig3 = go.Figure()
    fig3.add_scatter(x=games_df["game_num"], y=games_df["roll_win_5"],  name="5-game",  line=dict(color="#E74C3C",width=1.5))
    fig3.add_scatter(x=games_df["game_num"], y=games_df["roll_win_10"], name="10-game", line=dict(color="#FFD700",width=2))
    fig3.add_scatter(x=games_df["game_num"], y=games_df["cum_win_pct"], name="Season",  line=dict(color="#8B0000",width=2,dash="dot"))
    fig3.add_hline(y=0.5, line_dash="dash", line_color="#555", annotation_text=".500")
    fig3.update_layout(
        yaxis=dict(title="Win %", tickformat=".0%", range=[0,1]),
        xaxis_title="Game #", height=310, margin=dict(t=10,b=40),
        hovermode="x unified", plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", legend=dict(orientation="h", y=1.1),
    )
    st.plotly_chart(fig3, use_container_width=True)

with col_d:
    st.subheader("Monthly Record")
    games_df["month"]      = games_df["game_date"].dt.month
    games_df["month_name"] = games_df["game_date"].dt.strftime("%b")
    monthly = (games_df.groupby(["month","month_name"])
               .agg(wins=("win","sum"), games=("win","count"))
               .reset_index().sort_values("month"))
    monthly["losses"] = monthly["games"] - monthly["wins"]
    fig4 = go.Figure()
    fig4.add_bar(x=monthly["month_name"], y=monthly["wins"],   name="Wins",   marker_color="#2ECC71", opacity=0.85)
    fig4.add_bar(x=monthly["month_name"], y=monthly["losses"], name="Losses", marker_color="#E74C3C", opacity=0.85)
    fig4.update_layout(barmode="group", yaxis_title="Games", height=310,
                       margin=dict(t=10,b=40), plot_bgcolor="#0e1117",
                       paper_bgcolor="#0e1117", font_color="#ccc",
                       legend=dict(orientation="h",y=1.1))
    st.plotly_chart(fig4, use_container_width=True)

st.divider()
st.subheader("Quick Leaders")
ql1, ql2, ql3 = st.columns(3)

with ql1:
    st.markdown(f"**Top 5 OPS** *(min 50 PA)*")
    top = qual_bat.nlargest(5,"ops")[["player_name","pa","avg","ops","hr"]].rename(
        columns={"player_name":"Player","pa":"PA","avg":"AVG","ops":"OPS","hr":"HR"})
    top.index = range(1, len(top)+1)
    st.dataframe(top, use_container_width=True,
                 column_config={"AVG":st.column_config.NumberColumn(format="%.3f"),
                                "OPS":st.column_config.NumberColumn(format="%.3f")})

with ql2:
    st.markdown("**Top 5 ERA** *(min 20 IP)*")
    qual_p = pitching_df[pitching_df["ip"].fillna(0)>=20]
    top_p  = qual_p.nsmallest(5,"era")[["player_name","ip","era","whip","k9"]].rename(
        columns={"player_name":"Player","ip":"IP","era":"ERA","whip":"WHIP","k9":"K/9"})
    top_p["IP"] = top_p["IP"].round(1)
    top_p.index = range(1, len(top_p)+1)
    st.dataframe(top_p, use_container_width=True,
                 column_config={"ERA":st.column_config.NumberColumn(format="%.2f"),
                                "WHIP":st.column_config.NumberColumn(format="%.2f"),
                                "K/9":st.column_config.NumberColumn(format="%.2f")})

with ql3:
    st.markdown("**HR Leaders**")
    top_hr = batting_df.nlargest(5,"hr")[["player_name","hr","rbi","ops"]].rename(
        columns={"player_name":"Player","hr":"HR","rbi":"RBI","ops":"OPS"})
    top_hr.index = range(1, len(top_hr)+1)
    st.dataframe(top_hr, use_container_width=True,
                 column_config={"OPS":st.column_config.NumberColumn(format="%.3f")})
