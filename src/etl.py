"""
ETL pipeline: pull raw API data → flatten → insert into SQLite.
Each extract_* function returns a list of clean dicts ready for bulk_upsert.
"""
from __future__ import annotations

from typing import Any

from config import TEAM_ID, SEASON, SPORT_ID
from database import bulk_upsert
from utils import get_logger, safe_float, safe_int, safe_str, innings_to_float

log = get_logger(__name__)


# ── Teams ─────────────────────────────────────────────────────────────────────

def extract_team(raw: dict, team_id: int = TEAM_ID, season: int = SEASON) -> list[dict]:
    teams = raw.get("teams", [])
    rows = []
    for t in teams:
        rows.append({
            "team_id":    t.get("id", team_id),
            "team_name":  safe_str(t.get("name")),
            "season":     season,
            "sport_id":   safe_int(t.get("sport", {}).get("id")),
            "league_id":  safe_int(t.get("league", {}).get("id")),
            "venue_name": safe_str(t.get("venue", {}).get("name")),
        })
    if not rows:
        rows.append({"team_id": team_id, "team_name": "Reading Fightin Phils",
                     "season": season, "sport_id": SPORT_ID,
                     "league_id": 113, "venue_name": "FirstEnergy Stadium"})
    return rows


def load_team(raw: dict) -> None:
    rows = extract_team(raw)
    bulk_upsert("teams", rows)
    log.info("Loaded %d team row(s)", len(rows))


# ── Roster ────────────────────────────────────────────────────────────────────

def extract_roster(raw: dict) -> list[dict]:
    rows = []
    for p in raw.get("roster", []):
        person = p.get("person", {})
        pos    = p.get("position", {})
        rows.append({
            "player_id":    safe_int(person.get("id")),
            "player_name":  safe_str(person.get("fullName")),
            "first_name":   safe_str(person.get("firstName")),
            "last_name":    safe_str(person.get("lastName")),
            "position":     safe_str(pos.get("abbreviation")),
            "pos_type":     safe_str(pos.get("type")),
            "jersey":       safe_str(p.get("jerseyNumber")),
            "bats":         safe_str(person.get("batSide", {}).get("code")),
            "throws_hand":  safe_str(person.get("pitchHand", {}).get("code")),
            "birth_date":   safe_str(person.get("birthDate")),
            "birth_city":   safe_str(person.get("birthCity")),
            "birth_country":safe_str(person.get("birthCountry")),
            "height":       safe_str(person.get("height")),
            "weight":       safe_int(person.get("weight")),
            "mlb_debut":    safe_str(person.get("mlbDebutDate")),
            "active":       1 if person.get("active", True) else 0,
        })
    return [r for r in rows if r["player_id"] is not None]


def load_roster(raw: dict) -> None:
    rows = extract_roster(raw)
    bulk_upsert("roster", rows)
    log.info("Loaded %d roster players", len(rows))


# ── Batting ───────────────────────────────────────────────────────────────────

