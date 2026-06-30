"""
Publication-quality charts via matplotlib (static PNG) and Plotly (interactive HTML).
All outputs land in dashboard/.
"""

from pathlib import Path
from typing import Any

import matplotlib
matplotlib.use("Agg")   # headless — no display required
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import numpy as np
import pandas as pd

from config import DASHBOARD_DIR, TEAM_NAME, SEASON
from utils import get_logger

log = get_logger(__name__)

# Brand palette
COLORS = {
    "primary":   "#8B0000",   # Reading dark red
    "secondary": "#C41E3A",
    "accent":    "#FFD700",
    "neutral":   "#4A4A4A",
    "light":     "#F5F5F5",
    "win":       "#2ECC71",
    "loss":      "#E74C3C",
    "grid":      "#E0E0E0",
}

FIGSIZE_WIDE  = (14, 6)
FIGSIZE_SQUARE= (10, 8)
DPI = 150


def _save(fig: plt.Figure, name: str) -> Path:
    path = DASHBOARD_DIR / f"{name}.png"
    fig.savefig(path, dpi=DPI, bbox_inches="tight", facecolor=COLORS["light"])
    plt.close(fig)
    log.info("Chart saved → %s", path.name)
    return path


def _style_ax(ax: plt.Axes, title: str, xlabel: str = "", ylabel: str = "") -> None:
    ax.set_title(title, fontsize=14, fontweight="bold", color=COLORS["neutral"], pad=12)
    ax.set_xlabel(xlabel, fontsize=11, color=COLORS["neutral"])
    ax.set_ylabel(ylabel, fontsize=11, color=COLORS["neutral"])
    ax.tick_params(colors=COLORS["neutral"], labelsize=9)
    ax.spines[["top", "right"]].set_visible(False)
    ax.set_facecolor(COLORS["light"])
    ax.yaxis.grid(True, color=COLORS["grid"], linewidth=0.7, linestyle="--")
    ax.set_axisbelow(True)


# ── Win/Loss Timeline ─────────────────────────────────────────────────────────

def plot_win_loss_timeline(games: pd.DataFrame) -> Path:
    df = games.dropna(subset=["win"]).copy()
    df["game_date"] = pd.to_datetime(df["game_date"])
    df = df.sort_values("game_date").reset_index(drop=True)

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    colors = [COLORS["win"] if w else COLORS["loss"] for w in df["win"]]
    ax.bar(df.index, df["run_differential"], color=colors, width=0.8, alpha=0.85)
    ax.axhline(0, color=COLORS["neutral"], linewidth=1.0)

    _style_ax(ax, f"{TEAM_NAME} {SEASON} — Game-by-Game Run Differential",
              "Game #", "Run Differential")

    # Rolling win % overlay (right axis)
    ax2 = ax.twinx()
    rolling_wp = df["win"].rolling(10, min_periods=1).mean()
    ax2.plot(df.index, rolling_wp, color=COLORS["accent"], linewidth=2,
             label="10-game win%", zorder=5)
    ax2.set_ylabel("10-game Win %", fontsize=10, color=COLORS["accent"])
    ax2.tick_params(axis="y", colors=COLORS["accent"])
    ax2.set_ylim(0, 1)
    ax2.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    ax2.spines[["top"]].set_visible(False)

    from matplotlib.patches import Patch
    legend = [Patch(color=COLORS["win"], label="Win"),
              Patch(color=COLORS["loss"], label="Loss")]
    ax.legend(handles=legend, loc="upper left", fontsize=9)
    ax2.legend(loc="upper right", fontsize=9)

    fig.suptitle(f"Season: {SEASON}", fontsize=10, color=COLORS["neutral"], y=0.02)
    return _save(fig, "win_loss_timeline")


# ── Cumulative Run Differential ───────────────────────────────────────────────

def plot_run_differential(rolling: pd.DataFrame) -> Path:
    df = rolling.dropna(subset=["cum_run_diff"]).copy()
    df["game_date"] = pd.to_datetime(df["game_date"])

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    pos_mask = df["cum_run_diff"] >= 0
    ax.fill_between(df["game_num"], df["cum_run_diff"], 0,
                    where=pos_mask,  alpha=0.4, color=COLORS["win"], label="Positive")
    ax.fill_between(df["game_num"], df["cum_run_diff"], 0,
                    where=~pos_mask, alpha=0.4, color=COLORS["loss"], label="Negative")
    ax.plot(df["game_num"], df["cum_run_diff"], color=COLORS["primary"], linewidth=2)
    ax.axhline(0, color=COLORS["neutral"], linewidth=1.0)

    _style_ax(ax, f"{TEAM_NAME} {SEASON} — Cumulative Run Differential",
              "Game #", "Cumulative Run Diff")
    ax.legend(fontsize=9)
    return _save(fig, "cumulative_run_diff")


# ── Rolling Win % ─────────────────────────────────────────────────────────────

