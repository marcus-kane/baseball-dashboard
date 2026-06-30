"""
Dataclass models for type-safe data interchange between pipeline stages.
Not ORM — just named containers so function signatures stay readable.
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class PipelineResult:
    """Holds all DataFrames produced by one full pipeline run."""
    team_summary:  pd.DataFrame = field(default_factory=pd.DataFrame)
    batting:       pd.DataFrame = field(default_factory=pd.DataFrame)
    pitching:      pd.DataFrame = field(default_factory=pd.DataFrame)
    games:         pd.DataFrame = field(default_factory=pd.DataFrame)
    rolling:       pd.DataFrame = field(default_factory=pd.DataFrame)
    standings:     pd.DataFrame = field(default_factory=pd.DataFrame)
    monthly:       pd.DataFrame = field(default_factory=pd.DataFrame)
    opponent_splits: pd.DataFrame = field(default_factory=pd.DataFrame)
    home_away_splits: pd.DataFrame = field(default_factory=pd.DataFrame)
    batting_boards: dict[str, pd.DataFrame] = field(default_factory=dict)
    pitching_boards: dict[str, pd.DataFrame] = field(default_factory=dict)
    charts: list[str] = field(default_factory=list)
    validation_errors: int = 0
    validation_warnings: int = 0


@dataclass
class PlayerBio:
    player_id:    int
    player_name:  str
    position:     str
    bats:         Optional[str] = None
    throws_hand:  Optional[str] = None
    birth_date:   Optional[str] = None
    height:       Optional[str] = None
    weight:       Optional[int] = None
