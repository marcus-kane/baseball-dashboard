"""
Phillies prospect board — ranked list with live stats pulled from the database.
Edit data/prospects.csv to update rankings anytime.
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import streamlit as st
import pandas as pd

import web_data as db
from config import PROSPECTS_CSV

st.set_page_config(page_title="Prospect Board · Phillies", page_icon="🌟", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #C41632; padding-left: 10px; }
.prospect-rank { font-size: 1.4rem; font-weight: bold; color: #E41134; }
</style>
""", unsafe_allow_html=True)

LEVEL_COLORS = {"MLB": "#E41134", "AAA": "#FFD700", "AA": "#8B0000"}

with st.sidebar:
    st.markdown("## Phillies Prospect Board")
    st.divider()
    seasons = db.seasons_available()
    season  = st.selectbox("Season", seasons, index=0)
    st.divider()
    st.markdown("**Update Rankings**")
    st.caption(f"Edit `data/prospects.csv` and re-run `py main.py` to refresh rankings.")
    st.caption("Player IDs are matched automatically by name.")

st.title("🌟 Phillies Prospect Board")
st.caption(f"Rankings from `data/prospects.csv` · Live stats from {season} season")

prospects_df = db.prospects()
if prospects_df.empty:
    st.warning("No prospects loaded. Add players to `data/prospects.csv` and run `py main.py`.")
    st.stop()

# Load live stats for this season
ps = db.prospect_stats(season)

# ── Upload / edit notice ───────────────────────────────────────────────────────
with st.expander("How to update prospect rankings"):
    st.markdown(f"""
**File:** `data/prospects.csv`

Columns: `rank, player_name, position, eta, notes`

- **rank** — your ranking (1 = top prospect)
- **player_name** — must match roster spelling exactly for stats to link
- **position** — e.g. RHP, SS, OF, C
- **eta** — estimated MLB arrival year
- **notes** — scouting note, injury status, etc.

After editing the CSV, run `py main.py` (or click **Refresh** in sidebar) to reload.
""")

st.divider()

# ── Prospect board tabs ────────────────────────────────────────────────────────
tab_board, tab_hitters, tab_pitchers, tab_chart = st.tabs([
    "Full Board", "Hitter Prospects", "Pitcher Prospects", "ETA Chart"
])

with tab_board:
    st.subheader(f"Top {len(prospects_df)} Phillies Prospects")

    # Merge with live stats
    if not ps.empty:
        # Pick the most recent level's stats per player
        ps_latest = ps.sort_values("rank").drop_duplicates(subset=["rank","stat_type"], keep="first")
        # Pivot to get one row per prospect
        bat_ps = ps_latest[ps_latest["stat_type"]=="Hitter"][[
            "rank","ops","avg","hr","rbi","team_name","org_level"
        ]].rename(columns={"ops":"OPS","avg":"AVG","hr":"HR","rbi":"RBI",
                           "team_name":"Current Team","org_level":"Level"})
        pit_ps = ps_latest[ps_latest["stat_type"]=="Pitcher"][[
            "rank","era","whip","k9","ip","team_name","org_level"
        ]].rename(columns={"era":"ERA","whip":"WHIP","k9":"K/9","ip":"IP",
                           "team_name":"Current Team","org_level":"Level"})

        merged = prospects_df.merge(bat_ps,  on="rank", how="left")
        merged = merged.merge(pit_ps, on="rank", how="left", suffixes=("","_p"))

        # Coalesce level/team from whichever join succeeded
        merged["Level"]        = merged["Level"].combine_first(merged.get("Level_p"))
        merged["Current Team"] = merged["Current Team"].combine_first(merged.get("Current Team_p"))
    else:
        merged = prospects_df.copy()
        merged["Level"] = None
        merged["Current Team"] = None

    for col in ["OPS","AVG","HR","RBI","ERA","WHIP","K/9","IP","Level","Current Team"]:
        if col not in merged.columns:
            merged[col] = None

    display = merged[[
        "rank","player_name","position","eta","Level","Current Team",
        "OPS","AVG","HR","RBI","ERA","WHIP","K/9","IP","notes"
    ]].rename(columns={
        "rank":"#","player_name":"Prospect","position":"Pos","eta":"ETA","notes":"Notes"
    })

    # Color code by matched/unmatched
    matched = merged["player_id"].notna().sum()
    st.caption(f"{matched} of {len(prospects_df)} prospects matched to live stats")

    st.dataframe(
        display.reset_index(drop=True),
        use_container_width=True,
        height=min(60 + len(display)*35, 600),
        hide_index=True,
        column_config={
            "#":     st.column_config.NumberColumn(format="%d"),
            "ETA":   st.column_config.NumberColumn(format="%d"),
            "OPS":   st.column_config.NumberColumn(format="%.3f"),
            "AVG":   st.column_config.NumberColumn(format="%.3f"),
            "ERA":   st.column_config.NumberColumn(format="%.2f"),
            "WHIP":  st.column_config.NumberColumn(format="%.2f"),
            "K/9":   st.column_config.NumberColumn(format="%.2f"),
            "IP":    st.column_config.NumberColumn(format="%.1f"),
        },
    )