def extract_batting(raw: dict, team_id: int = TEAM_ID, season: int = SEASON) -> list[dict]:
    rows = []
    for group in raw.get("stats", []):
        for split in group.get("splits", []):
            player = split.get("player", {})
            s      = split.get("stat", {})
            pid    = safe_int(player.get("id"))
            if pid is None:
                continue
            rows.append({
                "player_id":    pid,
                "team_id":      team_id,
                "season":       season,
                "games":        safe_int(s.get("gamesPlayed")),
                "pa":           safe_int(s.get("plateAppearances")),
                "ab":           safe_int(s.get("atBats")),
                "runs":         safe_int(s.get("runs")),
                "hits":         safe_int(s.get("hits")),
                "doubles":      safe_int(s.get("doubles")),
                "triples":      safe_int(s.get("triples")),
                "hr":           safe_int(s.get("homeRuns")),
                "rbi":          safe_int(s.get("rbi")),
                "bb":           safe_int(s.get("baseOnBalls")),
                "ibb":          safe_int(s.get("intentionalWalks")),
                "so":           safe_int(s.get("strikeOuts")),
                "hbp":          safe_int(s.get("hitByPitch")),
                "sf":           safe_int(s.get("sacFlies")),
                "sh":           safe_int(s.get("sacBunts")),
                "gdp":          safe_int(s.get("groundIntoDoublePlay")),
                "sb":           safe_int(s.get("stolenBases")),
                "cs":           safe_int(s.get("caughtStealing")),
                "avg":          safe_float(s.get("avg")),
                "obp":          safe_float(s.get("obp")),
                "slg":          safe_float(s.get("slg")),
                "ops":          safe_float(s.get("ops")),
                "babip":        safe_float(s.get("babip")),
                "total_bases":  safe_int(s.get("totalBases")),
                "left_on_base": safe_int(s.get("leftOnBase")),
                "ground_outs":  safe_int(s.get("groundOuts")),
                "air_outs":     safe_int(s.get("airOuts")),
                "pitches_seen": safe_int(s.get("numberOfPitches")),
            })
    return rows


def load_batting(raw: dict, team_id: int = TEAM_ID, season: int = SEASON) -> None:
    rows = extract_batting(raw, team_id, season)
    bulk_upsert("batting_stats", rows)
    log.info("Loaded %d batting stat rows", len(rows))


# ── Pitching ──────────────────────────────────────────────────────────────────

def extract_pitching(raw: dict, team_id: int = TEAM_ID, season: int = SEASON) -> list[dict]:
    rows = []
    for group in raw.get("stats", []):
        for split in group.get("splits", []):
            player = split.get("player", {})
            s      = split.get("stat", {})
            pid    = safe_int(player.get("id"))
            if pid is None:
                continue
            # Only keep pitcher rows (gamesStarted or gamesPitched present)
            if not (s.get("gamesPitched") or s.get("gamesStarted")):
                continue
            rows.append({
                "player_id":     pid,
                "team_id":       team_id,
                "season":        season,
                "games":         safe_int(s.get("gamesPitched")),
                "games_started": safe_int(s.get("gamesStarted")),
                "wins":          safe_int(s.get("wins")),
                "losses":        safe_int(s.get("losses")),
                "saves":         safe_int(s.get("saves")),
                "save_opps":     safe_int(s.get("saveOpportunities")),
                "holds":         safe_int(s.get("holds")),
                "blown_saves":   safe_int(s.get("blownSaves")),
                "cg":            safe_int(s.get("completeGames")),
                "sho":           safe_int(s.get("shutouts")),
                "ip":            innings_to_float(s.get("inningsPitched")),
                "era":           safe_float(s.get("era")),
                "whip":          safe_float(s.get("whip")),
                "hits":          safe_int(s.get("hits")),
                "runs":          safe_int(s.get("runs")),
                "earned_runs":   safe_int(s.get("earnedRuns")),
                "hr":            safe_int(s.get("homeRuns")),
                "bb":            safe_int(s.get("baseOnBalls")),
                "ibb":           safe_int(s.get("intentionalWalks")),
                "hbp":           safe_int(s.get("hitBatsmen")),
                "so":            safe_int(s.get("strikeOuts")),
                "k9":            safe_float(s.get("strikeoutsPer9Inn")),
                "bb9":           safe_float(s.get("walksPer9Inn")),
                "h9":            safe_float(s.get("hitsPer9Inn")),
                "hr9":           safe_float(s.get("homeRunsPer9")),
                "k_bb":          safe_float(s.get("strikeoutWalkRatio")),
                "opp_avg":       safe_float(s.get("avg")),
                "opp_obp":       safe_float(s.get("obp")),
                "opp_slg":       safe_float(s.get("slg")),
                "opp_ops":       safe_float(s.get("ops")),
                "batters_faced": safe_int(s.get("battersFaced")),
                "pitches":       safe_int(s.get("numberOfPitches")),
                "strikes":       safe_int(s.get("strikes")),
                "wild_pitches":  safe_int(s.get("wildPitches")),
                "balks":         safe_int(s.get("balks")),
            })
    return rows


