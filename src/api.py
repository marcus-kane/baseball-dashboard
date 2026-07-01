"""
Thin wrapper around MLB-StatsAPI.
All raw API calls live here; nothing else touches statsapi directly.
"""

import json
import time
from pathlib import Path
from typing import Any

import statsapi

from config import (
    TEAM_ID, SEASON, SPORT_ID, LEAGUE_ID,
    SEASON_START, SEASON_END, RAW_DIR, API_RATE_LIMIT_PAUSE,
)
from utils import get_logger

log = get_logger(__name__)


def _save_raw(name: str, data: Any) -> Path:
    path = RAW_DIR / f"{name}.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    log.debug("Saved raw → %s", path.name)
    return path


def _get(endpoint: str, params: dict, pause: float = API_RATE_LIMIT_PAUSE) -> dict:
    data = statsapi.get(endpoint, params)
    time.sleep(pause)
    return data


# ── Public fetch functions ────────────────────────────────────────────────────

def fetch_team_info(team_id: int = TEAM_ID, season: int = SEASON) -> dict:
    data = _get("team", {"teamId": team_id, "season": season})
    _save_raw(f"team_{team_id}_{season}", data)
    return data


def fetch_roster(team_id: int = TEAM_ID, season: int = SEASON) -> dict:
    """Full 40-man + active roster with player detail."""
    data = _get("team_roster", {
        "teamId": team_id,
        "season": season,
        "rosterType": "fullSeason",
    })
    _save_raw(f"roster_{team_id}_{season}", data)
    return data


def fetch_batting_stats(team_id: int = TEAM_ID, season: int = SEASON,
                        sport_id: int = SPORT_ID) -> dict:
    # playerPool=All is required to get every player, not just qualified leaders.
    # sportIds (plural) is the correct query param name.
    data = _get("stats", {
        "stats": "season",
        "group": "hitting",
        "teamId": team_id,
        "season": season,
        "sportIds": sport_id,
        "playerPool": "All",
        "limit": 200,
    })
    _save_raw(f"batting_{team_id}_{season}", data)
    return data


def fetch_pitching_stats(team_id: int = TEAM_ID, season: int = SEASON,
                         sport_id: int = SPORT_ID) -> dict:
    data = _get("stats", {
        "stats": "season",
        "group": "pitching",
        "teamId": team_id,
        "season": season,
        "sportIds": sport_id,
        "playerPool": "All",
        "limit": 200,
    })
    _save_raw(f"pitching_{team_id}_{season}", data)
    return data


def fetch_schedule(team_id: int = TEAM_ID, season: int = SEASON,
                   sport_id: int = SPORT_ID,
                   start_date: str = SEASON_START,
                   end_date: str = SEASON_END) -> dict:
    data = _get("schedule", {
        "teamId": team_id,
        "season": season,
        "sportId": sport_id,
        "gameType": "R",
        "startDate": start_date,
        "endDate": end_date,
    })
    _save_raw(f"schedule_{team_id}_{season}", data)
    return data


def fetch_game_boxscore(game_pk: int) -> dict:
    """Fetch boxscore for one game. Results NOT saved individually (too many files)."""
    return _get("game_boxscore", {"gamePk": game_pk}, pause=0.2)


def fetch_game_linescore(game_pk: int) -> dict:
    return _get("game_linescore", {"gamePk": game_pk}, pause=0.15)


def fetch_standings(league_id: int = LEAGUE_ID, season: int = SEASON) -> dict:
    data = _get("standings", {
        "leagueId": league_id,
        "season": season,
        "standingsTypes": "regularSeason",
    })
    _save_raw(f"standings_{league_id}_{season}", data)
    return data


def fetch_transactions(team_id: int = TEAM_ID, season: int = SEASON,
                       start_date: str = SEASON_START,
                       end_date: str = SEASON_END) -> dict:
    data = _get("transactions", {
        "teamId": team_id,
        "startDate": start_date,
        "endDate": end_date,
    })
    _save_raw(f"transactions_{team_id}_{season}", data)
    return data


def fetch_player_info(player_id: int) -> dict:
    return _get("person", {"personId": player_id}, pause=0.15)
