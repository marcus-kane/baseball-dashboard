"""
Central configuration for the baseball analytics pipeline.
Change TEAM_ID and SEASON to analyze any MiLB team.
"""

from pathlib import Path

# ── Team & Season ─────────────────────────────────────────────────────────────
TEAM_ID: int = 522          # Reading Fightin Phils
TEAM_NAME: str = "Reading Fightin Phils"
SEASON: int = 2025
SPORT_ID: int = 12          # 11=AAA, 12=AA, 13=High-A, 14=Single-A
LEAGUE_ID: int = 113        # Eastern League (Double-A Northeast)

# Season date window
SEASON_START: str = f"{SEASON}-04-01"
SEASON_END: str   = f"{SEASON}-09-30"

# ── Paths ──────────────────────────────────────────────────────────────────────
BASE_DIR       = Path(__file__).parent
DATA_DIR       = BASE_DIR / "data"
RAW_DIR        = DATA_DIR / "raw"
PROCESSED_DIR  = DATA_DIR / "processed"
DB_DIR         = DATA_DIR / "database"
DASHBOARD_DIR  = BASE_DIR / "dashboard"
REPORTS_DIR    = BASE_DIR / "reports"
LOGS_DIR       = BASE_DIR / "logs"

DB_PATH = DB_DIR / "baseball.db"

# Ensure dirs exist at import time
for _d in (RAW_DIR, PROCESSED_DIR, DB_DIR, DASHBOARD_DIR, REPORTS_DIR, LOGS_DIR):
    _d.mkdir(parents=True, exist_ok=True)

# ── API ────────────────────────────────────────────────────────────────────────
API_RATE_LIMIT_PAUSE: float = 0.3   # seconds between heavy requests

# ── Analytics ─────────────────────────────────────────────────────────────────
MIN_PA_QUALIFY: int = 50            # min plate appearances for batting leaders
MIN_IP_QUALIFY: float = 20.0        # min innings pitched for pitching leaders
ROLLING_WINDOWS: list[int] = [5, 10, 20]
