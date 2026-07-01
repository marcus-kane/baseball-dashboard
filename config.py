"""
Central configuration for the Phillies org analytics pipeline.
ORG_TEAMS drives which teams get fetched — add/remove levels here.
"""

from pathlib import Path

# ── Active season ──────────────────────────────────────────────────────────────
SEASON: int = 2026
SEASON_START: str = f"{SEASON}-03-20"
SEASON_END: str   = f"{SEASON}-10-15"

# ── Phillies organization — all three active levels ───────────────────────────
ORG_TEAMS: list[dict] = [
    {
        "team_id":   143,
        "team_name": "Philadelphia Phillies",
        "level":     "MLB",
        "sport_id":  1,
        "league_id": 104,   # National League
    },
    {
        "team_id":   1410,
        "team_name": "Lehigh Valley IronPigs",
        "level":     "AAA",
        "sport_id":  11,
        "league_id": 112,   # International League
    },
    {
        "team_id":   522,
        "team_name": "Reading Fightin Phils",
        "level":     "AA",
        "sport_id":  12,
        "league_id": 113,   # Double-A Northeast
    },
]

# Convenience lookups
TEAM_BY_LEVEL: dict[str, dict] = {t["level"]: t for t in ORG_TEAMS}
TEAM_BY_ID:    dict[int, dict] = {t["team_id"]: t for t in ORG_TEAMS}

# Legacy single-team aliases (keeps src/ modules working without changes)
TEAM_ID:   int = 522
TEAM_NAME: str = "Reading Fightin Phils"
SPORT_ID:  int = 12
LEAGUE_ID: int = 113

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR      = Path(__file__).parent
DATA_DIR      = BASE_DIR / "data"
RAW_DIR       = DATA_DIR / "raw"
PROCESSED_DIR = DATA_DIR / "processed"
DB_DIR        = DATA_DIR / "database"
DASHBOARD_DIR = BASE_DIR / "dashboard"
REPORTS_DIR   = BASE_DIR / "reports"
LOGS_DIR      = BASE_DIR / "logs"

DB_PATH = DB_DIR / "baseball.db"

for _d in (RAW_DIR, PROCESSED_DIR, DB_DIR, DASHBOARD_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── API ────────────────────────────────────────────────────────────────────────
API_RATE_LIMIT_PAUSE: float = 0.25

# ── Analytics thresholds ───────────────────────────────────────────────────────
MIN_PA_QUALIFY:  int   = 50
MIN_IP_QUALIFY:  float = 20.0
ROLLING_WINDOWS: list[int] = [5, 10, 20]

# ── Prospects CSV ──────────────────────────────────────────────────────────────
PROSPECTS_CSV = BASE_DIR / "data" / "prospects.csv"
