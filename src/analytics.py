"""
All analytics computations.
Reads from SQLite, returns DataFrames, writes processed CSVs.
"""

import sqlite3
from pathlib import Path

import numpy as np
import pandas as pd

from config import (
    PROCESSED_DIR, SEASON, TEAM_ID,
    MIN_PA_QUALIFY, MIN_IP_QUALIFY, ROLLING_WINDOWS,
)
from database import get_conn
from utils import get_logger

log = get_logger(__name__)


def _query(sql: str, params: tuple = ()) -> pd.DataFrame:
    with get_conn() as conn:
        return pd.read_sql_query(sql, conn, params=params)


def _save(df: pd.DataFrame, name: str) -> Path:
    path = PROCESSED_DIR / f"{name}.csv"
    df.to_csv(path, index=False)
    log.debug("Saved processed CSV → %s", path.name)
    return path


# ── Team Summary ──────────────────────────────────────────────────────────────

def team_summary() -> pd.DataFrame:
    games = _query(
        "SELECT * FROM games WHERE season=? ORDER BY game_date",
        (SEASON,)
    )
    if games.empty:
        log.warning("No games found for season %s", SEASON)
        return pd.DataFrame()

    completed = games.dropna(subset=["win"])
    wins   = int(completed["win"].sum())
    losses = int((1 - completed["win"]).sum())
    gp     = wins + losses
    win_pct = wins / gp if gp else 0.0

    rs = games["team_score"].sum()
    ra = games["opp_score"].sum()
    run_diff = int(rs - ra) if not (pd.isna(rs) or pd.isna(ra)) else 0

    # Pythagorean win % (exponent 1.83 for baseball)
    exp = 1.83
    pyth = (rs ** exp) / (rs ** exp + ra ** exp) if (rs and ra) else None

    # Team batting
    bat = _query(
        "SELECT * FROM batting_stats b JOIN roster r ON b.player_id=r.player_id "
        "WHERE b.season=? AND b.team_id=?",
        (SEASON, TEAM_ID)
    )
    team_ops  = bat["ops"].mean()  if not bat.empty else None
    team_avg  = bat["avg"].mean()  if not bat.empty else None
    team_obp  = bat["obp"].mean()  if not bat.empty else None
    team_slg  = bat["slg"].mean()  if not bat.empty else None
    total_hr  = bat["hr"].sum()    if not bat.empty else None
    total_sb  = bat["sb"].sum()    if not bat.empty else None

    # Team pitching
    pit = _query(
        "SELECT * FROM pitching_stats WHERE season=? AND team_id=?",
        (SEASON, TEAM_ID)
    )
    # ERA weighted by innings
    if not pit.empty and pit["ip"].notna().any():
        ip_total = pit["ip"].fillna(0).sum()
        er_total = pit["earned_runs"].fillna(0).sum()
        team_era  = (er_total * 9 / ip_total) if ip_total else None
        hits_p    = pit["hits"].fillna(0).sum()
        bb_p      = pit["bb"].fillna(0).sum()
        team_whip = (hits_p + bb_p) / ip_total if ip_total else None
        total_ks  = int(pit["so"].fillna(0).sum())
    else:
        team_era = team_whip = total_ks = None

    summary = pd.DataFrame([{
        "season":            SEASON,
        "team_id":           TEAM_ID,
        "games_played":      gp,
        "wins":              wins,
        "losses":            losses,
        "win_pct":           round(win_pct, 3),
        "pythagorean_win_pct": round(pyth, 3) if pyth else None,
        "runs_scored":       int(rs) if not pd.isna(rs) else None,
        "runs_allowed":      int(ra) if not pd.isna(ra) else None,
        "run_differential":  run_diff,
        "team_ops":          round(team_ops, 3) if team_ops else None,
        "team_avg":          round(team_avg, 3) if team_avg else None,
        "team_obp":          round(team_obp, 3) if team_obp else None,
        "team_slg":          round(team_slg, 3) if team_slg else None,
        "team_hr":           int(total_hr) if total_hr is not None else None,
        "team_sb":           int(total_sb) if total_sb is not None else None,
        "team_era":          round(team_era, 2) if team_era else None,
        "team_whip":         round(team_whip, 2) if team_whip else None,
        "team_strikeouts":   total_ks,
    }])
    _save(summary, "team_summary")
    return summary


# ── Batting Leaders ───────────────────────────────────────────────────────────

