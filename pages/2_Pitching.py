"""Pitching stats page — sortable table + interactive charts."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

import web_data as db

st.set_page_config(page_title="Pitching · Reading", page_icon="🎯", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("## ⚾ Reading Fightin Phils")
    st.markdown("**2025 · Double-A Northeast**")
    st.divider()
    st.markdown("**Filters**")
    min_ip   = st.slider("Minimum Innings Pitched", 0, 150, 10, step=5)
    role_opt = st.radio("Role", ["All", "Starter", "Reliever"])
    hand_opt = st.radio("Throws", ["All", "R", "L"])

st.title("🎯 Pitching Stats — 2025")
st.caption("All regular-season stats · FIP = (13×HR + 3×(BB+HBP) − 2×K) / IP + 3.10")

df = db.pitching()

# Apply filters
df = df[df["ip"].fillna(0) >= min_ip]
if role_opt != "All":
    df = df[df["role"] == role_opt]
if hand_opt != "All":
    df = df[df["throws_hand"] == hand_opt]

# ── Metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3, c4, c5 = st.columns(5)
c1.metric("Pitchers shown", len(df))

ip_tot = df["ip"].fillna(0).sum()
er_tot = df["earned_runs"].fillna(0).sum()
c2.metric("Group ERA",  f"{(er_tot * 9 / ip_tot):.2f}" if ip_tot else "—")

h_tot  = df["hits"].fillna(0).sum()
bb_tot = df["bb"].fillna(0).sum()
c3.metric("Group WHIP", f"{((h_tot + bb_tot) / ip_tot):.2f}" if ip_tot else "—")

c4.metric("Total K",  int(df["so"].fillna(0).sum()))
c5.metric("Total IP", f"{ip_tot:.1f}")

st.divider()

# ── Stat table ────────────────────────────────────────────────────────────────
st.subheader("Full Pitching Table")
st.caption("Click any column header to sort")

display_cols = {
    "player_name": "Player", "throws_hand": "T", "role": "Role",
    "games": "G", "games_started": "GS", "wins": "W", "losses": "L",
    "saves": "SV", "holds": "HLD", "blown_saves": "BS",
    "ip": "IP", "era": "ERA", "whip": "WHIP", "fip": "FIP",
    "so": "K", "bb": "BB", "hits": "H", "hr": "HR",
    "k9": "K/9", "bb9": "BB/9", "k_bb": "K/BB",
    "opp_avg": "OppAVG", "hbp": "HBP", "wild_pitches": "WP",
    "k_pct": "K%", "bb_pct": "BB%",
}
table = df[list(display_cols.keys())].rename(columns=display_cols)

st.dataframe(
    table.reset_index(drop=True),
    use_container_width=True,
    height=420,
    column_config={
        "IP":      st.column_config.NumberColumn(format="%.1f"),
        "ERA":     st.column_config.NumberColumn(format="%.2f"),
        "WHIP":    st.column_config.NumberColumn(format="%.2f"),
        "FIP":     st.column_config.NumberColumn(format="%.2f"),
        "K/9":     st.column_config.NumberColumn(format="%.2f"),
        "BB/9":    st.column_config.NumberColumn(format="%.2f"),
        "K/BB":    st.column_config.NumberColumn(format="%.2f"),
        "OppAVG":  st.column_config.NumberColumn(format="%.3f"),
        "K%":      st.column_config.NumberColumn(format="%.1%"),
        "BB%":     st.column_config.NumberColumn(format="%.1%"),
    },
    hide_index=True,
)

st.divider()

# ── Charts row 1 ──────────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.subheader("ERA Leaders *(qualified)*")
    qual = df[df["ip"].fillna(0) >= 20].nsmallest(min(12, len(df[df["ip"]>=20])), "era")
    fig = px.bar(
        qual.sort_values("era", ascending=False),
        x="era", y="player_name", orientation="h",
        color="era",
        color_continuous_scale=["#2ECC71", "#F39C12", "#E74C3C"],
        labels={"era": "ERA", "player_name": ""},
        hover_data={"whip": ":.2f", "ip": ":.1f", "so": True, "bb": True},
        text="era",
    )
    fig.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig.update_layout(
        coloraxis_showscale=False,
        height=420,
        margin=dict(t=10, l=140, r=60),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.subheader("K/9 Leaders *(qualified)*")
    qual_k = df[df["ip"].fillna(0) >= 20].nlargest(min(12, len(df[df["ip"]>=20])), "k9")
    fig2 = px.bar(
        qual_k.sort_values("k9"),
        x="k9", y="player_name", orientation="h",
        color="k9",
        color_continuous_scale=["#1a1a5e", "#3333cc", "#8888FF"],
        labels={"k9": "K/9", "player_name": ""},
        hover_data={"era": ":.2f", "ip": ":.1f", "bb9": ":.2f"},
        text="k9",
    )
    fig2.update_traces(texttemplate="%{text:.2f}", textposition="outside")
    fig2.update_layout(
        coloraxis_showscale=False,
        height=420,
        margin=dict(t=10, l=140, r=60),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc", yaxis_title="",
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Scatter: K/9 vs BB/9 ──────────────────────────────────────────────────────
st.subheader("Command Map: K/9 vs BB/9")
st.caption("Top-right = high strikeouts + high walks · Top-left = dominant (high K, low BB)")

scatter_df = df[df["ip"].fillna(0) >= 5].dropna(subset=["k9", "bb9"])
if not scatter_df.empty:
    fig3 = px.scatter(
        scatter_df,
        x="bb9", y="k9",
        color="era",
        color_continuous_scale="RdYlGn_r",
        size=scatter_df["ip"].clip(lower=1),
        size_max=30,
        hover_name="player_name",
        hover_data={"bb9": ":.2f", "k9": ":.2f", "era": ":.2f", "ip": ":.1f", "role": True},
        labels={"bb9": "BB/9 (walks allowed)", "k9": "K/9 (strikeouts)"},
    )
    avg_k9  = scatter_df["k9"].mean()
    avg_bb9 = scatter_df["bb9"].mean()
    fig3.add_vline(x=avg_bb9, line_dash="dash", line_color="#555",
                   annotation_text="Avg BB/9")
    fig3.add_hline(y=avg_k9,  line_dash="dash", line_color="#555",
                   annotation_text="Avg K/9")
    fig3.update_layout(
        height=420,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        coloraxis_colorbar=dict(title="ERA"),
    )
    top5 = scatter_df.nlargest(5, "k9")
    for _, row in top5.iterrows():
        fig3.add_annotation(
            x=row["bb9"], y=row["k9"],
            text=row["player_name"].split()[-1],
            showarrow=False, yshift=12,
            font=dict(size=10, color="#FFD700"),
        )
    st.plotly_chart(fig3, use_container_width=True)

# ── ERA distribution: Starters vs Relievers ───────────────────────────────────
st.subheader("ERA Distribution by Role")
era_df = df.dropna(subset=["era"])
if not era_df.empty:
    fig4 = go.Figure()
    for role, color in [("Starter", "#8B0000"), ("Reliever", "#1a4a8B")]:
        sub = era_df[era_df["role"] == role]["era"]
        if not sub.empty:
            fig4.add_box(
                y=sub, name=role,
                marker_color=color, boxmean="sd",
                hovertemplate="ERA: %{y:.2f}<extra>" + role + "</extra>",
            )
    fig4.update_layout(
        yaxis_title="ERA",
        height=350,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
    )
    st.plotly_chart(fig4, use_container_width=True)

# ── Saves / Bullpen usage ─────────────────────────────────────────────────────
sv_df = df[df["saves"].fillna(0) > 0].sort_values("saves", ascending=False)
if not sv_df.empty:
    st.subheader("Bullpen: Saves & Holds")
    col_sv, col_hld = st.columns(2)
    with col_sv:
        st.markdown("**Saves**")
        st.dataframe(
            sv_df[["player_name", "games", "saves", "save_opps", "blown_saves", "era", "whip"]]
            .rename(columns={"player_name": "Player", "games": "G", "saves": "SV",
                             "save_opps": "SVO", "blown_saves": "BS", "era": "ERA", "whip": "WHIP"})
            .reset_index(drop=True),
            use_container_width=True, hide_index=True,
            column_config={
                "ERA":  st.column_config.NumberColumn(format="%.2f"),
                "WHIP": st.column_config.NumberColumn(format="%.2f"),
            },
        )
    hld_df = df[df["holds"].fillna(0) > 0].sort_values("holds", ascending=False)
    with col_hld:
        st.markdown("**Holds**")
        if not hld_df.empty:
            st.dataframe(
                hld_df[["player_name", "games", "holds", "era", "whip"]]
                .rename(columns={"player_name": "Player", "games": "G",
                                 "holds": "HLD", "era": "ERA", "whip": "WHIP"})
                .reset_index(drop=True),
                use_container_width=True, hide_index=True,
                column_config={
                    "ERA":  st.column_config.NumberColumn(format="%.2f"),
                    "WHIP": st.column_config.NumberColumn(format="%.2f"),
                },
            )
        else:
            st.info("No holds recorded under current filters.")
