"""
Entry point.  Run:  py main.py

Steps:
  1. Init database
  2. Fetch & load team / roster
  3. Fetch & load batting / pitching stats
  4. Fetch schedule → fetch boxscores → load games
  5. Fetch & load standings
  6. Fetch & load transactions
  7. Validate data
  8. Compute analytics
  9. Generate charts
  10. Export dashboard CSVs
  11. Generate Markdown report
"""

import sys
import time
from pathlib import Path

# ── Bootstrap path so src.* imports work from project root ───────────────────
sys.path.insert(0, str(Path(__file__).parent))

import config
from database import init_db
from src import api, etl
from src.analytics import (
    team_summary, batting_leaders, pitching_leaders, rolling_metrics,
    home_away_splits, monthly_splits, opponent_splits, standings_summary,
    export_dashboard_csvs, batting_leaderboard, pitching_leaderboard,
)
from src.clean import validate_all, export_validation_report
from src.models import PipelineResult
from src.report import generate_report
from src.visualizations import generate_all_charts
from utils import get_logger

log = get_logger("main")


def _step(label: str) -> None:
    print(f"  --> {label}")


def run_pipeline() -> PipelineResult:
    print("=" * 55)
    print("  Reading Fightin Phils Analytics Pipeline")
    print(f"  Team ID: {config.TEAM_ID}  |  Season: {config.SEASON}  |  DB: {config.DB_PATH.name}")
    print("=" * 55)

    t0 = time.perf_counter()

    # ── 1. Database ───────────────────────────────────────────────────────────
    _step("Initializing database")
    init_db()

    # ── 2. Team + Roster ──────────────────────────────────────────────────────
    _step("Fetching team info")
    team_raw = api.fetch_team_info()
    etl.load_team(team_raw)

    _step("Fetching roster")
    roster_raw = api.fetch_roster()
    etl.load_roster(roster_raw)

    # ── 3. Batting / Pitching ─────────────────────────────────────────────────
    _step("Fetching batting stats")
    bat_raw = api.fetch_batting_stats()
    etl.load_batting(bat_raw)

    _step("Fetching pitching stats")
    pit_raw = api.fetch_pitching_stats()
    etl.load_pitching(pit_raw)

    # ── 4. Schedule + Boxscores ───────────────────────────────────────────────
    _step("Fetching schedule")
    sched_raw = api.fetch_schedule()
    dates     = sched_raw.get("dates", [])
    game_pks  = [g["gamePk"] for d in dates for g in d.get("games", [])]

    print(f"     {len(game_pks)} games found -- fetching boxscores...")

    boxscores:  dict[int, dict] = {}
    linescores: dict[int, dict] = {}

    for i, pk in enumerate(game_pks, 1):
        if i % 25 == 0 or i == len(game_pks):
            print(f"     Boxscores: {i}/{len(game_pks)}")
        try:
            boxscores[pk]  = api.fetch_game_boxscore(pk)
            linescores[pk] = api.fetch_game_linescore(pk)
        except Exception as exc:
            log.warning("Boxscore fetch failed for game %s: %s", pk, exc)

    _step("Loading games into database")
    etl.load_games(sched_raw, boxscores, linescores)

    # ── 5. Standings ──────────────────────────────────────────────────────────
    _step("Fetching standings")
    try:
        standings_raw = api.fetch_standings()
        etl.load_standings(standings_raw)
    except Exception as exc:
        log.warning("Standings fetch failed: %s", exc)

    # ── 6. Transactions ───────────────────────────────────────────────────────
    _step("Fetching transactions")
    try:
        trans_raw = api.fetch_transactions()
        etl.load_transactions(trans_raw)
    except Exception as exc:
        log.warning("Transactions fetch failed: %s", exc)

    # ── 7. Validation ─────────────────────────────────────────────────────────
    _step("Validating data")
    val_report = validate_all()
    export_validation_report(val_report)
    if val_report.errors:
        print(f"  [!] {val_report.errors} validation error(s) found — see reports/validation_report.md")
    else:
        print(f"  [OK] Validation passed ({val_report.warnings} warnings)")

    # ── 8. Analytics ──────────────────────────────────────────────────────────
    _step("Computing analytics")
    summary_df   = team_summary()
    batting_df   = batting_leaders()
    pitching_df  = pitching_leaders()
    rolling_df   = rolling_metrics()
    monthly_df   = monthly_splits()
    ha_splits_df = home_away_splits()
    opp_splits_df= opponent_splits()
    standings_df = standings_summary()

    bat_boards = batting_leaderboard(batting_df)
    pit_boards = pitching_leaderboard(pitching_df)

    result = PipelineResult(
        team_summary     = summary_df,
        batting          = batting_df,
        pitching         = pitching_df,
        games            = rolling_df,   # rolling already has full game rows
        rolling          = rolling_df,
        standings        = standings_df,
        monthly          = monthly_df,
        home_away_splits = ha_splits_df,
        opponent_splits  = opp_splits_df,
        batting_boards   = bat_boards,
        pitching_boards  = pit_boards,
        validation_errors   = val_report.errors,
        validation_warnings = val_report.warnings,
    )

    # ── 9. Charts ─────────────────────────────────────────────────────────────
    _step("Generating charts")
    # Need the raw games df (not rolling) for win/loss timeline
    import pandas as pd
    from database import get_conn
    with get_conn() as conn:
        import sqlite3
        games_raw = pd.read_sql_query(
            f"SELECT * FROM games WHERE season={config.SEASON} ORDER BY game_date", conn
        )

    charts = generate_all_charts(batting_df, pitching_df, games_raw, rolling_df, monthly_df)
    result.charts = [str(c) for c in charts]

    # ── 10. Dashboard CSVs ────────────────────────────────────────────────────
    _step("Exporting dashboard CSVs")
    export_dashboard_csvs(batting_df, pitching_df, games_raw, rolling_df, standings_df, summary_df)

    # ── 11. Report ────────────────────────────────────────────────────────────
    _step("Generating season report")
    report_path = generate_report(result)

    # ── Summary ───────────────────────────────────────────────────────────────
    elapsed = time.perf_counter() - t0
    print("=" * 55)
    print(f"  Pipeline complete in {elapsed:.1f}s")
    print(f"  Charts: {len(charts)}  |  Validation errors: {val_report.errors}")
    print(f"  Report: {report_path}")
    print("=" * 55)
    return result


if __name__ == "__main__":
    run_pipeline()
