"""
Data validation and cleaning.
Runs after ETL and writes a human-readable validation report.
"""

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

import pandas as pd

from config import REPORTS_DIR, SEASON, TEAM_ID, MIN_PA_QUALIFY, MIN_IP_QUALIFY
from database import get_conn
from utils import get_logger

log = get_logger(__name__)


@dataclass
class ValidationIssue:
    table: str
    check: str
    severity: str      # 'ERROR' | 'WARNING' | 'INFO'
    count: int
    detail: str = ""


@dataclass
class ValidationReport:
    issues: list[ValidationIssue] = field(default_factory=list)

    def add(self, table: str, check: str, severity: str, count: int, detail: str = "") -> None:
        self.issues.append(ValidationIssue(table, check, severity, count, detail))
        sym = {"ERROR": "✗", "WARNING": "⚠", "INFO": "✓"}.get(severity, "?")
        log.info("[%s] %s — %s: %d %s", severity, sym, check, count, detail)

    @property
    def errors(self) -> int:
        return sum(1 for i in self.issues if i.severity == "ERROR")

    @property
    def warnings(self) -> int:
        return sum(1 for i in self.issues if i.severity == "WARNING")

    def to_markdown(self) -> str:
        lines = ["# Data Validation Report\n"]
        lines.append(f"**Errors:** {self.errors}  |  **Warnings:** {self.warnings}\n")
        lines.append("| Table | Check | Severity | Count | Detail |")
        lines.append("|-------|-------|----------|-------|--------|")
        for i in self.issues:
            lines.append(f"| {i.table} | {i.check} | {i.severity} | {i.count} | {i.detail} |")
        return "\n".join(lines)


def _query(conn: sqlite3.Connection, sql: str) -> pd.DataFrame:
    return pd.read_sql_query(sql, conn)


def validate_all() -> ValidationReport:
    report = ValidationReport()

    with get_conn() as conn:
        # ── Roster ──────────────────────────────────────────────────────────
        df = _query(conn, "SELECT * FROM roster")
        n_missing_name = df["player_name"].isna().sum() + (df["player_name"] == "").sum()
        report.add("roster", "missing player names", "ERROR" if n_missing_name else "INFO",
                   n_missing_name)

        dup_ids = df["player_id"].duplicated().sum()
        report.add("roster", "duplicate player IDs", "ERROR" if dup_ids else "INFO", dup_ids)

        # ── Batting Stats ────────────────────────────────────────────────────
        df = _query(conn, f"SELECT * FROM batting_stats WHERE season={SEASON}")
        if len(df):
            bad_avg = ((df["avg"] < 0) | (df["avg"] > 1)).sum()
            report.add("batting_stats", "AVG out of range [0,1]",
                       "ERROR" if bad_avg else "INFO", int(bad_avg))

            bad_obp = ((df["obp"] < 0) | (df["obp"] > 1)).dropna().sum() if "obp" in df.columns else 0
            report.add("batting_stats", "OBP out of range [0,1]",
                       "ERROR" if bad_obp else "INFO", int(bad_obp))

            neg_pa = (df["pa"].fillna(0) < 0).sum()
            report.add("batting_stats", "negative plate appearances",
                       "ERROR" if neg_pa else "INFO", int(neg_pa))

            zero_pa = (df["pa"].fillna(0) == 0).sum()
            report.add("batting_stats", "players with 0 PA (possible load issue)",
                       "WARNING" if zero_pa > 5 else "INFO", int(zero_pa))

            dup_bat = df.duplicated(subset=["player_id", "team_id", "season"]).sum()
            report.add("batting_stats", "duplicate (player, team, season) rows",
                       "ERROR" if dup_bat else "INFO", int(dup_bat))

        # ── Pitching Stats ────────────────────────────────────────────────────
        df = _query(conn, f"SELECT * FROM pitching_stats WHERE season={SEASON}")
        if len(df):
            bad_era = (df["era"].dropna() > 30).sum()
            report.add("pitching_stats", "ERA > 30 (suspect value)",
                       "WARNING" if bad_era else "INFO", int(bad_era),
                       df.loc[df["era"] > 30, "player_id"].tolist().__str__()[:80] if bad_era else "")

            bad_ip = (df["ip"].dropna() > 300).sum()
            report.add("pitching_stats", "IP > 300 (impossible for MiLB season)",
                       "ERROR" if bad_ip else "INFO", int(bad_ip))

            neg_ip = (df["ip"].fillna(0) < 0).sum()
            report.add("pitching_stats", "negative innings pitched",
                       "ERROR" if neg_ip else "INFO", int(neg_ip))

            dup_pit = df.duplicated(subset=["player_id", "team_id", "season"]).sum()
            report.add("pitching_stats", "duplicate (player, team, season) rows",
                       "ERROR" if dup_pit else "INFO", int(dup_pit))

        # ── Games ─────────────────────────────────────────────────────────────
        df = _query(conn, f"SELECT * FROM games WHERE season={SEASON}")
        if len(df):
            dup_games = df.duplicated(subset=["game_pk"]).sum()
            report.add("games", "duplicate game PKs",
                       "ERROR" if dup_games else "INFO", int(dup_games))

            null_scores = df["team_score"].isna().sum()
            report.add("games", "games with null team score",
                       "WARNING" if null_scores else "INFO", int(null_scores))

            null_dates = (df["game_date"] == "").sum()
            report.add("games", "games with missing date",
                       "ERROR" if null_dates else "INFO", int(null_dates))

            blowouts = (df["run_differential"].abs() > 20).sum()
            report.add("games", "run differential > 20 (extreme outlier check)",
                       "WARNING" if blowouts else "INFO", int(blowouts))

        # ── Teams ─────────────────────────────────────────────────────────────
        df = _query(conn, "SELECT * FROM teams")
        null_tid = df["team_id"].isna().sum()
        report.add("teams", "missing team IDs",
                   "ERROR" if null_tid else "INFO", int(null_tid))

    return report


def export_validation_report(report: ValidationReport) -> Path:
    path = REPORTS_DIR / "validation_report.md"
    path.write_text(report.to_markdown(), encoding="utf-8")
    log.info("Validation report written → %s", path)
    return path
