"""
Cached data-access layer for the Streamlit app.
All pages import from here — one place to change if the schema changes.
"""

import sqlite3
from pathlib import Path

import pandas as pd
import streamlit as st

DB_PATH = Path(__file__).parent / "data" / "database" / "baseball.db"

LEVEL_ORDER = {"MLB": 0, "AAA": 1, "AA": 2}


def _conn() -> sqlite3.Connection:
    return sqlite3.connect(DB_PATH)


# ── Core tables ───────────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def seasons_available() -> list[int]:
    try:
        df = pd.read_sql("SELECT DISTINCT season FROM games ORDER BY season DESC", _conn())
        return df["season"].tolist()
    except Exception:
        return [2026]


@st.cache_data(ttl=300)
def teams_in_db() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM teams ORDER BY season DESC", _conn())


@st.cache_data(ttl=300)
def batting(season: int = 2026, team_id: int | None = None) -> pd.DataFrame:
    where = f"b.season={season}"
    if team_id:
        where += f" AND b.team_id={team_id}"
    sql = f"""
        SELECT
            r.player_name, r.position, r.bats,
            b.games, b.pa, b.ab, b.runs, b.hits,
            b.doubles, b.triples, b.hr, b.rbi,
            b.bb, b.so, b.hbp, b.sb, b.cs, b.gdp,
            b.avg, b.obp, b.slg, b.ops, b.babip,
            b.sf, b.sh,
            b.player_id, b.team_id, b.season,
            t.team_name, t.org_level
        FROM batting_stats b
        JOIN roster r ON b.player_id = r.player_id
        LEFT JOIN teams t ON b.team_id = t.team_id AND b.season = t.season
        WHERE {where}
        ORDER BY b.ops DESC NULLS LAST
    """
    df = pd.read_sql(sql, _conn())
    df["xbh"]    = df["doubles"].fillna(0) + df["triples"].fillna(0) + df["hr"].fillna(0)
    df["bb_pct"] = (df["bb"]  / df["pa"].replace(0, float("nan"))).round(3)
    df["k_pct"]  = (df["so"]  / df["pa"].replace(0, float("nan"))).round(3)
    df["iso"]    = (df["slg"] - df["avg"]).round(3)
    return df


@st.cache_data(ttl=300)
def pitching(season: int = 2026, team_id: int | None = None) -> pd.DataFrame:
    where = f"p.season={season}"
    if team_id:
        where += f" AND p.team_id={team_id}"
    sql = f"""
        SELECT
            r.player_name, r.throws_hand,
            p.games, p.games_started, p.wins, p.losses,
            p.saves, p.save_opps, p.holds, p.blown_saves,
            p.ip, p.era, p.whip,
            p.hits, p.runs, p.earned_runs, p.hr,
            p.bb, p.so, p.hbp,
            p.k9, p.bb9, p.h9, p.hr9, p.k_bb,
            p.opp_avg, p.batters_faced, p.wild_pitches,
            p.player_id, p.team_id, p.season,
            t.team_name, t.org_level
        FROM pitching_stats p
        JOIN roster r ON p.player_id = r.player_id
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.season = t.season
        WHERE {where}
        ORDER BY p.era ASC NULLS LAST
    """
    df = pd.read_sql(sql, _conn())
    import numpy as np
    ip_safe = df["ip"].replace(0, float("nan"))
    df["fip"] = (
        (13 * df["hr"].fillna(0)
         + 3 * (df["bb"].fillna(0) + df["hbp"].fillna(0))
         - 2 * df["so"].fillna(0)) / ip_safe + 3.10
    ).round(2)
    df["role"]   = df["games_started"].apply(lambda x: "Starter" if x >= 3 else "Reliever")
    df["k_pct"]  = (df["so"] / df["batters_faced"].replace(0, float("nan"))).round(3)
    df["bb_pct"] = (df["bb"] / df["batters_faced"].replace(0, float("nan"))).round(3)
    return df


@st.cache_data(ttl=300)
def games(season: int = 2026, team_id: int | None = None) -> pd.DataFrame:
    where = f"season={season}"
    if team_id:
        where += f" AND team_id={team_id}"
    sql = f"SELECT * FROM games WHERE {where} ORDER BY game_date"
    df = pd.read_sql(sql, _conn())
    df["game_date"] = pd.to_datetime(df["game_date"])
    completed = df.dropna(subset=["win"]).copy()
    if completed.empty:
        return completed
    completed["game_num"]     = range(1, len(completed) + 1)
    completed["cum_wins"]     = completed["win"].cumsum().astype(int)
    completed["cum_losses"]   = (1 - completed["win"]).cumsum().astype(int)
    completed["cum_run_diff"] = completed["run_differential"].cumsum()
    completed["cum_win_pct"]  = (completed["cum_wins"] / completed["game_num"]).round(3)
    completed["roll_win_10"]  = completed["win"].rolling(10, min_periods=1).mean().round(3)
    completed["roll_win_5"]   = completed["win"].rolling(5,  min_periods=1).mean().round(3)
    completed["result"]       = completed["win"].map({1: "W", 0: "L"})
    return completed