def batting_leaders() -> pd.DataFrame:
    df = _query(
        """
        SELECT b.*, r.player_name, r.position, r.bats
        FROM batting_stats b
        JOIN roster r ON b.player_id = r.player_id
        WHERE b.season = ? AND b.team_id = ?
        """,
        (SEASON, TEAM_ID)
    )
    if df.empty:
        return df

    # Extra calculated columns
    df["xbh"]       = df["doubles"].fillna(0) + df["triples"].fillna(0) + df["hr"].fillna(0)
    df["bb_rate"]   = (df["bb"].fillna(0) / df["pa"].replace(0, np.nan)).round(3)
    df["k_rate"]    = (df["so"].fillna(0) / df["pa"].replace(0, np.nan)).round(3)
    df["iso"]       = (df["slg"].fillna(0) - df["avg"].fillna(0)).round(3)  # Isolated power
    df["ab_per_hr"] = (df["ab"] / df["hr"].replace(0, np.nan)).round(1)

    _save(df, "batting")
    return df


def batting_leaderboard(df: pd.DataFrame, min_pa: int = MIN_PA_QUALIFY) -> dict[str, pd.DataFrame]:
    """Return dict of named leaderboard DataFrames."""
    qualified = df[df["pa"].fillna(0) >= min_pa].copy()
    cols      = ["player_name", "position", "games", "pa", "ab"]

    boards: dict[str, pd.DataFrame] = {}

    def board(sort_col: str, name: str, ascending: bool = False) -> None:
        sub = qualified[qualified[sort_col].notna()].sort_values(sort_col, ascending=ascending)
        boards[name] = sub[cols + [sort_col]].head(10).reset_index(drop=True)

    board("ops",     "ops_leaders")
    board("avg",     "avg_leaders")
    board("obp",     "obp_leaders")
    board("slg",     "slg_leaders")
    board("hr",      "hr_leaders")
    board("rbi",     "rbi_leaders")
    board("xbh",     "xbh_leaders")
    board("bb_rate", "walk_rate_leaders")
    board("k_rate",  "k_rate_leaders", ascending=True)
    board("iso",     "iso_leaders")
    board("sb",      "sb_leaders")
    board("babip",   "babip_leaders")

    return boards


# ── Pitching Leaders ──────────────────────────────────────────────────────────

def pitching_leaders() -> pd.DataFrame:
    df = _query(
        """
        SELECT p.*, r.player_name, r.throws_hand
        FROM pitching_stats p
        JOIN roster r ON p.player_id = r.player_id
        WHERE p.season = ? AND p.team_id = ?
        """,
        (SEASON, TEAM_ID)
    )
    if df.empty:
        return df

    # FIP = ((13*HR + 3*(BB+HBP) - 2*K) / IP) + 3.10  (league constant ~3.10 for MiLB)
    FIP_CONST = 3.10
    ip_safe = df["ip"].replace(0, np.nan)
    df["fip"] = ((13 * df["hr"].fillna(0)
                  + 3 * (df["bb"].fillna(0) + df["hbp"].fillna(0))
                  - 2 * df["so"].fillna(0)) / ip_safe + FIP_CONST).round(2)

    df["k_pct"]  = (df["so"].fillna(0) / df["batters_faced"].replace(0, np.nan)).round(3)
    df["bb_pct"] = (df["bb"].fillna(0) / df["batters_faced"].replace(0, np.nan)).round(3)

    _save(df, "pitching")
    return df


def pitching_leaderboard(df: pd.DataFrame, min_ip: float = MIN_IP_QUALIFY) -> dict[str, pd.DataFrame]:
    qualified = df[df["ip"].fillna(0) >= min_ip].copy()
    cols      = ["player_name", "throws_hand", "games", "games_started", "ip"]

    boards: dict[str, pd.DataFrame] = {}

    def board(sort_col: str, name: str, ascending: bool = True) -> None:
        sub = qualified[qualified[sort_col].notna()].sort_values(sort_col, ascending=ascending)
        boards[name] = sub[cols + [sort_col]].head(10).reset_index(drop=True)

    board("era",    "era_leaders")
    board("whip",   "whip_leaders")
    board("fip",    "fip_leaders")
    board("k9",     "k9_leaders",    ascending=False)
    board("k_bb",   "kbb_leaders",   ascending=False)
    board("opp_avg","opp_avg_leaders")
    board("bb9",    "bb9_leaders")

    # Relievers: saves and holds (no IP min)
    rel = df.copy()
    boards["saves_leaders"] = (rel[rel["saves"].fillna(0) > 0]
                                .sort_values("saves", ascending=False)
                                [["player_name", "games", "saves", "save_opps", "blown_saves", "era"]]
                                .head(10).reset_index(drop=True))
    boards["holds_leaders"] = (rel[rel["holds"].fillna(0) > 0]
                                .sort_values("holds", ascending=False)
                                [["player_name", "games", "holds", "era", "whip"]]
                                .head(10).reset_index(drop=True))
    return boards


# ── Rolling / Trend Metrics ───────────────────────────────────────────────────

