"""Transactions page — searchable roster movement log."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

import plotly.express as px
import streamlit as st
import pandas as pd

import web_data as db

st.set_page_config(page_title="Transactions · Reading", page_icon="🔄", layout="wide")

st.markdown("""
<style>
[data-testid="stSidebar"] { background-color: #1a0a0a; }
[data-testid="stSidebar"] * { color: #f0e0d0 !important; }
h2 { border-left: 4px solid #8B0000; padding-left: 10px; }
</style>
""", unsafe_allow_html=True)

df = db.transactions()
df["date"] = pd.to_datetime(df["date"], errors="coerce")

with st.sidebar:
    st.markdown("## ⚾ Reading Fightin Phils")
    st.markdown("**2025 · Double-A Northeast**")
    st.divider()
    st.markdown("**Filters**")

    search = st.text_input("Search player name", placeholder="e.g. Reyes")

    types = ["All"] + sorted(df["type_desc"].dropna().unique().tolist())
    type_filter = st.selectbox("Transaction type", types)

    months = sorted(df["date"].dt.month.dropna().unique().tolist())
    month_names = {4:"April",5:"May",6:"June",7:"July",8:"August",9:"September"}
    month_opts  = ["All"] + [month_names.get(m, str(m)) for m in months]
    month_filter = st.selectbox("Month", month_opts)

st.title("🔄 Transactions — 2025")

# Apply filters
fdf = df.copy()
if search:
    fdf = fdf[fdf["player_name"].str.contains(search, case=False, na=False)]
if type_filter != "All":
    fdf = fdf[fdf["type_desc"] == type_filter]
if month_filter != "All":
    m_num = {v: k for k, v in month_names.items()}.get(month_filter)
    if m_num:
        fdf = fdf[fdf["date"].dt.month == m_num]

# ── Metrics ───────────────────────────────────────────────────────────────────
c1, c2, c3 = st.columns(3)
c1.metric("Total Transactions", len(fdf))
c2.metric("Players Involved", fdf["player_name"].nunique())
c3.metric("Transaction Types", fdf["type_desc"].nunique())

st.divider()

# ── Volume by month chart ─────────────────────────────────────────────────────
st.subheader("Transaction Volume by Month")

monthly = (
    df.copy()
    .assign(month=df["date"].dt.month,
            month_name=df["date"].dt.strftime("%b"))
    .groupby(["month","month_name","type_desc"])
    .size()
    .reset_index(name="count")
    .sort_values("month")
)

if not monthly.empty:
    fig = px.bar(
        monthly,
        x="month_name", y="count",
        color="type_desc",
        labels={"month_name": "Month", "count": "Transactions", "type_desc": "Type"},
        barmode="stack",
    )
    fig.update_layout(
        height=300,
        margin=dict(t=10, b=40),
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        legend=dict(orientation="h", y=1.05),
    )
    st.plotly_chart(fig, use_container_width=True)

# ── Type breakdown ────────────────────────────────────────────────────────────
col_pie, col_top = st.columns([1, 1])

with col_pie:
    st.subheader("By Type")
    type_counts = df["type_desc"].value_counts().reset_index()
    type_counts.columns = ["Type", "Count"]
    fig2 = px.pie(
        type_counts, names="Type", values="Count",
        color_discrete_sequence=px.colors.sequential.RdBu,
        hole=0.4,
    )
    fig2.update_layout(
        height=320,
        plot_bgcolor="#0e1117", paper_bgcolor="#0e1117",
        font_color="#ccc",
        margin=dict(t=20),
        legend=dict(font=dict(size=10)),
    )
    st.plotly_chart(fig2, use_container_width=True)

with col_top:
    st.subheader("Most Moved Players")
    top_players = (
        df.groupby("player_name").size()
        .reset_index(name="Moves")
        .sort_values("Moves", ascending=False)
        .head(10)
        .reset_index(drop=True)
    )
    top_players.index += 1
    top_players = top_players.rename(columns={"player_name": "Player"})
    st.dataframe(top_players, use_container_width=True, hide_index=False)

st.divider()

# ── Full transaction log ───────────────────────────────────────────────────────
st.subheader(f"Transaction Log ({len(fdf)} entries)")

display = fdf.copy()
display["date"] = display["date"].dt.strftime("%Y-%m-%d")
display["from_team"] = display["from_team"].fillna("—")
display["to_team"]   = display["to_team"].fillna("—")

display = display.rename(columns={
    "date":        "Date",
    "player_name": "Player",
    "type_desc":   "Type",
    "from_team":   "From",
    "to_team":     "To",
    "description": "Description",
})

st.dataframe(
    display[["Date","Player","Type","From","To","Description"]].reset_index(drop=True),
    use_container_width=True,
    height=500,
    hide_index=True,
)

# ── Roster movement summary ───────────────────────────────────────────────────
st.divider()
st.subheader("Roster Movement Summary")
st.caption("Players promoted to / demoted from Reading during 2025")

promo_keywords = ["Assigned", "Recalled", "Promoted", "Selected"]
demo_keywords  = ["Optioned", "Designated", "Released", "Transferred"]

promotions = df[df["type_desc"].str.contains("|".join(promo_keywords), case=False, na=False)
                & df["to_team"].str.contains("Reading", case=False, na=False)]
demotions  = df[df["type_desc"].str.contains("|".join(demo_keywords), case=False, na=False)
                & df["from_team"].str.contains("Reading", case=False, na=False)]

col_up, col_dn = st.columns(2)

with col_up:
    st.markdown(f"**Arrivals to Reading** ({len(promotions)})")
    if not promotions.empty:
        p = promotions[["date","player_name","type_desc","from_team"]].copy()
        p["date"] = pd.to_datetime(p["date"]).dt.strftime("%m/%d")
        p = p.rename(columns={"date":"Date","player_name":"Player",
                               "type_desc":"Type","from_team":"From"})
        st.dataframe(p.reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.info("None found under current data.")

with col_dn:
    st.markdown(f"**Departures from Reading** ({len(demotions)})")
    if not demotions.empty:
        d = demotions[["date","player_name","type_desc","to_team"]].copy()
        d["date"] = pd.to_datetime(d["date"]).dt.strftime("%m/%d")
        d = d.rename(columns={"date":"Date","player_name":"Player",
                               "type_desc":"Type","to_team":"To"})
        st.dataframe(d.reset_index(drop=True), use_container_width=True, hide_index=True)
    else:
        st.info("None found under current data.")