with tab_hitters:
    hitter_prospects = prospects_df[
        ~prospects_df["position"].str.contains("HP|SP|RP|P", na=False)
    ]
    if not ps.empty:
        h_stats = ps[ps["stat_type"]=="Hitter"].copy()
        h_merged = hitter_prospects.merge(h_stats[["rank","ops","avg","obp","slg","hr","rbi","sb","pa","team_name","org_level"]], on="rank", how="left")
    else:
        h_merged = hitter_prospects.copy()

    if not h_merged.empty:
        cols_show = [c for c in ["rank","player_name","position","eta","org_level","team_name","pa","avg","obp","slg","ops","hr","rbi","sb","notes"] if c in h_merged.columns]
        st.dataframe(
            h_merged[cols_show].rename(columns={
                "rank":"#","player_name":"Prospect","position":"Pos","eta":"ETA",
                "org_level":"Level","team_name":"Team",
                "pa":"PA","avg":"AVG","obp":"OBP","slg":"SLG","ops":"OPS",
                "hr":"HR","rbi":"RBI","sb":"SB","notes":"Notes"
            }).reset_index(drop=True),
            use_container_width=True, hide_index=True,
            column_config={
                "AVG": st.column_config.NumberColumn(format="%.3f"),
                "OBP": st.column_config.NumberColumn(format="%.3f"),
                "SLG": st.column_config.NumberColumn(format="%.3f"),
                "OPS": st.column_config.NumberColumn(format="%.3f"),
            },
        )

with tab_pitchers:
    pitcher_prospects = prospects_df[
        prospects_df["position"].str.contains("HP|SP|RP|P", na=False)
    ]
    if not ps.empty:
        p_stats = ps[ps["stat_type"]=="Pitcher"].copy()
        p_merged = pitcher_prospects.merge(p_stats[["rank","ip","era","whip","k9","bb9","fip","team_name","org_level"]], on="rank", how="left")
    else:
        p_merged = pitcher_prospects.copy()

    if not p_merged.empty:
        cols_show = [c for c in ["rank","player_name","position","eta","org_level","team_name","ip","era","whip","k9","bb9","fip","notes"] if c in p_merged.columns]
        st.dataframe(
            p_merged[cols_show].rename(columns={
                "rank":"#","player_name":"Prospect","position":"Pos","eta":"ETA",
                "org_level":"Level","team_name":"Team",
                "ip":"IP","era":"ERA","whip":"WHIP","k9":"K/9","bb9":"BB/9","fip":"FIP","notes":"Notes"
            }).reset_index(drop=True),
            use_container_width=True, hide_index=True,
            column_config={
                "ERA":  st.column_config.NumberColumn(format="%.2f"),
                "WHIP": st.column_config.NumberColumn(format="%.2f"),
                "K/9":  st.column_config.NumberColumn(format="%.2f"),
                "BB/9": st.column_config.NumberColumn(format="%.2f"),
                "FIP":  st.column_config.NumberColumn(format="%.2f"),
                "IP":   st.column_config.NumberColumn(format="%.1f"),
            },
        )

with tab_chart:
    st.subheader("Prospect Pipeline — ETA by Level")
    eta_df = prospects_df.copy()
    if not ps.empty:
        level_map = ps.drop_duplicates("rank")[["rank","org_level"]].copy()
        eta_df = eta_df.merge(level_map, on="rank", how="left")
    else:
        eta_df["org_level"] = None

    eta_df["org_level"] = eta_df["org_level"].fillna("Pre-org / Unknown")
    eta_df["eta"]       = pd.to_numeric(eta_df["eta"], errors="coerce")

    if eta_df["eta"].notna().any():
        fig = px.strip(
            eta_df.dropna(subset=["eta"]),
            x="eta", y="org_level",
            color="org_level",
            color_discrete_map={**LEVEL_COLORS, "Pre-org / Unknown": "#555"},
            hover_name="player_name",
            hover_data={"position": True, "notes": True, "eta": True},
            labels={"eta": "Estimated MLB Arrival", "org_level": "Current Level"},
        )
        fig.update_traces(jitter=0.4, marker_size=10)
        fig.update_layout(
            height=350,
            plot_bgcolor="#0e1117", paper_bgcolor="#0e1117", font_color="#ccc",
            showlegend=False,
            xaxis=dict(tickformat="d"),
        )
        st.plotly_chart(fig, use_container_width=True)

        # Pipeline countdown
        from datetime import date
        current_year = date.today().year
        arriving_soon = eta_df[eta_df["eta"].fillna(9999) <= current_year + 1].sort_values("eta")
        if not arriving_soon.empty:
            st.markdown("**Arriving soon (this year or next):**")
            for _, row in arriving_soon.iterrows():
                eta_str = f"ETA {int(row['eta'])}" if pd.notna(row["eta"]) else "Now"
                level   = row.get("org_level","?")
                color   = LEVEL_COLORS.get(level, "#888")
                st.markdown(
                    f"- **#{int(row['rank'])} {row['player_name']}** ({row['position']}) — "
                    f"<span style='color:{color}'>{level}</span> — {eta_str}  "
                    f"_{row.get('notes','')}_",
                    unsafe_allow_html=True,
                )
