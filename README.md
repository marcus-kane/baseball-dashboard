# Reading Fightin Phils — Minor League Baseball Analytics Dashboard

A production-quality analytics pipeline and dashboard for Double-A baseball, built as a portfolio project demonstrating the full data engineering stack a Baseball Operations or Research team uses day-to-day.

---

## Project Overview

This project ingests data from the **MLB Stats API**, stores it in a normalized **SQLite** database, computes advanced analytics, generates **14 publication-quality charts**, exports **Power BI / Tableau-ready CSVs**, and produces a natural-language **Markdown season report** — all triggered by a single command.

Built for: **Reading Fightin Phils (AA-East), 2025**

Changing two variables in `config.py` (`TEAM_ID` and `SEASON`) lets you run the same pipeline for any MiLB team and season.

---

## Screenshots

| Win/Loss Timeline | OPS Leaders |
|---|---|
| ![Win Loss](dashboard/win_loss_timeline.png) | ![OPS](dashboard/ops_leaders.png) |

| Rolling Win % | ERA Leaders |
|---|---|
| ![Rolling](dashboard/rolling_win_pct.png) | ![ERA](dashboard/era_leaders.png) |

---

## Installation

```bash
git clone <repo-url>
cd baseball-dashboard
py -m pip install -r requirements.txt
```

No API key required. The MLB Stats API is free and unauthenticated.

---

## Usage

```bash
py main.py
```

This single command:

1. Initializes the SQLite database
2. Downloads fresh team / roster data
3. Downloads full batting and pitching season stats
4. Downloads schedule + boxscore for every game
5. Downloads standings and transaction history
6. Validates all data and writes a validation report
7. Computes team summary, leaderboards, and rolling trends
8. Generates 14 charts (PNG)
9. Exports 6 dashboard-ready CSVs
10. Generates a natural-language season report

**Runtime:** ~4-6 minutes (most time is API rate-limiting on 149 boxscores)

---

## Project Structure

```
baseball-dashboard/
├── main.py                  # Orchestrator — run this
├── config.py                # All settings in one place
├── database.py              # SQLite schema + upsert helpers
├── utils.py                 # Logging, type coercions, shared helpers
├── requirements.txt
├── .env.example
│
├── src/
│   ├── api.py               # All MLB Stats API calls
│   ├── etl.py               # Extract/flatten/load for each table
│   ├── clean.py             # Data validation + report
│   ├── analytics.py         # Team metrics, leaderboards, splits
│   ├── visualizations.py    # 14 matplotlib charts
│   ├── report.py            # Natural-language season report
│   └── models.py            # PipelineResult dataclass
│
├── data/
│   ├── raw/                 # Raw JSON from API (for debugging)
│   ├── processed/           # Clean CSVs per analytics module
│   └── database/
│       └── baseball.db      # SQLite — all normalized tables
│
├── dashboard/               # Power BI / Tableau ready
│   ├── batting.csv
│   ├── pitching.csv
│   ├── games.csv
│   ├── rolling_metrics.csv
│   ├── standings.csv
│   ├── team_summary.csv
│   └── *.png                # 14 publication-quality charts
│
├── reports/
│   ├── season_report_2025.md
│   └── validation_report.md
│
└── logs/
    └── pipeline.log
```

---

## Database Schema

Six normalized SQLite tables:

| Table | Description |
|-------|-------------|
| `teams` | Team metadata per season |
| `roster` | Player bio + handedness |
| `batting_stats` | 35-column hitting stats per player/season |
| `pitching_stats` | 40-column pitching stats per player/season |
| `games` | Every regular-season game with boxscore data |
| `standings` | Division standings snapshot |
| `transactions` | Roster moves (assignments, IL, trades) |

All tables support `INSERT OR REPLACE` so the pipeline is fully **idempotent** — safe to re-run anytime.

---

## Analytics Computed

