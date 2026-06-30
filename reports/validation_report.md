# Data Validation Report

**Errors:** 0  |  **Warnings:** 1

| Table | Check | Severity | Count | Detail |
|-------|-------|----------|-------|--------|
| roster | missing player names | INFO | 0 |  |
| roster | duplicate player IDs | INFO | 0 |  |
| batting_stats | AVG out of range [0,1] | INFO | 0 |  |
| batting_stats | OBP out of range [0,1] | INFO | 0 |  |
| batting_stats | negative plate appearances | INFO | 0 |  |
| batting_stats | players with 0 PA (possible load issue) | INFO | 0 |  |
| batting_stats | duplicate (player, team, season) rows | INFO | 0 |  |
| pitching_stats | ERA > 30 (suspect value) | INFO | 0 |  |
| pitching_stats | IP > 300 (impossible for MiLB season) | INFO | 0 |  |
| pitching_stats | negative innings pitched | INFO | 0 |  |
| pitching_stats | duplicate (player, team, season) rows | INFO | 0 |  |
| games | duplicate game PKs | INFO | 0 |  |
| games | games with null team score | WARNING | 2 |  |
| games | games with missing date | INFO | 0 |  |
| games | run differential > 20 (extreme outlier check) | INFO | 0 |  |
| teams | missing team IDs | INFO | 0 |  |