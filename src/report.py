"""
Generates a natural-language Markdown analytics report from computed DataFrames.
All prose is data-driven — no hardcoded narratives.
"""

from datetime import datetime
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

from config import REPORTS_DIR, TEAM_NAME, SEASON
from src.models import PipelineResult
from utils import get_logger

log = get_logger(__name__)


def _pct(val: float | None) -> str:
    return f"{val:.1%}" if val is not None else "N/A"


def _fmt(val, decimals: int = 3) -> str:
    if val is None or (isinstance(val, float) and np.isnan(val)):
        return "N/A"
    if isinstance(val, float):
        return f"{val:.{decimals}f}"
    return str(val)


def _top(df: pd.DataFrame, col: str, name_col: str = "player_name",
         n: int = 3, ascending: bool = False) -> list[tuple[str, Any]]:
    """Return top-n (name, value) pairs from a DataFrame column."""
    sub = df.dropna(subset=[col]).sort_values(col, ascending=ascending).head(n)
    return [(row[name_col], row[col]) for _, row in sub.iterrows()]


def build_executive_summary(result: PipelineResult) -> str:
    ts = result.team_summary
    if ts.empty:
        return "_No team summary data available._\n"

    row = ts.iloc[0]
    wins = int(row.get("wins", 0))
    losses = int(row.get("losses", 0))
    gp = int(row.get("games_played", 0))
    win_pct = row.get("win_pct", 0)
    pyth = row.get("pythagorean_win_pct")
    rd = row.get("run_differential", 0)
    rs = row.get("runs_scored")
    ra = row.get("runs_allowed")

    # Narrative assessment
    if win_pct >= 0.570:
        pace = "an elite pace"
    elif win_pct >= 0.530:
        pace = "a playoff-caliber pace"
    elif win_pct >= 0.490:
        pace = "a near-.500 pace"
    elif win_pct >= 0.450:
        pace = "a below-average pace"
    else:
        pace = "a rebuilding pace"

    rd_desc = "outscoring" if rd >= 0 else "being outscored by"
    rd_abs = abs(int(rd)) if rd else 0

    lines = [
        f"**{TEAM_NAME}** finished the {SEASON} season with a **{wins}-{losses}** record "
        f"({_pct(win_pct)}) in {gp} games, putting them on {pace}.",
        "",
        f"The team scored **{int(rs) if rs else 'N/A'}** runs and allowed **{int(ra) if ra else 'N/A'}**, "
        f"{rd_desc} opponents by **{rd_abs}** runs on the season.",
    ]
    if pyth:
        diff = float(win_pct) - float(pyth)
        luck_str = (
            f"Their Pythagorean win expectancy of **{_pct(pyth)}** suggests they slightly "
            f"**{'outperformed' if diff > 0.01 else 'underperformed' if diff < -0.01 else 'matched'}** "
            f"their run-differential expectation."
        )
        lines.append(luck_str)

    return "\n".join(lines) + "\n"


def build_offense_section(result: PipelineResult) -> str:
    ts  = result.team_summary
    bat = result.batting
    if bat.empty:
        return "_No batting data available._\n"

    row = ts.iloc[0] if not ts.empty else {}
    ops  = row.get("team_ops")
    avg  = row.get("team_avg")
    obp  = row.get("team_obp")
    slg  = row.get("team_slg")
    hr   = row.get("team_hr")
    sb   = row.get("team_sb")

    qual = bat[bat["pa"].fillna(0) >= 50]

    def top3(col: str, asc: bool = False) -> str:
        leaders = _top(qual, col, ascending=asc) if not qual.empty else []
        if not leaders:
            return "N/A"
        return ", ".join(f"{n} ({_fmt(v)})" for n, v in leaders)

    lines = [
        f"- **Team OPS:** {_fmt(ops)}  |  **AVG:** {_fmt(avg)}  |  **OBP:** {_fmt(obp)}  |  **SLG:** {_fmt(slg)}",
        f"- **Team HR:** {int(hr) if hr else 'N/A'}  |  **SB:** {int(sb) if sb else 'N/A'}",
        "",
        f"**OPS leaders (min 50 PA):** {top3('ops')}",
        f"**AVG leaders:** {top3('avg')}",
        f"**HR leaders:** {top3('hr')}",
        f"**RBI leaders:** {top3('rbi')}",
        f"**Walk rate leaders:** {top3('bb_rate')}",
        f"**Strikeout rate (lowest):** {top3('k_rate', asc=True)}",
    ]
    return "\n".join(lines) + "\n"


