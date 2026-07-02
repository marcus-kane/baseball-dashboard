"""
Shared sidebar component used by every page.
Provides: season picker, level/team filter, on-demand refresh button.
"""
from __future__ import annotations

import subprocess
import sys
import time
from pathlib import Path

import streamlit as st

import web_data as db
from config import ORG_TEAMS


def render(page_title: str = "") -> tuple[int, int | None]:
    """
    Render the standard sidebar. Returns (selected_season, selected_team_id | None).
    selected_team_id is None when "All Levels" is chosen.
    """
    with st.sidebar:
        st.markdown("## Philadelphia Phillies")
        if page_title:
            st.markdown(f"**{page_title}**")
        st.divider()

        # Season selector
        seasons = db.seasons_available()
        if not seasons:
            seasons = [2026]
        season = st.selectbox("Season", seasons, index=0, key="global_season")

        # Level / team filter
        level_options = {"All Levels": None}
        for t in ORG_TEAMS:
            level_options[f"{t['level']} — {t['team_name']}"] = t["team_id"]
        chosen_label = st.selectbox("Level", list(level_options.keys()), key="global_level")
        team_id = level_options[chosen_label]

        st.divider()

        # Refresh button
        st.markdown("**Data Refresh**")
        st.caption("Pulls latest stats from MLB Stats API for all 3 levels.")

        season_to_refresh = st.selectbox(
            "Refresh season", seasons, index=0, key="refresh_season"
        )

        if st.button("Refresh Now", type="primary", use_container_width=True):
            _run_refresh(season_to_refresh)

        st.divider()
        st.caption("Data: MLB Stats API (free)")
        st.caption("Edit `data/prospects.csv` to update rankings.")

    return int(season), team_id


def _run_refresh(season: int) -> None:
    """Run main.py in a subprocess and stream output into st.status."""
    python = sys.executable
    script = str(Path(__file__).parent / "main.py")

    with st.status(f"Refreshing {season} data...", expanded=True) as status:
        try:
            proc = subprocess.Popen(
                [python, script, "--season", str(season)],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
            lines = []
            for line in proc.stdout:
                line = line.rstrip()
                if line:
                    st.write(line)
                    lines.append(line)
            proc.wait()

            if proc.returncode == 0:
                st.cache_data.clear()
                status.update(label="Refresh complete — reloading data.", state="complete")
                time.sleep(1)
                st.rerun()
            else:
                status.update(label="Refresh failed — check logs.", state="error")
        except Exception as exc:
            status.update(label=f"Error: {exc}", state="error")