def load_pitching(raw: dict, team_id: int = TEAM_ID, season: int = SEASON) -> None:
    rows = extract_pitching(raw, team_id, season)
    bulk_upsert("pitching_stats", rows)
    log.info("Loaded %d pitching stat rows", len(rows))


# ── Games ─────────────────────────────────────────────────────────────────────

def extract_games(schedule_raw: dict, boxscores: dict[int, dict],
                  linescores: dict[int, dict],
                  team_id: int = TEAM_ID, season: int = SEASON) -> list[dict]:
    rows = []
    for date_entry in schedule_raw.get("dates", []):
        for game in date_entry.get("games", []):
            pk   = safe_int(game.get("gamePk"))
            if pk is None:
                continue

            teams  = game.get("teams", {})
            home_t = teams.get("home", {})
            away_t = teams.get("away", {})

            if home_t.get("team", {}).get("id") == team_id:
                home_away  = "home"
                team_side  = home_t
                opp_side   = away_t
            else:
                home_away  = "away"
                team_side  = away_t
                opp_side   = home_t

            opp_team  = opp_side.get("team", {})
            team_score = safe_int(team_side.get("score"))
            opp_score  = safe_int(opp_side.get("score"))
            win = None
            if team_score is not None and opp_score is not None:
                win = 1 if team_score > opp_score else 0

            run_diff = None
            if team_score is not None and opp_score is not None:
                run_diff = team_score - opp_score

            # Pull from boxscore
            box   = boxscores.get(pk, {})
            ls    = linescores.get(pk, {})

            box_home = box.get("teams", {}).get("home" if home_away == "home" else "away", {})
            box_opp  = box.get("teams", {}).get("away" if home_away == "home" else "home", {})

            t_stats = box_home.get("teamStats", {})
            o_stats = box_opp.get("teamStats", {})

            team_hits   = safe_int(t_stats.get("batting", {}).get("hits"))
            team_errors = safe_int(t_stats.get("fielding", {}).get("errors"))
            opp_hits    = safe_int(o_stats.get("batting", {}).get("hits"))
            opp_errors  = safe_int(o_stats.get("fielding", {}).get("errors"))

            # Pitching decisions from linescore
            wp = lp = sv = ""
            decisions = ls.get("decisions", {})
            if decisions:
                wp = safe_str(decisions.get("winner", {}).get("fullName"))
                lp = safe_str(decisions.get("loser",  {}).get("fullName"))
                sv = safe_str(decisions.get("save",   {}).get("fullName"))

            info = box.get("teams", {})
            venue  = game.get("venue", {})
            weather = game.get("weather", {})

            rows.append({
                "game_pk":          pk,
                "team_id":          team_id,
                "season":           season,
                "game_date":        safe_str(game.get("gameDate", ""))[:10],
                "home_away":        home_away,
                "opponent_id":      safe_int(opp_team.get("id")),
                "opponent_name":    safe_str(opp_team.get("name")),
                "team_score":       team_score,
                "opp_score":        opp_score,
                "win":              win,
                "team_hits":        team_hits,
                "team_errors":      team_errors,
                "opp_hits":         opp_hits,
                "opp_errors":       opp_errors,
                "run_differential": run_diff,
                "game_duration":    safe_str(ls.get("gameDurationMinutes")),
                "attendance":       safe_int(game.get("attendance")),
                "venue_name":       safe_str(venue.get("name")),
                "winning_pitcher":  wp,
                "losing_pitcher":   lp,
                "save_pitcher":     sv,
                "series_game_number": safe_int(game.get("seriesGameNumber")),
                "games_in_series":  safe_int(game.get("gamesInSeries")),
                "weather_condition": safe_str(weather.get("condition")),
                "weather_temp":     safe_str(weather.get("temp")),
                "weather_wind":     safe_str(weather.get("wind")),
            })
    return rows


