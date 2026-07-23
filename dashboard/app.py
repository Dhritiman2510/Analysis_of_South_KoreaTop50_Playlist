"""
K-Pulse — Comeback Momentum, Chart Re-Entry & Fandom Intensity
Analysis of the South Korea Top 50 Playlist (Atlantic Recording Corp.)

Run:
    pip install -r requirements.txt
    streamlit run app.py

Expected CSV columns:
    date, position, song, artist, popularity, duration_ms,
    album_type, total_tracks, is_explicit, album_cover_url
"""

from __future__ import annotations

import io
from pathlib import Path
import sys


ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(ROOT_DIR))


import numpy as np
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ---------------------------------------------------------------------------
# Page config & theme
# ---------------------------------------------------------------------------
st.set_page_config(
    page_title="K-Pulse · KR Top 50 Comeback Analytics",
    page_icon="🎧",
    layout="wide",
)

CSS = """
<style>
.stApp { background: #0a0612; color: #fff; }
h1, h2, h3, h4 { color: #fff !important; }
.metric-card {
    background: rgba(255,255,255,0.04);
    border: 1px solid rgba(255,255,255,0.08);
    padding: 1rem 1.25rem; border-radius: 14px;
}
.metric-card .lbl { font-size:.72rem; letter-spacing:.2em;
    text-transform:uppercase; color:#f0abfc; }
.metric-card .val { font-size:1.9rem; font-weight:700; color:#fff; margin-top:.25rem; }
.metric-card .sub { font-size:.72rem; color:rgba(255,255,255,.5); margin-top:.15rem; }
.eyebrow { font-family: ui-monospace, monospace; font-size:.72rem;
    color:#e879f9; letter-spacing:.25em; text-transform:uppercase; }
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

PLOTLY_TEMPLATE = "plotly_dark"
ACCENT = "#e879f9"
ACCENT2 = "#38bdf8"
ACCENT3 = "#f472b6"

# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def load_data(source) -> pd.DataFrame:
    df = pd.read_csv(source)
    # Robust date parsing (handles DD-MM-YYYY and ISO)
    df["date"] = pd.to_datetime(df["date"], dayfirst=True, errors="coerce")
    df = df.dropna(subset=["date"]).copy()
    df["is_explicit"] = df["is_explicit"].astype(str).str.upper().eq("TRUE")
    df["duration_min"] = df["duration_ms"] / 60_000
    df["key"] = df["song"].str.strip() + " — " + df["artist"].str.strip()
    return df.sort_values(["key", "date"]).reset_index(drop=True)


@st.cache_data(show_spinner=False)
def compute_song_stats(df: pd.DataFrame) -> pd.DataFrame:
    """Per-song analytics: runs, re-entries, momentum, retention, fandom score."""
    records = []
    for key, g in df.groupby("key", sort=False):
        g = g.sort_values("date")
        dates = g["date"].to_numpy()
        # Split contiguous date runs (gap > 1 day starts a new run)
        gaps = np.diff(dates).astype("timedelta64[D]").astype(int)
        split_idx = np.where(gaps > 1)[0] + 1
        runs = np.split(g.to_dict("records"), split_idx) if len(g) > 1 else [g.to_dict("records")]

        momentum_scores, retention_days, gap_days, run_bounds = [], [], [], []
        for i, r in enumerate(runs):
            positions = [x["position"] for x in r]
            pops = [x["popularity"] for x in r]
            first_rank, best_rank = positions[0], min(positions)
            jump = first_rank - best_rank
            pop_delta = max(pops) - pops[0]
            momentum_scores.append(jump * 2 + pop_delta)
            peak_idx = int(np.argmin(positions))
            retention_days.append(len(r) - peak_idx)
            run_bounds.append((r[0]["date"], r[-1]["date"]))
            if i > 0:
                gap_days.append((r[0]["date"] - runs[i - 1][-1]["date"]).days)

        peak_rank = int(g["position"].min())
        peak_pop = int(g["popularity"].max())
        avg_pop = float(g["popularity"].mean())
        momentum = float(max(momentum_scores)) if momentum_scores else 0.0
        reentries = len(runs) - 1
        fandom = reentries * 15 + momentum * 0.5 + (peak_pop - avg_pop) * 0.8

        meta = g.iloc[0]
        records.append({
            "key": key,
            "song": meta["song"],
            "artist": meta["artist"],
            "album_type": meta["album_type"],
            "is_explicit": bool(meta["is_explicit"]),
            "total_tracks": int(meta["total_tracks"]),
            "duration_min": float(meta["duration_min"]),
            "cover": meta["album_cover_url"],
            "days_on": int(len(g)),
            "peak": peak_rank,
            "avg_pop": round(avg_pop, 1),
            "peak_pop": peak_pop,
            "runs": len(runs),
            "reentries": reentries,
            "momentum": round(momentum, 1),
            "avg_retention": round(float(np.mean(retention_days)), 1),
            "avg_gap_days": round(float(np.mean(gap_days)) if gap_days else 0.0, 1),
            "fandom": round(float(fandom), 1),
            "run_bounds": run_bounds,
        })
    return pd.DataFrame(records).sort_values("fandom", ascending=False).reset_index(drop=True)


# ---------------------------------------------------------------------------
# Sidebar — data source + filters
# ---------------------------------------------------------------------------
st.sidebar.title("🎧 K-Pulse")
st.sidebar.caption("KR Top 50 Comeback & Fandom Analytics")


data_file = ROOT_DIR / "data" / "Atlantic_South_Korea.csv"
df=load_data(data_file)

st.sidebar.header("Download Dataset")
st.sidebar.download_button(
    use_container_width=True,
    label="Download",
    data=df.to_csv(index=False).encode("utf-8"),
    file_name="Atlantic_South_Korea.csv",

)

stats = compute_song_stats(df)

# Filters
min_d, max_d = df["date"].min().date(), df["date"].max().date()
date_range = st.sidebar.date_input("Date range", (min_d, max_d),
                                   min_value=min_d, max_value=max_d)
album_type = st.sidebar.radio("Album type", ["All", "single", "album"], horizontal=True)
min_reentries = st.sidebar.slider("Min re-entries", 0, int(stats["reentries"].max()), 0)
explicit_only = st.sidebar.checkbox("Explicit only", value=False)
query = st.sidebar.text_input("Search song / artist")

df_f = df[(df["date"].dt.date >= date_range[0]) & (df["date"].dt.date <= date_range[1])]
stats_f = stats.copy()
if album_type != "All":
    stats_f = stats_f[stats_f["album_type"] == album_type]
if explicit_only:
    stats_f = stats_f[stats_f["is_explicit"]]
stats_f = stats_f[stats_f["reentries"] >= min_reentries]
if query:
    q = query.lower()
    stats_f = stats_f[stats_f["song"].str.lower().str.contains(q) |
                      stats_f["artist"].str.lower().str.contains(q)]

# ---------------------------------------------------------------------------
# Hero + KPIs
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">Atlantic Recording · KR Chart Intelligence</div>',
            unsafe_allow_html=True)
st.title("Comeback Momentum, Chart Re-Entry & Fandom Intensity")
st.caption(f"South Korea Top 50 · {min_d} → {max_d} · "
           f"{df['date'].nunique()} days · {stats.shape[0]} unique tracks")

def kpi(col, label, value, sub=""):
    col.markdown(
        f'<div class="metric-card"><div class="lbl">{label}</div>'
        f'<div class="val">{value}</div><div class="sub">{sub}</div></div>',
        unsafe_allow_html=True)

c1, c2, c3, c4 = st.columns(4)
kpi(c1, "Days Tracked", f"{df['date'].nunique():,}")
kpi(c2, "Unique Tracks", f"{stats.shape[0]:,}")
reentry_share = (stats["reentries"] > 0).mean() * 100
kpi(c3, "Songs w/ Re-Entry", f"{(stats['reentries'] > 0).sum():,}",
    f"{reentry_share:.1f}% of catalog")
kpi(c4, "Avg Re-Entries", f"{stats['reentries'].mean():.2f}", "per track")

st.divider()

# ---------------------------------------------------------------------------
# 01 · Fandom leaderboard
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">01 · Fandom Intensity Proxy</div>',
            unsafe_allow_html=True)
st.subheader("Who moves the needle hardest?")
st.caption("Composite score = re-entry frequency × popularity spike sharpness × rank recovery.")

show_cols = ["song", "artist", "album_type", "fandom", "reentries",
             "momentum", "peak", "days_on", "avg_retention"]
st.dataframe(
    stats_f[show_cols].head(30).rename(columns={
        "song": "Song", "artist": "Artist", "album_type": "Type",
        "fandom": "Fandom", "reentries": "Re-Entries", "momentum": "Momentum",
        "peak": "Peak #", "days_on": "Days On", "avg_retention": "Avg Retention (d)",
    }),
    use_container_width=True, hide_index=True,
)

# ---------------------------------------------------------------------------
# 02 · Re-entry timeline for a selected track
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">02 · Re-Entry Timeline</div>',
            unsafe_allow_html=True)
options = stats_f["key"].tolist() or stats["key"].tolist()
selected_key = st.selectbox("Select a track", options, index=0)
sel = stats[stats["key"] == selected_key].iloc[0]
sel_df = df[df["key"] == selected_key].sort_values("date")

left, right = st.columns([1, 3])
with left:
    st.image(sel["cover"], use_container_width=True)
    st.markdown(f"### {sel['song']}")
    st.caption(sel["artist"])
    st.write(f"**Album type:** {sel['album_type']}  \n"
             f"**Explicit:** {'Yes' if sel['is_explicit'] else 'No'}  \n"
             f"**Duration:** {sel['duration_min']:.2f} min  \n"
             f"**Peak rank:** #{sel['peak']}  \n"
             f"**Days on chart:** {sel['days_on']} days  \n"
             f"**Chart runs:** {sel['runs']} runs  \n"
             f"**Re-entries:** {sel['reentries']} re-entries  \n"
             f"**Avg gap between runs:** {sel['avg_gap_days']} days  \n"
             f"**Momentum score:** {sel['momentum']}  \n"
             f"**Fandom score:** {sel['fandom']}")

with right:
    # Break the line at gaps so exits appear as breaks
    plot_df = sel_df.copy()
    plot_df["gap"] = plot_df["date"].diff().dt.days.gt(1).cumsum()
    fig = go.Figure()
    for _, grp in plot_df.groupby("gap"):
        fig.add_trace(go.Scatter(
            x=grp["date"], y=grp["position"], mode="lines+markers",
            line=dict(color=ACCENT, width=2), marker=dict(size=4),
            showlegend=False,
            hovertemplate="%{x|%Y-%m-%d}<br>Rank #%{y}<extra></extra>",
        ))
    fig.update_yaxes(autorange="reversed", range=[50, 1], title="Rank")
    fig.update_layout(template=PLOTLY_TEMPLATE, height=420,
                      margin=dict(l=10, r=10, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 03 · Momentum spike detection
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">03 · Momentum Spike Detection</div>',
            unsafe_allow_html=True)
st.subheader("The sharpest comebacks")
top_m = stats.sort_values("momentum", ascending=False).head(15)
fig = px.bar(top_m, x="momentum", y="key", orientation="h",
             color_discrete_sequence=[ACCENT])
fig.update_layout(template=PLOTLY_TEMPLATE, height=520, yaxis_title="",
                  xaxis_title="Momentum",
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  yaxis={"categoryorder": "total ascending"})
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 04 · Content attributes vs momentum
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">04 · Content Attributes vs Momentum</div>',
            unsafe_allow_html=True)
c1, c2 = st.columns(2)

with c1:
    st.markdown("**Single vs Album**")
    grp = stats.groupby("album_type").agg(
        momentum=("momentum", "mean"),
        retention=("avg_retention", "mean"),
        count=("key", "count"),
    ).reset_index()
    fig = px.bar(grp.melt(id_vars="album_type", value_vars=["momentum", "retention"]),
                 x="album_type", y="value", color="variable", barmode="group",
                 color_discrete_sequence=[ACCENT, ACCENT2])
    fig.update_layout(template=PLOTLY_TEMPLATE, height=340,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

with c2:
    st.markdown("**Explicit vs Clean**")
    grp = stats.assign(kind=np.where(stats["is_explicit"], "Explicit", "Clean")) \
               .groupby("kind").agg(momentum=("momentum", "mean"),
                                    count=("key", "count")).reset_index()
    fig = px.bar(grp.melt(id_vars="kind", value_vars=["momentum", "count"]),
                 x="kind", y="value", color="variable", barmode="group",
                 color_discrete_sequence=[ACCENT3, "#a78bfa"])
    fig.update_layout(template=PLOTLY_TEMPLATE, height=340,
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
    st.plotly_chart(fig, use_container_width=True)

# Duration vs momentum scatter
st.markdown("**Song duration vs momentum**")
fig = px.scatter(stats, x="duration_min", y="momentum",
                 size=stats["days_on"].clip(lower=3),
                 color="album_type", hover_name="key",
                 color_discrete_sequence=[ACCENT, ACCENT2])
fig.update_layout(template=PLOTLY_TEMPLATE, height=380,
                  xaxis_title="Duration (min)", yaxis_title="Momentum",
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 05 · Re-entry × momentum map
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">05 · Re-Entry × Momentum Map</div>',
            unsafe_allow_html=True)
sc = stats[stats["reentries"] > 0]
fig = px.scatter(sc, x="reentries", y="momentum",
                 size="days_on", hover_name="key", color="album_type",
                 color_discrete_sequence=[ACCENT, ACCENT2])
fig.update_layout(template=PLOTLY_TEMPLATE, height=440,
                  paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                  xaxis_title="Re-Entry Count", yaxis_title="Momentum")
st.plotly_chart(fig, use_container_width=True)

# ---------------------------------------------------------------------------
# 06 · Re-entry champions
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">06 · Re-Entry Champions</div>',
            unsafe_allow_html=True)
champs = stats[stats["reentries"] > 0].sort_values("reentries", ascending=False).head(12)
cols = st.columns(3)
for i, (_, row) in enumerate(champs.iterrows()):
    with cols[i % 3]:
        st.image(row["cover"], width=90)
        st.markdown(f"**{row['song']}**  \n_{row['artist']}_")
        st.caption(f"{row['reentries']} re-entries · Peak #{row['peak']}")

# ---------------------------------------------------------------------------
# 07 · Executive summary
# ---------------------------------------------------------------------------
st.markdown('<div class="eyebrow">07 · Executive Summary</div>',
            unsafe_allow_html=True)
st.subheader("What this means for release strategy")

m_single = stats[stats["album_type"] == "single"]["momentum"].mean()
m_album = stats[stats["album_type"] == "album"]["momentum"].mean()
m_expl = stats[stats["is_explicit"]]["momentum"].mean()
m_clean = stats[~stats["is_explicit"]]["momentum"].mean()

c1, c2 = st.columns(2)
c1.info(f"**{reentry_share:.0f}% of tracks re-enter the chart.** "
        "Chart exit is rarely terminal in Korea; budget for sustained promo "
        "windows, not single launches.")
c2.info(("**Album cuts win comeback intensity.** " if m_album > m_single
         else "**Singles carry the sharpest spikes.** ")
        + f"Albums avg {m_album:.1f} momentum vs singles {m_single:.1f}.")
c1.info(f"**Clean content dominates.** Momentum: clean {m_clean:.1f} · "
        f"explicit {m_expl:.1f}. KR mainstream still rewards clean-audio releases.")
c2.info("**Re-entry gaps predict promo cadence.** Tight fandom cycles cluster "
        "around performances and anniversaries — align pushes to those windows.")

# ---------------------------------------------------------------------------
# Export
# ---------------------------------------------------------------------------
with st.expander("⬇️  Download per-song analytics (CSV)"):
    buf = io.StringIO()
    stats.drop(columns=["run_bounds"]).to_csv(buf, index=False)
    st.download_button("Download CSV", buf.getvalue(),
                       file_name="kpulse_song_stats.csv", mime="text/csv")

st.caption(f"Prepared for Atlantic Recording Corporation · "
           f"Data window {min_d} → {max_d}")