@st.cache_data(ttl=300)
def standings(season: int = 2026, league_id: int | None = None) -> pd.DataFrame:
    where = f"season={season}"
    if league_id:
        where += f" AND league_id={league_id}"
    return pd.read_sql(
        f"SELECT * FROM standings WHERE {where} ORDER BY league_rank", _conn()
    )


@st.cache_data(ttl=300)
def transactions(team_id: int | None = None, season: int = 2026) -> pd.DataFrame:
    # transactions table has no team_id; show all transactions for the season
    return pd.read_sql(
        f"SELECT date, player_name, type_code, type_desc, from_team, to_team, description "
        f"FROM transactions WHERE date LIKE '{season}%' ORDER BY date DESC",
        _conn()
    )


@st.cache_data(ttl=300)
def roster() -> pd.DataFrame:
    return pd.read_sql("SELECT * FROM roster ORDER BY position, player_name", _conn())


# ── Prospect queries ──────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def prospects() -> pd.DataFrame:
    sql = """
        SELECT p.rank, p.player_name, p.position, p.eta, p.notes, p.player_id
        FROM prospects p
        ORDER BY p.rank
    """
    return pd.read_sql(sql, _conn())


@st.cache_data(ttl=300)
def prospect_stats(season: int = 2026) -> pd.DataFrame:
    """Prospects joined with their current batting + pitching stats."""
    bat_sql = f"""
        SELECT pr.rank, pr.player_name, pr.position, pr.eta, pr.notes,
               'Hitter' as stat_type,
               b.games, b.pa, b.avg, b.obp, b.slg, b.ops, b.hr, b.rbi,
               b.sb, b.bb_pct, b.k_pct, b.babip,
               NULL as era, NULL as whip, NULL as ip, NULL as k9, NULL as fip,
               t.team_name, t.org_level
        FROM prospects pr
        JOIN batting_stats b ON pr.player_id = b.player_id AND b.season={season}
        LEFT JOIN teams t ON b.team_id = t.team_id AND b.season = t.season
        WHERE pr.player_id IS NOT NULL
    """
    pit_sql = f"""
        SELECT pr.rank, pr.player_name, pr.position, pr.eta, pr.notes,
               'Pitcher' as stat_type,
               p.games, NULL as pa, NULL as avg, NULL as obp, NULL as slg, NULL as ops,
               NULL as hr, NULL as rbi, NULL as sb, NULL as bb_pct, NULL as k_pct,
               NULL as babip, p.era, p.whip, p.ip, p.k9,
               (13*p.hr + 3*(p.bb+p.hbp) - 2*p.so) / NULLIF(p.ip, 0) + 3.10 as fip,
               t.team_name, t.org_level
        FROM prospects pr
        JOIN pitching_stats p ON pr.player_id = p.player_id AND p.season={season}
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.season = t.season
        WHERE pr.player_id IS NOT NULL
    """
    try:
        df = pd.concat([
            pd.read_sql(bat_sql, _conn()),
            pd.read_sql(pit_sql, _conn()),
        ], ignore_index=True)
        return df.sort_values(["rank", "stat_type"])
    except Exception:
        return pd.DataFrame()


# ── Player development tracker ────────────────────────────────────────────────

@st.cache_data(ttl=300)
def player_career_batting(player_id: int) -> pd.DataFrame:
    sql = """
        SELECT b.season, b.games, b.pa, b.ab, b.hits, b.hr, b.rbi, b.sb,
               b.avg, b.obp, b.slg, b.ops, b.babip, b.bb, b.so,
               b.doubles, b.triples,
               t.team_name, t.org_level
        FROM batting_stats b
        LEFT JOIN teams t ON b.team_id = t.team_id AND b.season = t.season
        WHERE b.player_id = ?
        ORDER BY b.season, t.org_level
    """
    return pd.read_sql(sql, _conn(), params=(player_id,))


@st.cache_data(ttl=300)
def player_career_pitching(player_id: int) -> pd.DataFrame:
    sql = """
        SELECT p.season, p.games, p.games_started, p.ip, p.wins, p.losses,
               p.saves, p.era, p.whip, p.so, p.bb, p.hr,
               p.k9, p.bb9, p.opp_avg,
               t.team_name, t.org_level
        FROM pitching_stats p
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.season = t.season
        WHERE p.player_id = ?
        ORDER BY p.season, t.org_level
    """
    return pd.read_sql(sql, _conn(), params=(player_id,))


