"""
Entry point — runs the full Phillies org pipeline.

    py main.py              # pulls all 3 levels for current SEASON
    py main.py --season 2025  # pull a specific season

Steps per team:
  1. Team info + roster
  2. Batting + pitching season stats
  3. Schedule → incremental boxscores (skips games already in DB)
  4. Standings + transactions

Then org-wide:
  5. Load prospect CSV → match to roster player_ids
  6. Validate
  7. Export processed CSVs
"""

import argparse
import sqlite3
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import config
from config import ORG_TEAMS, SEASON, SEASON_START, SEASON_END
from database import init_db, get_conn, bulk_upsert
from src import api, etl
from src.analytics import (
    team_summary, batting_leaders, pitching_leaders, rolling_metrics,
    home_away_splits, monthly_splits, standings_summary,
)
from src.clean import validate_all, export_validation_report
from utils import get_logger

log = get_logger("main")


# ── Prospects loader ──────────────────────────────────────────────────────────

def load_prospects() -> None:
    """Read prospects.csv, fuzzy-match player_ids from roster, upsert to DB."""
    csv_path = config.PROSPECTS_CSV
    if not csv_path.exists():
        log.warning("prospects.csv not found at %s — skipping", csv_path)
        return

    import pandas as pd
    df = pd.read_csv(csv_path)

    # Match names to roster table
    with get_conn() as conn:
        roster = pd.read_sql("SELECT player_id, player_name FROM roster", conn)

    roster_lower = {n.lower(): pid for n, pid in zip(roster["player_name"], roster["player_id"])}

    rows = []
    for _, row in df.iterrows():
        name = str(row["player_name"]).strip()
        pid  = roster_lower.get(name.lower())
        rows.append({
            "rank":        int(row["rank"]),
            "player_name": name,
            "position":    str(row.get("position", "")) or None,
            "eta":         int(row["eta"]) if str(row.get("eta","")).isdigit() else None,
            "notes":       str(row.get("notes", "")) or None,
            "player_id":   pid,
        })

    bulk_upsert("prospects", rows)
    matched = sum(1 for r in rows if r["player_id"] is not None)
    log.info("Prospects loaded: %d total, %d matched to roster", len(rows), matched)


# ── Incremental boxscore fetch ────────────────────────────────────────────────

def _existing_game_pks(season: int, team_id: int) -> set[int]:
    with get_conn() as conn:
        rows = conn.execute(
            "SELECT game_pk FROM games WHERE season=? AND team_id=?", (season, team_id)
        ).fetchall()
    return {r[0] for r in rows}


def fetch_team(team: dict, season: int, season_start: str, season_end: str) -> None:
    tid   = team["team_id"]
    name  = team["team_name"]
    level = team["level"]
    sid   = team["sport_id"]
    lid   = team["league_id"]

    print(f"\n  [{level}] {name}")

    # ── Team row ─────────────────────────────────────────────────────────────
    print("    --> team info + roster")
    try:
        team_raw = api.fetch_team_info(tid, season)
        # inject org_level since the API doesn't return it
        for t in team_raw.get("teams", []):
            t["_org_level"] = level
        rows = etl.extract_team(team_raw, tid, season)
        for r in rows:
            r["org_level"] = level
        bulk_upsert("teams", rows)
    except Exception as exc:
        log.warning("[%s] team info failed: %s", level, exc)

    # ── Roster ───────────────────────────────────────────────────────────────
    try:
        roster_raw = api.fetch_roster(tid, season)
        etl.load_roster(roster_raw)
    except Exception as exc:
        log.warning("[%s] roster failed: %s", level, exc)

    # ── Batting / Pitching stats ──────────────────────────────────────────────
    print("    --> season stats")
    try:
        bat_raw = api.fetch_batting_stats(tid, season, sid)
        etl.load_batting(bat_raw, tid, season)
    except Exception as exc:
        log.warning("[%s] batting stats failed: %s", level, exc)

    try:
        pit_raw = api.fetch_pitching_stats(tid, season, sid)
        etl.load_pitching(pit_raw, tid, season)
    except Exception as exc:
        log.warning("[%s] pitching stats failed: %s", level, exc)

    # ── Schedule + incremental boxscores ─────────────────────────────────────
    print("    --> schedule")
    try:
        sched_raw = api.fetch_schedule(tid, season, sid, season_start, season_end)
        dates     = sched_raw.get("dates", [])
        all_pks   = [g["gamePk"] for d in dates for g in d.get("games", [])]
        existing  = _existing_game_pks(season, tid)
        new_pks   = [pk for pk in all_pks if pk not in existing]

        print(f"    --> boxscores: {len(new_pks)} new / {len(all_pks)} total")
        boxscores:  dict[int, dict] = {}
        linescores: dict[int, dict] = {}

        for i, pk in enumerate(new_pks, 1):
            if i % 25 == 0 or i == len(new_pks):
                print(f"       {i}/{len(new_pks)}")
            try:
                boxscores[pk]  = api.fetch_game_boxscore(pk)
                linescores[pk] = api.fetch_game_linescore(pk)
            except Exception as exc:
                log.warning("boxscore %s failed: %s", pk, exc)

        # Build a partial schedule containing only new games for loading
        if new_pks:
            new_pk_set = set(new_pks)
            partial_sched = {"dates": [
                {"games": [g for g in d.get("games", []) if g["gamePk"] in new_pk_set]}
                for d in dates
            ]}
            etl.load_games(partial_sched, boxscores, linescores, tid, season)
    except Exception as exc:
        log.warning("[%s] schedule/games failed: %s", level, exc)

    # ── Standings ─────────────────────────────────────────────────────────────
    try:
        standings_raw = api.fetch_standings(lid, season)
        etl.load_standings(standings_raw, season, lid)
    except Exception as exc:
        log.warning("[%s] standings failed: %s", level, exc)

    # ── Transactions ──────────────────────────────────────────────────────────
    try:
        trans_raw = api.fetch_transactions(tid, season, season_start, season_end)
        etl.load_transactions(trans_raw)
    except Exception as exc:
        log.warning("[%s] transactions failed: %s", level, exc)


# ── Main ──────────────────────────────────────────────────────────────────────

def run_pipeline(season: int | None = None) -> None:
    s = season or SEASON
    s_start = f"{s}-03-20"
    s_end   = f"{s}-10-15"

    print("=" * 60)
    print(f"  Phillies Org Analytics Pipeline  |  Season: {s}")
    print("=" * 60)

    t0 = time.perf_counter()

    init_db()

    for team in ORG_TEAMS:
        fetch_team(team, s, s_start, s_end)

    print("\n  --> loading prospects")
    load_prospects()

    print("  --> validating")
    val = validate_all()
    export_validation_report(val)
    status = "[OK]" if val.errors == 0 else f"[!] {val.errors} errors"
    print(f"  {status} — {val.warnings} warnings")

    elapsed = time.perf_counter() - t0
    print("=" * 60)
    print(f"  Done in {elapsed:.1f}s")
    print("=" * 60)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--season", type=int, default=None,
                        help="Override season (default: config.SEASON)")
    args = parser.parse_args()
    run_pipeline(args.season)