def rolling_metrics() -> pd.DataFrame:
    games = _query(
        "SELECT * FROM games WHERE season=? ORDER BY game_date",
        (SEASON,)
    )
    if games.empty:
        return pd.DataFrame()

    games["game_date"] = pd.to_datetime(games["game_date"])
    games = games.sort_values("game_date").reset_index(drop=True)
    games["game_num"] = range(1, len(games) + 1)

    # Cumulative
    games["cum_wins"]     = games["win"].cumsum()
    games["cum_losses"]   = (1 - games["win"]).cumsum()
    games["cum_run_diff"] = games["run_differential"].cumsum()
    games["cum_win_pct"]  = games["cum_wins"] / games["game_num"]

    for w in ROLLING_WINDOWS:
        games[f"win_pct_{w}g"] = games["win"].rolling(w, min_periods=1).mean().round(3)
        games[f"run_diff_{w}g"] = games["run_differential"].rolling(w, min_periods=1).mean().round(2)

    _save(games, "rolling_metrics")
    return games


# ── Splits Analytics ─────────────────────────────────────────────────────────

def home_away_splits() -> pd.DataFrame:
    games = _query(
        "SELECT home_away, win, team_score, opp_score, run_differential "
        "FROM games WHERE season=? AND win IS NOT NULL",
        (SEASON,)
    )
    if games.empty:
        return pd.DataFrame()

    splits = games.groupby("home_away").agg(
        games=("win", "count"),
        wins=("win", "sum"),
        rs=("team_score", "sum"),
        ra=("opp_score", "sum"),
        avg_run_diff=("run_differential", "mean"),
    ).reset_index()
    splits["losses"]  = splits["games"] - splits["wins"]
    splits["win_pct"] = (splits["wins"] / splits["games"]).round(3)
    splits["avg_rs"]  = (splits["rs"] / splits["games"]).round(2)
    splits["avg_ra"]  = (splits["ra"] / splits["games"]).round(2)

    _save(splits, "home_away_splits")
    return splits


def monthly_splits() -> pd.DataFrame:
    games = _query(
        "SELECT game_date, win, team_score, opp_score, run_differential "
        "FROM games WHERE season=? AND win IS NOT NULL",
        (SEASON,)
    )
    if games.empty:
        return pd.DataFrame()

    games["game_date"] = pd.to_datetime(games["game_date"])
    games["month"]     = games["game_date"].dt.month
    games["month_name"]= games["game_date"].dt.strftime("%B")

    monthly = games.groupby(["month", "month_name"]).agg(
        games=("win", "count"),
        wins=("win", "sum"),
        rs=("team_score", "sum"),
        ra=("opp_score", "sum"),
    ).reset_index().sort_values("month")
    monthly["losses"]  = monthly["games"] - monthly["wins"]
    monthly["win_pct"] = (monthly["wins"] / monthly["games"]).round(3)

    _save(monthly, "monthly_splits")
    return monthly


def opponent_splits() -> pd.DataFrame:
    games = _query(
        "SELECT opponent_name, home_away, win, team_score, opp_score "
        "FROM games WHERE season=? AND win IS NOT NULL",
        (SEASON,)
    )
    if games.empty:
        return pd.DataFrame()

    splits = games.groupby("opponent_name").agg(
        games=("win", "count"),
        wins=("win", "sum"),
        rs=("team_score", "sum"),
        ra=("opp_score", "sum"),
    ).reset_index()
    splits["losses"]  = splits["games"] - splits["wins"]
    splits["win_pct"] = (splits["wins"] / splits["games"]).round(3)
    splits["run_diff"]= splits["rs"] - splits["ra"]
    splits = splits.sort_values("win_pct", ascending=False).reset_index(drop=True)

    _save(splits, "opponent_splits")
    return splits


# ── Standings Summary ─────────────────────────────────────────────────────────

def standings_summary() -> pd.DataFrame:
    df = _query(
        "SELECT * FROM standings WHERE season=? ORDER BY league_rank",
        (SEASON,)
    )
    if not df.empty:
        _save(df, "standings")
    return df


# ── Dashboard Export (all in one place) ──────────────────────────────────────

def export_dashboard_csvs(
    batting_df: pd.DataFrame,
    pitching_df: pd.DataFrame,
    games_df: pd.DataFrame,
    rolling_df: pd.DataFrame,
    standings_df: pd.DataFrame,
    summary_df: pd.DataFrame,
) -> None:
    from config import DASHBOARD_DIR
    for df, name in [
        (batting_df,   "batting"),
        (pitching_df,  "pitching"),
        (games_df,     "games"),
        (rolling_df,   "rolling_metrics"),
        (standings_df, "standings"),
        (summary_df,   "team_summary"),
    ]:
        if not df.empty:
            path = DASHBOARD_DIR / f"{name}.csv"
            df.to_csv(path, index=False)
            log.info("Dashboard CSV → %s", path.name)