def build_pitching_section(result: PipelineResult) -> str:
    ts  = result.team_summary
    pit = result.pitching
    if pit.empty:
        return "_No pitching data available._\n"

    row = ts.iloc[0] if not ts.empty else {}
    era  = row.get("team_era")
    whip = row.get("team_whip")
    ks   = row.get("team_strikeouts")

    qual = pit[pit["ip"].fillna(0) >= 20]

    def top3(col: str, asc: bool = True) -> str:
        leaders = _top(qual, col, ascending=asc) if not qual.empty else []
        if not leaders:
            return "N/A"
        return ", ".join(f"{n} ({_fmt(v)})" for n, v in leaders)

    # Saves leaders (no IP min)
    saves_leaders = _top(pit, "saves", ascending=False)
    saves_str = ", ".join(f"{n} ({int(v)})" for n, v in saves_leaders) or "N/A"

    lines = [
        f"- **Team ERA:** {_fmt(era, 2)}  |  **WHIP:** {_fmt(whip, 2)}  |  **Team K:** {int(ks) if ks else 'N/A'}",
        "",
        f"**ERA leaders (min 20 IP):** {top3('era')}",
        f"**WHIP leaders:** {top3('whip')}",
        f"**FIP leaders:** {top3('fip')}",
        f"**K/9 leaders:** {top3('k9', asc=False)}",
        f"**K/BB leaders:** {top3('k_bb', asc=False)}",
        f"**Saves leaders:** {saves_str}",
    ]
    return "\n".join(lines) + "\n"


def build_trends_section(result: PipelineResult) -> str:
    rolling = result.rolling
    monthly = result.monthly
    if rolling.empty:
        return "_No game-log data available._\n"

    # Best and worst 10-game stretches
    col = "win_pct_10g"
    lines: list[str] = []
    if col in rolling.columns:
        best_idx  = rolling[col].idxmax()
        worst_idx = rolling[col].idxmin()
        best_g    = int(rolling.loc[best_idx, "game_num"])
        worst_g   = int(rolling.loc[worst_idx, "game_num"])
        best_val  = rolling.loc[best_idx, col]
        worst_val = rolling.loc[worst_idx, col]
        lines += [
            f"- **Best 10-game stretch:** {_pct(best_val)} (ending game {best_g})",
            f"- **Worst 10-game stretch:** {_pct(worst_val)} (ending game {worst_g})",
        ]

    # Monthly narrative
    if not monthly.empty:
        best_month  = monthly.loc[monthly["win_pct"].idxmax(), "month_name"]
        worst_month = monthly.loc[monthly["win_pct"].idxmin(), "month_name"]
        lines += [
            f"- **Best month:** {best_month} ({_pct(monthly['win_pct'].max())})",
            f"- **Worst month:** {worst_month} ({_pct(monthly['win_pct'].min())})",
        ]

    # Home/away
    ha = result.home_away_splits
    if not ha.empty:
        for _, r in ha.iterrows():
            role = r["home_away"].capitalize()
            lines.append(
                f"- **{role} record:** {int(r['wins'])}-{int(r['losses'])} ({_pct(r['win_pct'])})"
            )

    return "\n".join(lines) + "\n"