def plot_rolling_win_pct(rolling: pd.DataFrame) -> Path:
    df = rolling.copy()

    fig, ax = plt.subplots(figsize=FIGSIZE_WIDE)
    palette = [COLORS["primary"], COLORS["secondary"], COLORS["accent"]]
    for i, w in enumerate([5, 10, 20]):
        col = f"win_pct_{w}g"
        if col in df.columns:
            ax.plot(df["game_num"], df[col], color=palette[i], linewidth=2,
                    label=f"{w}-game win%")

    ax.axhline(0.5, color=COLORS["neutral"], linewidth=1, linestyle="--", label=".500 pace")
    ax.yaxis.set_major_formatter(mticker.PercentFormatter(xmax=1, decimals=0))
    _style_ax(ax, f"{TEAM_NAME} {SEASON} — Rolling Win Percentage",
              "Game #", "Win %")
    ax.set_ylim(0, 1)
    ax.legend(fontsize=9)
    return _save(fig, "rolling_win_pct")


# ── Batting Leaders ───────────────────────────────────────────────────────────

def _horizontal_bar(df: pd.DataFrame, col: str, label_col: str,
                    title: str, xlabel: str, fname: str,
                    color: str | None = None) -> Path:
    df = df.dropna(subset=[col]).head(10).sort_values(col)
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df[label_col], df[col],
                   color=color or COLORS["primary"], alpha=0.85, height=0.65)
    for bar, val in zip(bars, df[col]):
        ax.text(bar.get_width() + bar.get_width() * 0.01, bar.get_y() + bar.get_height() / 2,
                f"{val:.3f}" if isinstance(val, float) else str(val),
                va="center", ha="left", fontsize=9, color=COLORS["neutral"])
    _style_ax(ax, title, xlabel)
    ax.xaxis.grid(True, color=COLORS["grid"], linewidth=0.7)
    ax.yaxis.grid(False)
    plt.tight_layout()
    return _save(fig, fname)


def plot_ops_leaders(batting: pd.DataFrame) -> Path:
    df = batting[batting["pa"].fillna(0) >= 50].nlargest(10, "ops")
    return _horizontal_bar(df, "ops", "player_name",
                           f"{TEAM_NAME} {SEASON} — OPS Leaders (min 50 PA)",
                           "OPS", "ops_leaders", COLORS["primary"])


def plot_avg_leaders(batting: pd.DataFrame) -> Path:
    df = batting[batting["pa"].fillna(0) >= 50].nlargest(10, "avg")
    return _horizontal_bar(df, "avg", "player_name",
                           f"{TEAM_NAME} {SEASON} — Batting Average Leaders",
                           "AVG", "avg_leaders", COLORS["secondary"])


def plot_hr_leaders(batting: pd.DataFrame) -> Path:
    df = batting.nlargest(10, "hr")
    fig, ax = plt.subplots(figsize=(10, 6))
    bars = ax.barh(df["player_name"], df["hr"], color=COLORS["primary"], alpha=0.85, height=0.65)
    for bar, val in zip(bars, df["hr"]):
        ax.text(bar.get_width() + 0.1, bar.get_y() + bar.get_height() / 2,
                str(int(val)), va="center", ha="left", fontsize=10, fontweight="bold")
    _style_ax(ax, f"{TEAM_NAME} {SEASON} — Home Run Leaders", "Home Runs")
    ax.xaxis.grid(True, color=COLORS["grid"])
    plt.tight_layout()
    return _save(fig, "hr_leaders")


def plot_rbi_leaders(batting: pd.DataFrame) -> Path:
    df = batting.nlargest(10, "rbi")
    return _horizontal_bar(df, "rbi", "player_name",
                           f"{TEAM_NAME} {SEASON} — RBI Leaders",
                           "RBI", "rbi_leaders", COLORS["secondary"])


def plot_strikeout_leaders(batting: pd.DataFrame) -> Path:
    """Top K leaders among batters (most strikeouts)."""
    df = batting.nlargest(10, "so")
    return _horizontal_bar(df, "so", "player_name",
                           f"{TEAM_NAME} {SEASON} — Strikeout Leaders (Batters)",
                           "Strikeouts", "batter_k_leaders", COLORS["neutral"])


# ── Pitching Charts ───────────────────────────────────────────────────────────

def plot_era_leaders(pitching: pd.DataFrame) -> Path:
    df = pitching[pitching["ip"].fillna(0) >= 20].nsmallest(10, "era")
    return _horizontal_bar(df, "era", "player_name",
                           f"{TEAM_NAME} {SEASON} — ERA Leaders (min 20 IP)",
                           "ERA", "era_leaders", COLORS["secondary"])


def plot_whip_leaders(pitching: pd.DataFrame) -> Path:
    df = pitching[pitching["ip"].fillna(0) >= 20].nsmallest(10, "whip")
    return _horizontal_bar(df, "whip", "player_name",
                           f"{TEAM_NAME} {SEASON} — WHIP Leaders (min 20 IP)",
                           "WHIP", "whip_leaders", COLORS["primary"])