@st.cache_data(ttl=300)
def player_transactions(player_id: int) -> pd.DataFrame:
    sql = """
        SELECT date, type_desc, from_team, to_team, description
        FROM transactions
        WHERE player_id = ?
        ORDER BY date
    """
    return pd.read_sql(sql, _conn(), params=(player_id,))


@st.cache_data(ttl=300)
def all_players_with_stats() -> pd.DataFrame:
    """All players who have any stat line in the DB — for search dropdowns."""
    sql = """
        SELECT DISTINCT r.player_id, r.player_name, r.position
        FROM roster r
        WHERE r.player_id IN (SELECT player_id FROM batting_stats)
           OR r.player_id IN (SELECT player_id FROM pitching_stats)
        ORDER BY r.player_name
    """
    return pd.read_sql(sql, _conn())


# ── Org-level summary ─────────────────────────────────────────────────────────

@st.cache_data(ttl=300)
def org_batting_summary(season: int = 2026) -> pd.DataFrame:
    """Team-level batting aggregates for each org level."""
    sql = f"""
        SELECT t.org_level, t.team_name,
               COUNT(DISTINCT b.player_id) as players,
               ROUND(AVG(b.ops), 3) as avg_ops,
               ROUND(AVG(b.avg), 3) as avg_avg,
               ROUND(AVG(b.obp), 3) as avg_obp,
               ROUND(AVG(b.slg), 3) as avg_slg,
               SUM(b.hr)  as total_hr,
               SUM(b.sb)  as total_sb,
               SUM(b.rbi) as total_rbi
        FROM batting_stats b
        LEFT JOIN teams t ON b.team_id = t.team_id AND b.season = t.season
        WHERE b.season = {season}
        GROUP BY t.org_level, t.team_name
    """
    df = pd.read_sql(sql, _conn())
    df["_order"] = df["org_level"].map(LEVEL_ORDER).fillna(99)
    return df.sort_values("_order").drop(columns="_order")


@st.cache_data(ttl=300)
def org_pitching_summary(season: int = 2026) -> pd.DataFrame:
    """Team-level pitching aggregates for each org level."""
    sql = f"""
        SELECT t.org_level, t.team_name,
               COUNT(DISTINCT p.player_id) as pitchers,
               ROUND(SUM(p.earned_runs)*9.0 / NULLIF(SUM(p.ip), 0), 2) as team_era,
               ROUND((SUM(p.hits)+SUM(p.bb)) / NULLIF(SUM(p.ip), 0), 2) as team_whip,
               SUM(p.so) as total_k,
               ROUND(SUM(p.so)*9.0 / NULLIF(SUM(p.ip), 0), 2) as k9,
               ROUND(SUM(p.bb)*9.0 / NULLIF(SUM(p.ip), 0), 2) as bb9,
               ROUND(SUM(p.ip), 1) as total_ip
        FROM pitching_stats p
        LEFT JOIN teams t ON p.team_id = t.team_id AND p.season = t.season
        WHERE p.season = {season}
        GROUP BY t.org_level, t.team_name
    """
    df = pd.read_sql(sql, _conn())
    df["_order"] = df["org_level"].map(LEVEL_ORDER).fillna(99)
    return df.sort_values("_order").drop(columns="_order")


@st.cache_data(ttl=300)
def org_records(season: int = 2026) -> pd.DataFrame:
    """Win-loss record per team_id in the games table."""
    sql = f"""
        SELECT t.org_level, t.team_name,
               COUNT(*) as gp,
               SUM(g.win) as wins,
               SUM(1 - g.win) as losses,
               ROUND(AVG(g.win), 3) as win_pct,
               SUM(g.run_differential) as run_diff
        FROM games g
        LEFT JOIN teams t ON t.season = {season}
            AND (g.home_away = 'home' AND t.team_id = (
                    SELECT team_id FROM teams WHERE season={season}
                    ORDER BY team_id LIMIT 1))
        WHERE g.season = {season} AND g.win IS NOT NULL
        GROUP BY t.org_level, t.team_name
    """
    # Simpler fallback: just count from games directly
    sql2 = f"""
        SELECT
            COUNT(*) as gp,
            SUM(win) as wins,
            SUM(1-win) as losses,
            ROUND(AVG(win), 3) as win_pct,
            SUM(run_differential) as run_diff
        FROM games WHERE season={season} AND win IS NOT NULL
    """
    df = pd.read_sql(sql2, _conn())
    return df