def build_weaknesses_section(result: PipelineResult) -> str:
    """Highlight statistical red flags automatically."""
    items: list[str] = []
    ts  = result.team_summary
    bat = result.batting
    pit = result.pitching

    if not ts.empty:
        row = ts.iloc[0]
        if row.get("team_era", 0) and row["team_era"] > 4.5:
            items.append(f"Team ERA of **{_fmt(row['team_era'], 2)}** ranks among the worst in the league tier.")
        if row.get("team_ops", 0) and row["team_ops"] < 0.680:
            items.append(f"Team OPS of **{_fmt(row['team_ops'])}** indicates an anemic offense.")
        if row.get("run_differential", 0) and row["run_differential"] < -30:
            items.append(f"Run differential of **{int(row['run_differential'])}** shows consistent losing margin.")
        if row.get("win_pct", 0) and row["pythagorean_win_pct"] and \
                row["win_pct"] > row["pythagorean_win_pct"] + 0.03:
            items.append("Win% significantly exceeds Pythagorean expectation — run differential suggests record may regress.")

    if not bat.empty:
        qual = bat[bat["pa"].fillna(0) >= 50]
        if not qual.empty:
            high_k = qual[qual["k_rate"] > 0.30]
            if len(high_k) > 3:
                items.append(f"**{len(high_k)} qualified hitters** striking out at >30% rate — contact quality concern.")
            low_obp = qual[qual["obp"] < 0.300]
            if len(low_obp) > 3:
                items.append(f"**{len(low_obp)} qualified hitters** posting OBP below .300 — on-base issues limit offense.")

    if not pit.empty:
        qual = pit[pit["ip"].fillna(0) >= 20]
        if not qual.empty:
            high_bb9 = qual[qual["bb9"] > 4.5]
            if len(high_bb9) >= 2:
                items.append(f"**{len(high_bb9)} pitchers** with BB/9 > 4.5 — command is a systemic weakness.")

    if not items:
        items.append("No major statistical red flags detected. Solid across-the-board performance.")

    return "\n".join(f"- {item}" for item in items) + "\n"


def generate_report(result: PipelineResult) -> Path:
    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    sections = {
        "Executive Summary": build_executive_summary(result),
        "Offensive Performance": build_offense_section(result),
        "Pitching Performance": build_pitching_section(result),
        "Season Trends": build_trends_section(result),
        "Key Weaknesses": build_weaknesses_section(result),
    }

    # Key takeaways: best bat + best arm
    takeaways: list[str] = []
    if not result.batting.empty:
        qual = result.batting[result.batting["pa"].fillna(0) >= 50]
        if not qual.empty:
            top_bat = qual.nlargest(1, "ops").iloc[0]
            takeaways.append(
                f"**Best Hitter:** {top_bat['player_name']} — "
                f".{str(round(float(top_bat['avg']),3))[2:]} AVG / "
                f"{_fmt(top_bat['ops'])} OPS"
            )
    if not result.pitching.empty:
        qual = result.pitching[result.pitching["ip"].fillna(0) >= 20]
        if not qual.empty:
            top_arm = qual.nsmallest(1, "era").iloc[0]
            takeaways.append(
                f"**Best Pitcher:** {top_arm['player_name']} — "
                f"{_fmt(top_arm['era'], 2)} ERA / {_fmt(top_arm['whip'], 2)} WHIP"
            )

    lines = [
        f"# {TEAM_NAME} {SEASON} Analytics Report",
        f"*Generated: {now}*",
        "",
        "---",
        "",
    ]
    for heading, body in sections.items():
        lines += [f"## {heading}", "", body, ""]

    if takeaways:
        lines += ["## Key Takeaways", ""]
        lines += [f"- {t}" for t in takeaways]
        lines.append("")

    lines += [
        "---",
        f"*Data sourced from the MLB Stats API via MLB-StatsAPI Python package. "
        f"Report auto-generated by the Reading Analytics Pipeline.*",
    ]

    path = REPORTS_DIR / f"season_report_{SEASON}.md"
    path.write_text("\n".join(lines), encoding="utf-8")
    log.info("Season report written → %s", path)
    return path