### Team Metrics
- Win %, Run Differential, Pythagorean Win %
- Team OPS / AVG / OBP / SLG
- Team ERA / WHIP, total strikeouts

### Batting Leaderboards
OPS, AVG, OBP, SLG, HR, RBI, XBH, Walk Rate, K Rate, ISO, SB, BABIP

### Pitching Leaderboards
ERA, WHIP, FIP, K/9, K/BB, Opp AVG, BB/9, Saves, Holds

### Splits
- Home / Away
- Monthly (April–September)
- By opponent

### Rolling Trends
- 5-game, 10-game, 20-game rolling win %
- Cumulative run differential
- Cumulative win %

---

## Charts Generated

| Chart | File |
|-------|------|
| Win/loss timeline + rolling win% | `win_loss_timeline.png` |
| Cumulative run differential | `cumulative_run_diff.png` |
| Rolling win % (5/10/20 game) | `rolling_win_pct.png` |
| OPS leaders bar | `ops_leaders.png` |
| AVG leaders bar | `avg_leaders.png` |
| HR leaders bar | `hr_leaders.png` |
| RBI leaders bar | `rbi_leaders.png` |
| Batter K leaders | `batter_k_leaders.png` |
| ERA leaders bar | `era_leaders.png` |
| WHIP leaders bar | `whip_leaders.png` |
| K/9 leaders bar | `k9_leaders.png` |
| OPS vs PA scatter (HR color) | `ops_scatter.png` |
| Starter vs Reliever ERA boxplot | `era_starter_vs_reliever.png` |
| Monthly W-L record | `monthly_record.png` |

---

## Switching Teams

Open `config.py` and change:

```python
TEAM_ID:   int = 522     # Reading Fightin Phils
TEAM_NAME: str = "Reading Fightin Phils"
SEASON:    int = 2025
SPORT_ID:  int = 12      # 11=AAA, 12=AA, 13=High-A, 14=Single-A
LEAGUE_ID: int = 113     # Eastern League
```

Use `statsapi.lookup_team("<city>", sportIds="11,12,13,14")` to find any MiLB team's ID.

---

## Data Sources

- **MLB Stats API** (free, no key required): `https://statsapi.mlb.com/api/v1/`
- Python wrapper: [MLB-StatsAPI](https://github.com/toddrob99/MLB-StatsAPI)

Key discovery: the `stats` endpoint requires `playerPool=All` and `sportIds` (plural) to return all roster players, not just qualified leaders.

---

## Key 2025 Findings

- **55-81 record** (.404) — rebuilding season
- **Felix Reyes** led the team with .335 AVG / .937 OPS / 15 HR / 65 RBI
- **Tristan Garnett** posted the best ERA at 2.16 out of the bullpen
- **Griff McGarry** led starters with 3.25 ERA and 12.88 K/9
- Team had 173 stolen bases — strong emphasis on speed
- **Command** was the primary pitching weakness: 7 pitchers with BB/9 > 4.5

---

## Future Improvements

- [ ] Game-level pitch tracking (if Statcast available for AA)
- [ ] Left/right platoon splits per batter
- [ ] Day/night splits
- [ ] Prospect ranking integration
- [ ] Attendance trend analysis
- [ ] Multi-season longitudinal comparisons
- [ ] Player development tracking (AA → AAA → MLB promotions)
- [ ] Plotly interactive HTML dashboard
- [ ] Automated nightly refresh via Task Scheduler / cron

---

## Tech Stack

| Layer | Tool |
|-------|------|
| API Client | MLB-StatsAPI |
| Database | SQLite + contextmanager |
| Data Processing | pandas, numpy |
| Visualizations | matplotlib |
| Logging | Python logging |
| Type Safety | dataclasses, type hints |
| CLI Output | Rich (disabled on legacy terminals) |

---

*Portfolio project demonstrating end-to-end sports analytics engineering. All data from the official MLB Stats API.*
