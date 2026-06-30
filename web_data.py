"""
Cached data-access layer for the Streamlit app.
All pages import from here — one place to change if the schema changes.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "database" / "baseball.db"


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


@st.cache_data(ttl=300)
def team_summary() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM teams", _conn())


@st.cache_data(ttl=300)
def batting() -> pd.DataFrame:
    sql = """
        SELECT
            r.player_name, r.position, r.bats,
            b.games, b.pa, b.ab, b.runs, b.hits,
            b.doubles, b.triples, b.hr, b.rbi,
            b.bb, b.so, b.hbp, b.sb, b.cs, b.gdp,
            b.avg, b.obp, b.slg, b.ops, b.babip,
            b.sf, b.sh,
            b.player_id, b.team_id, b.season
        FROM batting_stats b
        JOIN roster r ON b.player_id = r.player_id
        ORDER BY b.ops DESC NULLS LAST
    """
    df = pd.read_sql(sql, _conn())
    df["xbh"]     = df["doubles"].fillna(0) + df["triples"].fillna(0) + df["hr"].fillna(0)
    df["bb_pct"]  = (df["bb"]  / df["pa"].replace(0, float("nan"))).round(3)
    df["k_pct"]   = (df["so"]  / df["pa"].replace(0, float("nan"))).round(3)
    df["iso"]     = (df["slg"] - df["avg"]).round(3)
    return df


@st.cache_data(ttl=300)
def pitching() -> pd.DataFrame:
    sql = """
        SELECT
            r.player_name, r.throws_hand,
            p.games, p.games_started, p.wins, p.losses,
            p.saves, p.save_opps, p.holds, p.blown_saves,
            p.ip, p.era, p.whip,
            p.hits, p.runs, p.earned_runs, p.hr,
            p.bb, p.so, p.hbp,
            p.k9, p.bb9, p.h9, p.hr9, p.k_bb,
            p.opp_avg, p.batters_faced, p.wild_pitches,
            p.player_id, p.team_id, p.season
        FROM pitching_stats p
        JOIN roster r ON p.player_id = r.player_id
        ORDER BY p.era ASC NULLS LAST
    """
    df = pd.read_sql(sql, _conn())
    import numpy as np
    FIP_CONST = 3.10
    ip_safe = df["ip"].replace(0, float("nan"))
    df["fip"] = (
        (13 * df["hr"].fillna(0)
         + 3 * (df["bb"].fillna(0) + df["hbp"].fillna(0))
         - 2 * df["so"].fillna(0)) / ip_safe + FIP_CONST
    ).round(2)
    df["role"] = df["games_started"].apply(lambda x: "Starter" if x >= 3 else "Reliever")
    df["k_pct"]  = (df["so"] / df["batters_faced"].replace(0, float("nan"))).round(3)
    df["bb_pct"] = (df["bb"] / df["batters_faced"].replace(0, float("nan"))).round(3)
    return df


@st.cache_data(ttl=300)
def games() -> pd.DataFrame:
    sql = """
        SELECT * FROM games ORDER BY game_date
    """
    df = pd.read_sql(sql, _conn())
    df["game_date"] = pd.to_datetime(df["game_date"])
    completed = df.dropna(subset=["win"]).copy()
    completed["game_num"]    = range(1, len(completed) + 1)
    completed["cum_wins"]    = completed["win"].cumsum().astype(int)
    completed["cum_losses"]  = (1 - completed["win"]).cumsum().astype(int)
    completed["cum_run_diff"]= completed["run_differential"].cumsum()
    completed["cum_win_pct"] = (completed["cum_wins"] / completed["game_num"]).round(3)
    completed["roll_win_10"] = completed["win"].rolling(10, min_periods=1).mean().round(3)
    completed["roll_win_5"]  = completed["win"].rolling(5,  min_periods=1).mean().round(3)
    completed["result"]      = completed["win"].map({1: "W", 0: "L"})
    return completed


@st.cache_data(ttl=300)
def standings() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM standings ORDER BY league_rank", _conn())


@st.cache_data(ttl=300)
def transactions() -> pd.DataFrame:
    return pd.read_sql(
        "SELECT date, player_name, type_desc, from_team, to_team, description "
        "FROM transactions ORDER BY date DESC",
        _conn()
    )


@st.cache_data(ttl=300)
def roster() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM roster ORDER BY position, player_name", _conn())
