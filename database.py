"""
SQLite schema creation and upsert helpers.
All writes go through this module so the rest of the pipeline never touches raw SQL.
"""

import sqlite3
from contextlib import contextmanager
from typing import Generator

from config import DB_PATH
from utils import get_logger

log = get_logger(__name__)

DDL = """
PRAGMA journal_mode=WAL;
PRAGMA foreign_keys=ON;

CREATE TABLE IF NOT EXISTS teams (
    team_id     INTEGER PRIMARY KEY,
    team_name   TEXT NOT NULL,
    season      INTEGER NOT NULL,
    sport_id    INTEGER,
    league_id   INTEGER,
    venue_name  TEXT,
    UNIQUE(team_id, season)
);

CREATE TABLE IF NOT EXISTS roster (
    player_id   INTEGER PRIMARY KEY,
    player_name TEXT NOT NULL,
    first_name  TEXT,
    last_name   TEXT,
    position    TEXT,
    pos_type    TEXT,
    jersey      TEXT,
    bats        TEXT,
    throws_hand TEXT,
    birth_date  TEXT,
    birth_city  TEXT,
    birth_country TEXT,
    height      TEXT,
    weight      INTEGER,
    mlb_debut   TEXT,
    active      INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS batting_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL REFERENCES roster(player_id),
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    season          INTEGER NOT NULL,
    games           INTEGER,
    pa              INTEGER,
    ab              INTEGER,
    runs            INTEGER,
    hits            INTEGER,
    doubles         INTEGER,
    triples         INTEGER,
    hr              INTEGER,
    rbi             INTEGER,
    bb              INTEGER,
    ibb             INTEGER,
    so              INTEGER,
    hbp             INTEGER,
    sf              INTEGER,
    sh              INTEGER,
    gdp             INTEGER,
    sb              INTEGER,
    cs              INTEGER,
    avg             REAL,
    obp             REAL,
    slg             REAL,
    ops             REAL,
    babip           REAL,
    total_bases     INTEGER,
    left_on_base    INTEGER,
    ground_outs     INTEGER,
    air_outs        INTEGER,
    pitches_seen    INTEGER,
    UNIQUE(player_id, team_id, season)
);

CREATE TABLE IF NOT EXISTS pitching_stats (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    player_id       INTEGER NOT NULL REFERENCES roster(player_id),
    team_id         INTEGER NOT NULL REFERENCES teams(team_id),
    season          INTEGER NOT NULL,
    games           INTEGER,
    games_started   INTEGER,
    wins            INTEGER,
    losses          INTEGER,
    saves           INTEGER,
    save_opps       INTEGER,
    holds           INTEGER,
    blown_saves     INTEGER,
    cg              INTEGER,
    sho             INTEGER,
    ip              REAL,
    era             REAL,
    whip            REAL,
    hits            INTEGER,
    runs            INTEGER,
    earned_runs     INTEGER,
    hr              INTEGER,
    bb              INTEGER,
    ibb             INTEGER,
    hbp             INTEGER,
    so              INTEGER,
    k9              REAL,
    bb9             REAL,
    h9              REAL,
    hr9             REAL,
    k_bb            REAL,
    opp_avg         REAL,
    opp_obp         REAL,
    opp_slg         REAL,
    opp_ops         REAL,
    batters_faced   INTEGER,
    pitches         INTEGER,
    strikes         INTEGER,
    wild_pitches    INTEGER,
    balks           INTEGER,
    UNIQUE(player_id, team_id, season)
);

CREATE TABLE IF NOT EXISTS games (
    game_pk             INTEGER PRIMARY KEY,
    season              INTEGER NOT NULL,
    game_date           TEXT NOT NULL,
    home_away           TEXT NOT NULL,        -- 'home' or 'away'
    opponent_id         INTEGER,
    opponent_name       TEXT,
    team_score          INTEGER,
    opp_score           INTEGER,
    win                 INTEGER,              -- 1/0
    team_hits           INTEGER,
    team_errors         INTEGER,
    opp_hits            INTEGER,
    opp_errors          INTEGER,
    run_differential    INTEGER,
    game_duration       TEXT,
    attendance          INTEGER,
    venue_name          TEXT,
    winning_pitcher     TEXT,
    losing_pitcher      TEXT,
    save_pitcher        TEXT,
    series_game_number  INTEGER,
    games_in_series     INTEGER,
    weather_condition   TEXT,
    weather_temp        TEXT,
    weather_wind        TEXT
);

CREATE TABLE IF NOT EXISTS standings (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    season          INTEGER NOT NULL,
    snapshot_date   TEXT NOT NULL,
    team_id         INTEGER NOT NULL,
    team_name       TEXT,
    division_id     INTEGER,
    wins            INTEGER,
    losses          INTEGER,
    ties            INTEGER,
    pct             REAL,
    games_back      TEXT,
    wc_games_back   TEXT,
    division_rank   INTEGER,
    league_rank     INTEGER,
    home_wins       INTEGER,
    home_losses     INTEGER,
    away_wins       INTEGER,
    away_losses     INTEGER,
    last_10_wins    INTEGER,
    last_10_losses  INTEGER,
    streak          TEXT,
    rs              INTEGER,
    ra              INTEGER,
    UNIQUE(season, snapshot_date, team_id)
);

CREATE TABLE IF NOT EXISTS transactions (
    transaction_id  INTEGER PRIMARY KEY,
    player_id       INTEGER,
    player_name     TEXT,
    type_code       TEXT,
    type_desc       TEXT,
    from_team       TEXT,
    to_team         TEXT,
    date            TEXT,
    effective_date  TEXT,
    description     TEXT
);

CREATE INDEX IF NOT EXISTS idx_batting_player  ON batting_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_batting_team    ON batting_stats(team_id, season);
CREATE INDEX IF NOT EXISTS idx_pitching_player ON pitching_stats(player_id);
CREATE INDEX IF NOT EXISTS idx_pitching_team   ON pitching_stats(team_id, season);
CREATE INDEX IF NOT EXISTS idx_games_date      ON games(game_date);
CREATE INDEX IF NOT EXISTS idx_standings_team  ON standings(team_id, season);
"""


@contextmanager
def get_conn() -> Generator[sqlite3.Connection, None, None]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def init_db() -> None:
    """Create all tables if they don't exist."""
    with get_conn() as conn:
        conn.executescript(DDL)
    log.info("Database initialized: %s", DB_PATH)


def upsert(conn: sqlite3.Connection, table: str, row: dict, conflict_cols: list[str]) -> None:
    """INSERT OR REPLACE using conflict columns for deduplication."""
    cols = list(row.keys())
    placeholders = ", ".join("?" * len(cols))
    col_names = ", ".join(cols)
    sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
    conn.execute(sql, list(row.values()))


def bulk_upsert(table: str, rows: list[dict]) -> int:
    """Upsert a list of dicts into table. Returns count inserted."""
    if not rows:
        return 0
    with get_conn() as conn:
        cols = list(rows[0].keys())
        placeholders = ", ".join("?" * len(cols))
        col_names = ", ".join(cols)
        sql = f"INSERT OR REPLACE INTO {table} ({col_names}) VALUES ({placeholders})"
        conn.executemany(sql, [list(r.values()) for r in rows])
    log.debug("Upserted %d rows into %s", len(rows), table)
    return len(rows)