def load_games(schedule_raw: dict, boxscores: dict, linescores: dict,
               team_id: int = TEAM_ID, season: int = SEASON) -> None:
    rows = extract_games(schedule_raw, boxscores, linescores, team_id, season)
    bulk_upsert("games", rows)
    log.info("Loaded %d game rows", len(rows))


# ── Standings ─────────────────────────────────────────────────────────────────

def extract_standings(raw: dict, season: int = SEASON, league_id: int | None = None) -> list[dict]:
    rows = []
    from datetime import date
    snapshot = str(date.today())

    for record in raw.get("records", []):
        div_id  = safe_int(record.get("division", {}).get("id"))
        lg_id   = league_id or safe_int(record.get("league", {}).get("id"))
        for tr in record.get("teamRecords", []):
            team   = tr.get("team", {})
            lr     = tr.get("leagueRecord", {})
            splits = {s["type"]: s for s in tr.get("records", {}).get("splitRecords", [])}
            home   = splits.get("home", {})
            away   = splits.get("away", {})
            last10 = splits.get("lastTen", {})

            rows.append({
                "season":       season,
                "snapshot_date": snapshot,
                "team_id":      safe_int(team.get("id")),
                "team_name":    safe_str(team.get("name")),
                "league_id":    lg_id,
                "division_id":  div_id,
                "wins":         safe_int(lr.get("wins")),
                "losses":       safe_int(lr.get("losses")),
                "ties":         safe_int(lr.get("ties", 0)),
                "pct":          safe_float(lr.get("pct")),
                "games_back":   safe_str(tr.get("gamesBack")),
                "wc_games_back":safe_str(tr.get("wildCardGamesBack")),
                "division_rank":safe_int(tr.get("divisionRank")),
                "league_rank":  safe_int(tr.get("leagueRank")),
                "home_wins":    safe_int(home.get("wins")),
                "home_losses":  safe_int(home.get("losses")),
                "away_wins":    safe_int(away.get("wins")),
                "away_losses":  safe_int(away.get("losses")),
                "last_10_wins": safe_int(last10.get("wins")),
                "last_10_losses": safe_int(last10.get("losses")),
                "streak":       safe_str(tr.get("streak", {}).get("streakCode")),
                "rs":           safe_int(tr.get("runsScored")),
                "ra":           safe_int(tr.get("runsAllowed")),
            })
    return rows


def load_standings(raw: dict, season: int = SEASON, league_id: int | None = None) -> None:
    rows = extract_standings(raw, season, league_id)
    bulk_upsert("standings", rows)
    log.info("Loaded %d standing rows", len(rows))


# ── Transactions ──────────────────────────────────────────────────────────────

def extract_transactions(raw: dict) -> list[dict]:
    rows = []
    for t in raw.get("transactions", []):
        rows.append({
            "transaction_id": safe_int(t.get("id")),
            "player_id":      safe_int(t.get("person", {}).get("id")),
            "player_name":    safe_str(t.get("person", {}).get("fullName")),
            "type_code":      safe_str(t.get("typeCode")),
            "type_desc":      safe_str(t.get("typeDesc")),
            "from_team":      safe_str(t.get("fromTeam", {}).get("name")),
            "to_team":        safe_str(t.get("toTeam", {}).get("name")),
            "date":           safe_str(t.get("date")),
            "effective_date": safe_str(t.get("effectiveDate")),
            "description":    safe_str(t.get("description")),
        })
    return [r for r in rows if r["transaction_id"] is not None]


def load_transactions(raw: dict) -> None:
    rows = extract_transactions(raw)
    bulk_upsert("transactions", rows)
    log.info("Loaded %d transaction rows", len(rows))