def plot_k9_leaders(pitching: pd.DataFrame) -> Path:
    df = pitching[pitching["ip"].fillna(0) >= 20].nlargest(10, "k9")
    return _horizontal_bar(df, "k9", "player_name",
                           f"{TEAM_NAME} {SEASON} — K/9 Leaders (min 20 IP)",
                           "K/9", "k9_leaders", COLORS["accent"])


# ── Scatter: OPS vs PA ────────────────────────────────────────────────────────

def plot_ops_scatter(batting: pd.DataFrame) -> Path:
    df = batting.dropna(subset=["ops", "pa"]).copy()
    df = df[df["pa"] > 10]

    fig, ax = plt.subplots(figsize=FIGSIZE_SQUARE)
    sc = ax.scatter(df["pa"], df["ops"],
                    c=df["hr"].fillna(0), cmap="YlOrRd",
                    s=60, alpha=0.75, edgecolors="white", linewidth=0.5, zorder=3)
    plt.colorbar(sc, ax=ax, label="Home Runs")

    # Label top performers
    top = df.nlargest(5, "ops")
    for _, row in top.iterrows():
        ax.annotate(row["player_name"].split()[-1], (row["pa"], row["ops"]),
                    fontsize=8, xytext=(4, 4), textcoords="offset points",
                    color=COLORS["neutral"])

    _style_ax(ax, f"{TEAM_NAME} {SEASON} — OPS vs Plate Appearances",
              "Plate Appearances", "OPS")
    return _save(fig, "ops_scatter")


# ── Starter vs Reliever ERA ───────────────────────────────────────────────────

def plot_starter_vs_reliever(pitching: pd.DataFrame) -> Path:
    df = pitching.dropna(subset=["era"]).copy()
    df["role"] = df["games_started"].apply(lambda x: "Starter" if x >= 3 else "Reliever")

    fig, ax = plt.subplots(figsize=(8, 5))
    roles = ["Starter", "Reliever"]
    eras  = [df[df["role"] == r]["era"].tolist() for r in roles]
    bp = ax.boxplot(eras, labels=roles, patch_artist=True,
                    medianprops={"color": COLORS["accent"], "linewidth": 2})
    for patch, color in zip(bp["boxes"], [COLORS["primary"], COLORS["secondary"]]):
        patch.set_facecolor(color)
        patch.set_alpha(0.7)

    _style_ax(ax, f"{TEAM_NAME} {SEASON} — ERA Distribution: Starters vs Relievers",
              "Role", "ERA")
    return _save(fig, "era_starter_vs_reliever")


# ── Monthly W-L ───────────────────────────────────────────────────────────────

def plot_monthly_record(monthly: pd.DataFrame) -> Path:
    if monthly.empty:
        return DASHBOARD_DIR / "monthly_record.png"

    fig, ax = plt.subplots(figsize=(10, 5))
    x = np.arange(len(monthly))
    width = 0.35
    ax.bar(x - width/2, monthly["wins"],   width, label="Wins",   color=COLORS["win"],  alpha=0.85)
    ax.bar(x + width/2, monthly["losses"], width, label="Losses", color=COLORS["loss"], alpha=0.85)

    ax.set_xticks(x)
    ax.set_xticklabels(monthly["month_name"], fontsize=10)
    _style_ax(ax, f"{TEAM_NAME} {SEASON} — Monthly Win-Loss Record", "Month", "Games")
    ax.legend(fontsize=9)
    return _save(fig, "monthly_record")


# ── Run all charts ────────────────────────────────────────────────────────────

def generate_all_charts(
    batting: pd.DataFrame,
    pitching: pd.DataFrame,
    games: pd.DataFrame,
    rolling: pd.DataFrame,
    monthly: pd.DataFrame,
) -> list[Path]:
    charts: list[Path] = []
    safe_calls = [
        (plot_win_loss_timeline,      [games],    "win-loss timeline"),
        (plot_run_differential,       [rolling],  "cumulative run diff"),
        (plot_rolling_win_pct,        [rolling],  "rolling win %"),
        (plot_ops_leaders,            [batting],  "OPS leaders"),
        (plot_avg_leaders,            [batting],  "AVG leaders"),
        (plot_hr_leaders,             [batting],  "HR leaders"),
        (plot_rbi_leaders,            [batting],  "RBI leaders"),
        (plot_strikeout_leaders,      [batting],  "batter K leaders"),
        (plot_era_leaders,            [pitching], "ERA leaders"),
        (plot_whip_leaders,           [pitching], "WHIP leaders"),
        (plot_k9_leaders,             [pitching], "K/9 leaders"),
        (plot_ops_scatter,            [batting],  "OPS scatter"),
        (plot_starter_vs_reliever,    [pitching], "starter/reliever ERA"),
        (plot_monthly_record,         [monthly],  "monthly record"),
    ]
    for fn, args, label in safe_calls:
        try:
            p = fn(*args)
            charts.append(p)
        except Exception as exc:
            log.warning("Chart '%s' failed: %s", label, exc)
    log.info("Generated %d charts", len(charts))
    return charts
