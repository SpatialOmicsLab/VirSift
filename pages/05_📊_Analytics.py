# -*- coding: utf-8 -*-
"""
pages/05_📊_Analytics.py — Vectorized Visualizations + Extended Chart Suite

Charts (10 total):
  • Distribution        — bar / pie
  • Temporal            — line (monthly / quarterly / yearly)
  • Cross-Tab           — stacked bar (cat1 × cat2)
  • Epidemic Curve      — annotated bar with wave peaks/troughs
  • Sunburst Hierarchy  — clade → subtype → host (px.sunburst)
  • Treemap             — area-encoded hierarchy (px.treemap)
  • Violin / Box        — sequence length distribution (go.Violin)
  • Bubble Timeline     — Year × Location scatter (px.scatter)
  • Parallel Categories — multi-dim flow (px.parallel_categories)
  • Gantt Range         — per-subtype temporal span (px.timeline)

Dataset Overview:
  • 3 go.Indicator gauges (total seqs, avg length, completeness %)
  • Collapsible expander

Per-page sidebar:
  • Chart type quick-switch
  • Active palette mini-preview
  • Download-at-every-stage via session_state["an_fig"]
"""

import colorsys
import json
import random

import pandas as pd
import streamlit as st

from utils.minimal_i18n import T
from utils.peak_detector import EpiWaveDetector

try:
    import plotly.express as px
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

st.title(f"\U0001f4ca {T('analytics_header')}")

if not _PLOTLY:
    st.error("plotly is required for Analytics. Run: `pip install plotly`")
    st.stop()

_active_df: pd.DataFrame = st.session_state.get("active_df", pd.DataFrame())
_filtered_df: pd.DataFrame = st.session_state.get("filtered_df", pd.DataFrame())
_df = _filtered_df if not _filtered_df.empty else _active_df
_src = T("analytics_filtered_badge") if not _filtered_df.empty else T("analytics_active_badge")

if _df.empty:
    st.warning(T("error_no_active_df"))
    st.stop()

# ── Per-file scope selector (multi-file datasets only) ──────────────────────
_an_raw_files: list = st.session_state.get("raw_files", [])
_an_action_logs: list = st.session_state.get("action_logs", [])
_an_last_act = next(
    (lg for lg in reversed(_an_action_logs) if lg.get("action") == "activate"), None
)
_an_act_names: list = (
    _an_last_act.get("files", []) if _an_last_act
    else ([_an_raw_files[0]["name"]] if _an_raw_files else [])
)
_an_contrib = [rf for rf in _an_raw_files if rf["name"] in _an_act_names]

if len(_an_contrib) > 1:
    _an_scope_files = st.multiselect(
        T("timeline_scope_label"),
        options=[rf["name"] for rf in _an_contrib],
        default=st.session_state.get("an_scope_files", []),
        key="an_scope_files",
        help=T("timeline_scope_help"),
        placeholder=T("analytics_scope_all_placeholder"),
    )
    if _an_scope_files:
        _scope_dfs = []
        for _sf_name in _an_scope_files:
            _sf_rf = next((rf for rf in _an_contrib if rf["name"] == _sf_name), None)
            if _sf_rf:
                _sf_df = pd.DataFrame(_sf_rf["parsed"])
                _sf_df["_source_file"] = _sf_name
                _scope_dfs.append(_sf_df)
        if _scope_dfs:
            _df = pd.concat(_scope_dfs, ignore_index=True)
            _src = f"📁 {T('analytics_scope_files_selected', n=len(_an_scope_files))}"
            st.caption(
                f"📁 {T('timeline_scope_active')}: "
                f"**{', '.join(_an_scope_files)[:80]}**"
            )
    else:
        st.caption(T("timeline_scope_all_caption", n=len(_an_contrib)))
    st.divider()

# ── Multi-dimensional scope filters (collapsible) ───────────────────────────
# Builds a compact filter expander with one row per available dimension.
# Each filter is an independent multiselect; all active selections are ANDed.
_an_scope_dims = [
    ("segment",       T("analytics_segment_scope_label"),  "🧩", "an_seg_scope"),
    ("subtype_clean", T("analytics_subtype_scope_label"),  "🧬", "an_sub_scope"),
    ("host",          T("analytics_host_scope_label"),     "🐦", "an_host_scope"),
    ("host_species",  T("analytics_host_species_label"),   "🦆", "an_host_sp_scope"),
    ("location",      T("analytics_location_scope_label"), "📍", "an_loc_scope"),
    ("clade_l1",      T("analytics_clade_scope_label"),    "🌿", "an_clade_scope"),
]
# Only show dimensions that have ≥2 meaningful unique values
_an_active_dims = [
    (col, lbl, icon, key)
    for col, lbl, icon, key in _an_scope_dims
    if col in _df.columns
    and _df[col].replace("Unknown", pd.NA).dropna().nunique() >= 2
]

if _an_active_dims:
    _an_scope_labels: list[str] = []
    with st.expander(T("analytics_scope_expander"), expanded=False):
        for col, lbl, icon, sk in _an_active_dims:
            _opts = sorted(
                _df[col].replace("Unknown", pd.NA).dropna().unique().tolist(),
                key=str,
            )
            _sel = st.multiselect(
                f"{icon} {lbl}",
                options=_opts,
                default=st.session_state.get(sk, []),
                key=sk,
                placeholder=T("analytics_scope_all_placeholder"),
            )
            if _sel:
                _df = _df[_df[col].isin(_sel)].copy()
                _an_scope_labels.append(f"{icon}{', '.join(_sel[:3])}{'…' if len(_sel)>3 else ''}")
    if _an_scope_labels:
        _src = " · ".join(_an_scope_labels)
        st.caption(f"**{T('analytics_scope_active_badge')}:** {_src}")
    st.divider()

st.caption(T("analytics_dataset_label", n=f"{len(_df):,}", src=_src))

# ---------------------------------------------------------------------------
# Pre-built color palettes
# ---------------------------------------------------------------------------

_SCHEMES = {
    "bar": {
        "Nature Journal":  ["#E64B35","#4DBBD5","#00A087","#3C5488","#F39B7F","#8491B4","#91D1C2","#B09C85"],
        "Spike Surge":     ["#8dd3c7","#ffffb3","#bebada","#fb8072","#80b1d3","#fdb462","#b3de69","#fccde5"],
        "Epi Alert":       px.colors.sequential.Reds,
        "Genomic Helix":   px.colors.sequential.Viridis_r,
    },
    "pie": {
        "Viral Mosaic":    px.colors.qualitative.Set1,
        "Journal Crisp":   ["#00A087","#3C5488","#F39B7F","#8491B4","#D55E00","#CC79A7","#0072B2","#009E73"],
        "Nebula Burst":    px.colors.qualitative.Set2,
        "Outbreak Slices": ["#7fcdbb","#2c7fb8","#41b6c4","#a63603","#f03b20","#fee0d2","#fcbba1","#fc9272"],
    },
    "line": {
        "Journal Timeline":["#E31A1C","#1F78B4","#33A02C","#FF7F00","#6A3A4C"],
        "Pandemic Wave":   px.colors.diverging.Spectral,
        "Bio Rhythm":      px.colors.sequential.Oranges,
        "Evo Path":        px.colors.sequential.Greens,
    },
    "heatmap": {
        "Global Outbreak": px.colors.sequential.Reds,
        "Eco Layers":      px.colors.sequential.YlGnBu,
        "Helix Intensity": px.colors.sequential.Inferno,
        "Genomic Density": px.colors.diverging.RdBu_r,
    },
    "stacked": {
        "Host Stacks":     ["#8c510a","#d8b365","#f6e8c3","#c7eae5","#5ab4ac","#01665e","#f03b20","#fee0d2"],
        "Pub Stack":       ["#D55E00","#0072B2","#009E73","#CC79A7","#E69F00","#F0E442","#56B4E9","#00A087"],
        "Layered Genomes": px.colors.qualitative.Set2,
        "Outbreak Build":  px.colors.sequential.OrRd,
    },
    "sunburst": {
        "Viral Hierarchy": px.colors.qualitative.Set2,
        "Clade Cascade":   px.colors.qualitative.Pastel1,
        "Nature Lineage":  ["#E64B35","#4DBBD5","#00A087","#3C5488","#F39B7F","#8491B4","#91D1C2","#B09C85"],
        "Nebula Burst":    px.colors.qualitative.Dark2,
    },
    "treemap": {
        "Outbreak Area":   px.colors.sequential.Reds,
        "Eco Terrain":     px.colors.sequential.YlGnBu,
        "Lineage Blocks":  px.colors.qualitative.Set1,
        "Density Map":     px.colors.sequential.Inferno,
    },
    "violin": {
        "Length Spread":   px.colors.qualitative.Pastel1,
        "Genomic Range":   px.colors.qualitative.Set2,
        "Seg Palette":     ["#E64B35","#4DBBD5","#00A087","#3C5488","#F39B7F","#8491B4","#91D1C2","#B09C85"],
        "Muted Tones":     px.colors.qualitative.Pastel2,
    },
    "bubble": {
        "Spatio-Temporal": px.colors.qualitative.Set1,
        "Geo Scatter":     ["#264653","#2a9d8f","#e9c46a","#f4a261","#e76f51","#d62828","#023e8a","#0077b6"],
        "Heat Dots":       px.colors.sequential.OrRd,
        "Cool Bubbles":    px.colors.qualitative.Pastel2,
    },
    "parallel": {
        "Pathway Flow":    px.colors.sequential.Viridis,
        "Thermal Paths":   px.colors.sequential.Inferno,
        "Spectral Flow":   px.colors.diverging.Spectral,
        "Cool Stream":     px.colors.sequential.Blues,
    },
    "gantt": {
        "Timeline Bands":  px.colors.qualitative.Dark2,
        "Journal Spans":   ["#E64B35","#4DBBD5","#00A087","#3C5488","#F39B7F","#8491B4","#91D1C2","#B09C85"],
        "Muted Spans":     px.colors.qualitative.Pastel1,
        "Viral Epochs":    px.colors.qualitative.Set2,
    },
}

# ── Scheme display-name translations (kept inline to avoid 40+ JSON keys) ────
_lang = st.session_state.get("lang", st.session_state.get("language", "en"))
_SCHEME_RU_NAMES: dict[str, str] = {
    # bar
    "Nature Journal": "Научный журнал",    "Spike Surge": "Волна шипа",
    "Epi Alert": "Эпи-тревога",            "Genomic Helix": "Геномная спираль",
    # pie
    "Viral Mosaic": "Вирусная мозаика",    "Journal Crisp": "Чёткий журнал",
    "Nebula Burst": "Взрыв туманности",    "Outbreak Slices": "Срезы вспышки",
    # line
    "Journal Timeline": "Хронология журнала", "Pandemic Wave": "Пандемическая волна",
    "Bio Rhythm": "Биоритм",               "Evo Path": "Эво-путь",
    # heatmap
    "Global Outbreak": "Глобальная вспышка", "Eco Layers": "Эко-слои",
    "Helix Intensity": "Интенсивность спирали", "Genomic Density": "Геномная плотность",
    # stacked
    "Host Stacks": "Стеки хозяев",         "Pub Stack": "Публ.-стек",
    "Layered Genomes": "Слоистые геномы",  "Outbreak Build": "Рост вспышки",
    # sunburst
    "Viral Hierarchy": "Вирусная иерархия", "Clade Cascade": "Каскад клад",
    "Nature Lineage": "Природная линия",
    # treemap
    "Outbreak Area": "Ареал вспышки",      "Eco Terrain": "Эко-ландшафт",
    "Lineage Blocks": "Блоки линий",       "Density Map": "Карта плотности",
    # violin
    "Length Spread": "Разброс длины",      "Genomic Range": "Геномный диапазон",
    "Seg Palette": "Палитра сегментов",    "Muted Tones": "Приглушённые тона",
    # bubble
    "Spatio-Temporal": "Пространственно-временной", "Geo Scatter": "Георассеяние",
    "Heat Dots": "Тепловые точки",         "Cool Bubbles": "Холодные пузыри",
    # parallel
    "Pathway Flow": "Поток путей",         "Thermal Paths": "Тепловые пути",
    "Spectral Flow": "Спектральный поток", "Cool Stream": "Холодный поток",
    # gantt
    "Timeline Bands": "Временные полосы",  "Journal Spans": "Охваты журнала",
    "Muted Spans": "Приглушённые охваты",  "Viral Epochs": "Вирусные эпохи",
}


def _scheme_disp(name: str) -> str:
    """Return localised display name for a colour scheme internal key."""
    if _lang == "ru":
        return _SCHEME_RU_NAMES.get(name, name)
    return name


_FIELD_MAP = {
    T("analytics_field_subtype"):   "subtype_clean",
    T("analytics_field_host"):      "host",
    T("analytics_field_segment"):   "segment",
    T("analytics_field_location"):  "location",
    T("analytics_field_clade"):     "clade",
    T("analytics_field_clade_l1"):  "clade_l1",       # Broad clade grouping (L1 only)
    T("analytics_field_year"):      "_year",
    T("analytics_field_clone"):     "sequence_clone",  # Post-Timeline curated clone name
}

_CHART_TYPES = {
    T("analytics_chart_type_dist"):     "dist",
    T("analytics_chart_type_temporal"): "temporal",
    T("analytics_chart_type_stacked"):  "stacked",
    T("analytics_chart_type_epi"):      "epi",
    T("analytics_chart_type_heatmap"):  "heatmap",
    T("analytics_chart_type_sunburst"): "sunburst",
    T("analytics_chart_type_treemap"):  "treemap",
    T("analytics_chart_type_violin"):   "violin",
    T("analytics_chart_type_bubble"):   "bubble",
    T("analytics_chart_type_parallel"): "parallel",
    T("analytics_chart_type_gantt"):    "gantt",
}

# Human-readable display names for raw column names
_COL_LABELS: dict = {
    "clade":          T("analytics_field_clade"),
    "subtype_clean":  T("analytics_field_subtype"),
    "host":           T("analytics_field_host"),
    "segment":        T("analytics_field_segment"),
    "location":       T("analytics_field_location"),
    "clade_l1":       T("analytics_field_clade_l1"),
    "_year":          T("analytics_field_year"),
    "sequence_clone": T("analytics_field_clone"),
    "isolate":        "Isolate",
    "collection_date": "Collection Date",
}

_INTERVALS = {
    T("analytics_interval_month"):   "M",
    T("analytics_interval_quarter"): "Q",
    T("analytics_interval_year"):    "Y",
}

_LAYOUT = dict(
    paper_bgcolor="rgba(0,0,0,0)",
    plot_bgcolor="rgba(0,0,0,0)",
    margin=dict(t=55, b=30, l=25, r=25),
    title_font_size=18,
    font=dict(family="Inter, Arial, sans-serif"),
)


# ---------------------------------------------------------------------------
# Helper: enriched df  (adds _year column)
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def _enrich(df_hash: str, df: pd.DataFrame) -> pd.DataFrame:  # noqa: ARG001
    out = df.copy()
    if "collection_date" in out.columns:
        dates = pd.to_datetime(out["collection_date"], errors="coerce")
        out["_year"] = dates.dt.year.astype("Int64").astype(str).where(dates.notna(), other=None)
    return out


_df_enriched = _enrich(str(len(_df)) + str(_df.columns.tolist()), _df)

# ── sequence_clone enrichment from Timeline matrix (post-curation clone names) ──
# If the user has run Molecular Timeline, the matrix stores human-readable
# clone names keyed by sequence_hash.  We join them here so "Sequence Clone"
# appears in _FIELD_MAP for all chart types without re-running Timeline.
if "sequence_clone" not in _df_enriched.columns:
    _tl_mdf = st.session_state.get("_tl_matrix_df")
    if (
        _tl_mdf is not None
        and "sequence_hash" in _df_enriched.columns
        and "sequence_clone" in _tl_mdf.columns
    ):
        _h2c = _tl_mdf.set_index("sequence_hash")["sequence_clone"].to_dict()
        _df_enriched = _df_enriched.assign(
            sequence_clone=_df_enriched["sequence_hash"].map(_h2c)
        )


# ---------------------------------------------------------------------------
# Helper: data completeness %
# ---------------------------------------------------------------------------

def _calc_completeness(df: pd.DataFrame) -> float:
    n = max(len(df), 1)
    has_date    = df.get("collection_date", pd.Series(dtype=str)).notna().sum()
    has_subtype = df.get("subtype_clean",   pd.Series(dtype=str)).notna().sum()
    has_host    = df.get("host",            pd.Series(dtype=str)).notna().sum()
    return round(((has_date + has_subtype + has_host) / (3 * n)) * 100, 1)


# ---------------------------------------------------------------------------
# DATASET OVERVIEW — gauge KPI panel
# ---------------------------------------------------------------------------

with st.expander(f"\U0001f4ca {T('analytics_overview_header')}", expanded=True):
    _avg_len = (
        float(_df["sequence_length"].dropna().mean())
        if "sequence_length" in _df.columns and not _df["sequence_length"].dropna().empty
        else 0.0
    )
    _completeness = _calc_completeness(_df)
    _max_len = max(3000, int(_avg_len * 1.5) if _avg_len > 0 else 2000)

    ov1, ov2, ov3 = st.columns(3)

    with ov1:
        _fig_cnt = go.Figure(go.Indicator(
            mode="number",
            value=len(_df),
            title={"text": T("analytics_gauge_sequences"), "font": {"size": 14}},
            number={"font": {"color": "#0891b2", "size": 52}},
            domain={"x": [0, 1], "y": [0, 1]},
        ))
        _fig_cnt.update_layout(
            height=170, margin=dict(l=10, r=10, t=45, b=10),
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(_fig_cnt, use_container_width=True, key="ov_cnt")

    with ov2:
        _fig_len = go.Figure(go.Indicator(
            mode="gauge+number+delta",
            value=_avg_len,
            number={"suffix": " bp", "font": {"color": "#0891b2", "size": 28}},
            delta={"reference": 1600, "position": "top",
                   "increasing": {"color": "#22c55e"},
                   "decreasing": {"color": "#ef4444"}},
            title={"text": T("analytics_gauge_length"), "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, _max_len], "tickfont": {"size": 9}},
                "bar":  {"color": "#0891b2", "thickness": 0.7},
                "steps": [
                    {"range": [0, 500],       "color": "#fca5a5"},
                    {"range": [500, 1500],    "color": "#fde68a"},
                    {"range": [1500, _max_len], "color": "#86efac"},
                ],
                "threshold": {
                    "line": {"color": "#dc2626", "width": 3},
                    "thickness": 0.75, "value": 1600,
                },
            },
            domain={"x": [0, 1], "y": [0.1, 1]},
        ))
        _fig_len.update_layout(
            height=220, margin=dict(l=15, r=15, t=45, b=5),
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(_fig_len, use_container_width=True, key="ov_len")

    with ov3:
        _fig_comp = go.Figure(go.Indicator(
            mode="gauge+number",
            value=_completeness,
            number={"suffix": "%", "font": {"color": "#059669", "size": 34}},
            title={"text": T("analytics_gauge_completeness"), "font": {"size": 13}},
            gauge={
                "axis": {"range": [0, 100], "tickfont": {"size": 9}},
                "bar":  {"color": "#059669", "thickness": 0.7},
                "steps": [
                    {"range": [0, 40],   "color": "#fca5a5"},
                    {"range": [40, 70],  "color": "#fde68a"},
                    {"range": [70, 100], "color": "#86efac"},
                ],
            },
            domain={"x": [0, 1], "y": [0.1, 1]},
        ))
        _fig_comp.update_layout(
            height=220, margin=dict(l=15, r=15, t=45, b=5),
            paper_bgcolor="rgba(0,0,0,0)"
        )
        st.plotly_chart(_fig_comp, use_container_width=True, key="ov_comp")
        st.caption(T("analytics_completeness_label"))

st.divider()


# ---------------------------------------------------------------------------
# Chart generation functions (all vectorized — no iterrows)
# ---------------------------------------------------------------------------

def _empty_fig(msg: str) -> go.Figure:
    fig = go.Figure()
    fig.update_layout(
        **_LAYOUT,
        xaxis=dict(visible=False), yaxis=dict(visible=False),
        annotations=[dict(
            text=msg, xref="paper", yref="paper",
            x=0.5, y=0.5, showarrow=False,
            font=dict(size=16, color="#888"),
        )],
    )
    return fig


def _make_distribution(df: pd.DataFrame, field: str, chart_sub: str,
                        top_n: int, scheme) -> go.Figure:
    col = df[field].dropna().replace("", pd.NA).dropna()
    counts = col.value_counts().nlargest(top_n)
    if counts.empty:
        return _empty_fig(T("analytics_no_data"))

    labels = counts.index.tolist()
    values = counts.values.tolist()

    if chart_sub == "pie":
        colors = scheme if isinstance(scheme, list) else None
        fig = px.pie(names=labels, values=values, color_discrete_sequence=colors, hole=0.35)
        fig.update_traces(textposition="inside", textinfo="percent+label",
                          pull=[0.04] * len(labels))
    else:
        data_df = pd.DataFrame({"Category": labels, "Count": values})
        if isinstance(scheme, list):
            fig = px.bar(data_df.sort_values("Count"), y="Category", x="Count",
                         orientation="h", text_auto=True,
                         color="Category", color_discrete_sequence=scheme)
            fig.update_layout(showlegend=False)
        else:
            fig = px.bar(data_df.sort_values("Count"), y="Category", x="Count",
                         orientation="h", text_auto=True,
                         color="Count", color_continuous_scale=scheme)
            fig.update_layout(coloraxis_showscale=False)
        fig.update_yaxes(categoryorder="total ascending", title=None)
        fig.update_xaxes(title=T("obs_col_count"))

    fig.update_layout(**_LAYOUT)
    return fig


def _make_temporal(df: pd.DataFrame, interval_code: str, scheme) -> go.Figure:
    if "collection_date" not in df.columns:
        return _empty_fig(T("analytics_no_data"))

    dates = pd.to_datetime(df["collection_date"], errors="coerce").dropna()
    if dates.empty:
        return _empty_fig(T("analytics_no_data"))

    if interval_code == "Q":
        periods = dates.dt.to_period("Q").astype(str)
    else:
        fmt = {"M": "%Y-%m", "Y": "%Y"}[interval_code]
        periods = dates.dt.strftime(fmt)

    counts = periods.value_counts().sort_index()
    data_df = pd.DataFrame({"Period": counts.index, "Count": counts.values})
    line_color = scheme[0] if isinstance(scheme, list) and scheme else "#3b82f6"

    fig = px.line(data_df, x="Period", y="Count", markers=True, text="Count")
    fig.update_traces(line=dict(color=line_color, width=2.5),
                      marker=dict(size=7, color=line_color),
                      textposition="top center")
    fig.update_xaxes(title=T("analytics_period_label"), tickangle=45)
    fig.update_yaxes(title=T("obs_col_count"))
    fig.update_layout(**_LAYOUT)
    return fig


def _make_stacked(df: pd.DataFrame, cat1_field: str, cat2_field: str,
                  top_n: int, scheme) -> go.Figure:
    if cat1_field not in df.columns or cat2_field not in df.columns:
        return _empty_fig(T("analytics_no_data"))

    sub = df[[cat1_field, cat2_field]].dropna()
    if sub.empty:
        return _empty_fig(T("analytics_no_data"))

    top_cats = sub[cat1_field].value_counts().nlargest(top_n).index
    sub = sub[sub[cat1_field].isin(top_cats)]
    pivot = sub.groupby([cat1_field, cat2_field]).size().reset_index(name="Count")
    colors = scheme if isinstance(scheme, list) else None

    fig = px.bar(pivot, x=cat1_field, y="Count", color=cat2_field,
                 barmode="stack", text_auto=".2s",
                 color_discrete_sequence=colors,
                 category_orders={cat1_field: top_cats.tolist()})
    fig.update_traces(textfont_size=10, textangle=0,
                      textposition="inside", cliponaxis=False)
    fig.update_xaxes(tickangle=40, title=_COL_LABELS.get(cat1_field, cat1_field))
    fig.update_yaxes(title=T("obs_col_count"))
    fig.update_layout(**_LAYOUT,
                      legend_title=_COL_LABELS.get(cat2_field, cat2_field))
    return fig


def _make_epi_curve(df: pd.DataFrame, sensitivity: float, scheme) -> go.Figure:
    detector = EpiWaveDetector()
    ts = detector._build_weekly_counts(df)
    if ts.empty:
        return _empty_fig(T("analytics_no_data"))

    bar_color = (scheme[0] if isinstance(scheme, list) and scheme else "steelblue")

    fig = go.Figure()
    fig.add_trace(go.Bar(x=ts.index.tolist(), y=ts.values.tolist(),
                         marker_color=bar_color, name=T("analytics_epi_curve"),
                         opacity=0.85))

    waves = detector.detect_epi_waves(df, sensitivity=sensitivity)
    if waves["peaks"]:
        px_list, py_list = zip(*waves["peaks"])
        fig.add_trace(go.Scatter(
            x=list(px_list), y=list(py_list), mode="markers+text",
            marker=dict(symbol="triangle-up", size=14, color="#E64B35",
                        line=dict(width=1.5, color="white")),
            text=[f"▲{c}" for c in py_list],
            textposition="top center", textfont=dict(size=10, color="#E64B35"),
            name=T("analytics_wave_peaks"),
        ))
    if waves["troughs"]:
        tx_list, ty_list = zip(*waves["troughs"])
        fig.add_trace(go.Scatter(
            x=list(tx_list), y=list(ty_list), mode="markers",
            marker=dict(symbol="triangle-down", size=10, color="#4DBBD5",
                        line=dict(width=1.5, color="white")),
            name=T("analytics_wave_troughs"),
        ))

    fig.update_xaxes(title=T("obs_epi_x"), tickangle=45)
    fig.update_yaxes(title=T("obs_epi_y"))
    fig.update_layout(
        **_LAYOUT,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        annotations=[dict(text=T("analytics_wave_count", n=waves["wave_count"]),
                          xref="paper", yref="paper", x=0.01, y=0.97,
                          showarrow=False, font=dict(size=12, color="#888"))],
    )
    return fig


# ── 6 NEW chart types ───────────────────────────────────────────────────────

def _make_sunburst(df: pd.DataFrame, depth: int, top_n: int, scheme) -> go.Figure:
    hier_all = ["host", "subtype_clean", "clade"]
    hier = [c for c in hier_all if c in df.columns][:depth]
    if not hier:
        return _empty_fig(T("analytics_no_data"))

    sub = df[hier].copy().dropna()
    if sub.empty:
        return _empty_fig(T("analytics_no_data"))

    for col in hier:
        top_vals = sub[col].value_counts().nlargest(top_n).index
        sub = sub[sub[col].isin(top_vals)]

    agg = sub.groupby(hier).size().reset_index(name="count")
    colors = scheme if isinstance(scheme, list) else None

    fig = px.sunburst(agg, path=hier, values="count",
                      color_discrete_sequence=colors,
                      branchvalues="total")
    fig.update_traces(textinfo="label+percent root", insidetextorientation="radial")
    fig.update_layout(**_LAYOUT, height=520)
    return fig


def _make_treemap(df: pd.DataFrame, depth: int, top_n: int, scheme) -> go.Figure:
    hier_all = ["host", "subtype_clean", "clade"]
    hier = [c for c in hier_all if c in df.columns][:depth]
    if not hier:
        return _empty_fig(T("analytics_no_data"))

    sub = df[hier].copy().dropna()
    if sub.empty:
        return _empty_fig(T("analytics_no_data"))

    for col in hier:
        top_vals = sub[col].value_counts().nlargest(top_n).index
        sub = sub[sub[col].isin(top_vals)]

    agg = sub.groupby(hier).size().reset_index(name="count")

    _cscale = scheme if isinstance(scheme, str) else px.colors.sequential.Viridis
    fig = px.treemap(agg, path=hier, values="count",
                     color="count",
                     color_continuous_scale=_cscale,
                     branchvalues="total")
    fig.update_traces(
        textinfo="label+value+percent parent",
        textfont=dict(size=12),
        marker=dict(line=dict(width=2, color="#fff")),
        root_color="rgba(0,0,0,0)",
    )
    fig.update_layout(**_LAYOUT, height=520)
    return fig


def _make_violin(df: pd.DataFrame, group_col: str, scheme) -> go.Figure:
    if "sequence_length" not in df.columns:
        return _empty_fig(T("analytics_no_length_col"))

    pal = scheme if isinstance(scheme, list) else px.colors.qualitative.Set2

    fig = go.Figure()

    if group_col in df.columns:
        sub = df[["sequence_length", group_col]].dropna()
        top_groups = sub[group_col].value_counts().nlargest(8).index
        sub = sub[sub[group_col].isin(top_groups)]
        for i, grp in enumerate(top_groups):
            grp_data = sub[sub[group_col] == grp]["sequence_length"]
            color = pal[i % len(pal)]
            fig.add_trace(go.Violin(
                y=grp_data, name=str(grp)[:22],
                box_visible=True, meanline_visible=True,
                points="outliers",
                marker_color=color, line_color=color,
                opacity=0.75,
            ))
    else:
        sub = df[["sequence_length"]].dropna()
        fig.add_trace(go.Violin(
            y=sub["sequence_length"],
            name=T("analytics_gauge_sequences"),
            box_visible=True, meanline_visible=True,
            points="outliers",
            marker_color="#0891b2", line_color="#0891b2",
            opacity=0.75,
        ))

    fig.update_layout(
        **_LAYOUT, height=500,
        violinmode="overlay",
        yaxis_title="Sequence Length (bp)",
        xaxis_title=_COL_LABELS.get(group_col, group_col) if group_col in df.columns else "",
    )
    return fig


def _make_bubble(df: pd.DataFrame, interval_code: str,
                 y_field: str, top_n: int, scheme) -> go.Figure:
    if "collection_date" not in df.columns or y_field not in df.columns:
        return _empty_fig(T("analytics_no_data"))

    dates = pd.to_datetime(df["collection_date"], errors="coerce")
    if dates.dropna().empty:
        return _empty_fig(T("analytics_no_data"))

    if interval_code == "Y":
        period_col = dates.dt.year.astype("Int64").astype(str)
    else:
        period_col = (dates.dt.year.astype(str) + "-Q"
                      + dates.dt.quarter.astype(str))

    sub = df[[y_field]].copy()
    sub["_period"] = period_col.values
    sub = sub.dropna()

    top_y = sub[y_field].value_counts().nlargest(top_n).index
    sub = sub[sub[y_field].isin(top_y)]

    agg = sub.groupby(["_period", y_field]).size().reset_index(name="count")
    colors = scheme if isinstance(scheme, list) else None

    fig = px.scatter(agg, x="_period", y=y_field, size="count",
                     color=y_field, color_discrete_sequence=colors,
                     size_max=65, text="count")
    fig.update_traces(textposition="middle center",
                      textfont=dict(size=9, color="white"))
    fig.update_xaxes(title=T("analytics_period_label"), tickangle=45)
    fig.update_yaxes(title=_COL_LABELS.get(y_field, y_field))
    fig.update_layout(**_LAYOUT, height=520, showlegend=False)
    return fig


def _make_parallel(df: pd.DataFrame, dims: list) -> go.Figure:
    avail = [d for d in dims if d in df.columns]
    if len(avail) < 2:
        return _empty_fig(T("analytics_no_data"))

    sub = df[avail].dropna().copy()
    if sub.empty:
        return _empty_fig(T("analytics_no_data"))

    # Limit cardinality for readability
    for col in avail:
        top_vals = sub[col].value_counts().nlargest(15).index
        sub = sub[sub[col].isin(top_vals)]

    # Encode first dimension as numeric color
    sub["_color_idx"] = sub[avail[0]].astype("category").cat.codes.astype(float)

    fig = px.parallel_categories(
        sub, dimensions=avail, color="_color_idx",
        color_continuous_scale=px.colors.sequential.Viridis,
    )
    fig.update_layout(**_LAYOUT, height=500)
    return fig


def _make_gantt(df: pd.DataFrame, top_n: int, scheme, y_field: str = "subtype_clean") -> go.Figure:
    date_col = "collection_date"
    if y_field not in df.columns or date_col not in df.columns:
        return _empty_fig(T("analytics_no_data"))

    sub = df[[y_field, date_col]].copy()
    sub[date_col] = pd.to_datetime(sub[date_col], errors="coerce")
    sub = sub.dropna()
    if sub.empty:
        return _empty_fig(T("analytics_no_data"))

    top_vals = sub[y_field].value_counts().nlargest(top_n).index
    sub = sub[sub[y_field].isin(top_vals)]
    counts = sub[y_field].value_counts()

    agg = (
        sub.groupby(y_field)[date_col]
        .agg(Start="min", Finish="max")
        .reset_index()
    )
    agg["Sequences"] = agg[y_field].map(counts)
    # px.timeline requires Finish > Start
    same_day = agg["Start"] == agg["Finish"]
    agg.loc[same_day, "Finish"] = agg.loc[same_day, "Finish"] + pd.Timedelta(days=1)

    colors = scheme if isinstance(scheme, list) else None
    y_label = _COL_LABELS.get(y_field, y_field)

    fig = px.timeline(agg, x_start="Start", x_end="Finish", y=y_field,
                      color=y_field, color_discrete_sequence=colors,
                      hover_data={"Sequences": True, "Start": True, "Finish": True},
                      labels={y_field: y_label})
    fig.update_yaxes(autorange="reversed")
    fig.update_xaxes(title=T("analytics_gantt_date_axis"))
    fig.update_layout(**_LAYOUT, height=max(320, top_n * 36), showlegend=False)
    return fig


def _make_heatmap(df: pd.DataFrame, field: str, top_n: int, scheme) -> go.Figure:
    """Geographic / field frequency heatmap — horizontal bar with color scale."""
    if field not in df.columns:
        return _empty_fig(T("analytics_no_data"))

    counts = (
        df[field].dropna()
        .replace("", pd.NA).dropna()
        .value_counts().nlargest(top_n)
    )
    if counts.empty:
        return _empty_fig(T("analytics_no_data"))

    data_df = pd.DataFrame({
        _COL_LABELS.get(field, field): counts.index,
        T("obs_col_count"): counts.values,
    })
    col_name = _COL_LABELS.get(field, field)
    count_name = T("obs_col_count")

    # Color scale: use first entry if list, or the whole value if string
    cs = "Reds"
    if isinstance(scheme, str):
        cs = scheme
    elif isinstance(scheme, list) and scheme:
        # Build discrete scale from list
        cs = [[i / max(len(scheme) - 1, 1), c] for i, c in enumerate(scheme)]

    fig = px.bar(
        data_df.sort_values(count_name),
        y=col_name, x=count_name,
        orientation="h", text_auto=True,
        color=count_name,
        color_continuous_scale=cs,
    )
    fig.update_yaxes(categoryorder="total ascending", title=None)
    fig.update_xaxes(title=count_name)
    fig.update_layout(**_LAYOUT, coloraxis_showscale=True,
                      title=f"{col_name} — Top {top_n}")
    return fig


# ---------------------------------------------------------------------------
# UI — Chart controls
# ---------------------------------------------------------------------------

ctrl_col, palette_col = st.columns([3, 2])

with ctrl_col:
    # Bigger, bolder "Chart Type" label above the radio
    st.markdown(
        f"<p style='font-size:1.15rem;font-weight:800;color:#0c4a6e;"
        f"margin-bottom:0.1rem;letter-spacing:-.2px;'>"
        f"🗂 {T('analytics_chart_type_label')}</p>",
        unsafe_allow_html=True,
    )
    chart_type_label = st.radio(
        T("analytics_chart_type_label"),
        options=list(_CHART_TYPES.keys()),
        horizontal=True,
        key="an_chart_type",
        label_visibility="collapsed",
    )
    chart_type = _CHART_TYPES[chart_type_label]

    # ── Chart type guidance cue ────────────────────────────────────────────
    _CHART_GUIDES = {
        "dist":     T("analytics_guide_dist"),
        "temporal": T("analytics_guide_temporal"),
        "stacked":  T("analytics_guide_stacked"),
        "epi":      T("analytics_guide_epi"),
        "heatmap":  T("analytics_guide_heatmap"),
        "sunburst": T("analytics_guide_sunburst"),
        "treemap":  T("analytics_guide_treemap"),
        "violin":   T("analytics_guide_violin"),
        "bubble":   T("analytics_guide_bubble"),
        "parallel": T("analytics_guide_parallel"),
        "gantt":    T("analytics_guide_gantt"),
    }
    if chart_type in _CHART_GUIDES:
        st.info(_CHART_GUIDES[chart_type], icon="💡")

    # ── Dist ──────────────────────────────────────────────────────────────
    if chart_type == "dist":
        c1, c2, c3 = st.columns([2, 1, 1])
        field_label = c1.selectbox(
            T("analytics_field"),
            options=[k for k, v in _FIELD_MAP.items() if v in _df_enriched.columns],
            key="an_field",
        )
        _bar_label = T("analytics_dist_bar")
        _pie_label = T("analytics_dist_pie")
        _sub_label = c2.radio(T("analytics_dist_mode"),
                              options=[_bar_label, _pie_label],
                              horizontal=True, key="an_dist_mode")
        chart_sub = "pie" if _sub_label == _pie_label else "bar"
        top_n = c3.number_input(T("analytics_top_n"), min_value=3, max_value=50,
                                 value=10, step=1, key="an_top_n")

    # ── Temporal ──────────────────────────────────────────────────────────
    elif chart_type == "temporal":
        interval_label = st.selectbox(T("analytics_interval"),
                                       options=list(_INTERVALS.keys()), key="an_interval")

    # ── Stacked ───────────────────────────────────────────────────────────
    elif chart_type == "stacked":
        ca, cb, cc = st.columns([2, 2, 1])
        available = [k for k, v in _FIELD_MAP.items() if v in _df_enriched.columns]
        cat1_label = ca.selectbox(T("analytics_cat1"), options=available,
                                   key="an_cat1", index=0)
        cat2_label = cb.selectbox(T("analytics_cat2"), options=available,
                                   key="an_cat2", index=min(1, len(available) - 1))
        top_n_s = cc.number_input(T("analytics_top_n"), min_value=3, max_value=30,
                                   value=10, step=1, key="an_top_n_s")
        if cat1_label == cat2_label:
            st.warning(T("analytics_same_category_warning"))

    # ── Epidemic Curve ────────────────────────────────────────────────────
    elif chart_type == "epi":
        sensitivity = st.slider(T("analytics_sensitivity"),
                                min_value=0.1, max_value=1.0, value=0.5, step=0.05,
                                key="an_sensitivity")

    # ── Sunburst / Treemap ────────────────────────────────────────────────
    elif chart_type in ("sunburst", "treemap"):
        sb1, sb2 = st.columns(2)
        hier_max = sum(c in _df_enriched.columns for c in ["host", "subtype_clean", "clade"])
        depth = sb1.slider(T("analytics_hierarchy_depth"),
                            min_value=2, max_value=max(2, hier_max), value=min(3, hier_max),
                            step=1, key="an_depth",
                            help=T("analytics_hierarchy_depth_help"))
        top_n_h = sb2.number_input(T("analytics_top_n"), min_value=3, max_value=30,
                                    value=10, step=1, key="an_top_n_h")

    # ── Violin / Box ──────────────────────────────────────────────────────
    elif chart_type == "violin":
        grp_options = [k for k, v in _FIELD_MAP.items()
                       if v in _df_enriched.columns and v != "_year"]
        violin_group_label = st.selectbox(T("analytics_violin_group"),
                                           options=grp_options, key="an_violin_grp")

    # ── Bubble Timeline ───────────────────────────────────────────────────
    elif chart_type == "bubble":
        bb1, bb2, bb3, bb4 = st.columns(4)
        bbl_interval = bb1.selectbox(T("analytics_bubble_interval"),
                                      options=list(_INTERVALS.keys()), key="an_bbl_int")
        bbl_y_label = bb2.selectbox(
            T("analytics_bubble_y_field"),
            options=[k for k, v in _FIELD_MAP.items()
                     if v in _df_enriched.columns and v not in ("_year",)],
            key="an_bbl_y",
        )
        top_n_bb = bb3.number_input(T("analytics_top_n"), min_value=3, max_value=30,
                                     value=10, step=1, key="an_top_n_bb")

    # ── Parallel Categories ───────────────────────────────────────────────
    elif chart_type == "parallel":
        # All categorical columns available for parallel categories —
        # ordered from coarse (host) to fine (full clade).
        _par_candidates = [
            "host", "subtype_clean", "segment", "clade_l1",
            "location", "clade", "_year", "sequence_clone",
        ]
        all_cat_fields = [v for v in _par_candidates if v in _df_enriched.columns]
        default_dims = all_cat_fields[:3]
        # Show human-readable labels in the multiselect
        _par_label_to_col = {_COL_LABELS.get(v, v): v for v in all_cat_fields}
        _par_col_to_label = {v: k for k, v in _par_label_to_col.items()}
        _par_default_labels = [_par_col_to_label.get(c, c) for c in default_dims]
        pc_labels = st.multiselect(
            T("analytics_parallel_dims"),
            options=list(_par_label_to_col.keys()),
            default=_par_default_labels,
            max_selections=6,
            key="an_parallel_dims",
        )
        # Resolve back to column names for the chart builder
        all_cat_fields = [_par_label_to_col.get(lbl, lbl) for lbl in pc_labels]

    # ── Gantt Range ───────────────────────────────────────────────────────
    elif chart_type == "gantt":
        gn1, gn2 = st.columns([2, 1])
        _gantt_y_opts = [k for k, v in _FIELD_MAP.items()
                         if v in _df_enriched.columns and v != "_year"]
        gantt_y_label = gn1.selectbox(
            T("analytics_gantt_y_field"),
            options=_gantt_y_opts,
            key="an_gantt_y",
        )
        top_n_gantt = gn2.number_input(T("analytics_gantt_top_n"),
                                        min_value=3, max_value=40, value=15, step=1,
                                        key="an_top_n_gantt")

    # ── Heatmap ───────────────────────────────────────────────────────────
    elif chart_type == "heatmap":
        hm1, hm2 = st.columns([2, 1])
        hm_field_opts = [k for k, v in _FIELD_MAP.items() if v in _df_enriched.columns]
        hm_field_label = hm1.selectbox(T("analytics_heatmap_field"),
                                       options=hm_field_opts, key="an_hm_field")
        top_n_hm = hm2.number_input(T("analytics_top_n"), min_value=3, max_value=50,
                                     value=20, step=1, key="an_top_n_hm")

    # ── Color scheme selector ─────────────────────────────────────────────
    _SKEY_MAP = {
        "dist": "bar", "temporal": "line", "stacked": "stacked",
        "epi": "bar", "heatmap": "heatmap",
        "sunburst": "sunburst", "treemap": "treemap", "violin": "violin",
        "bubble": "bubble", "parallel": "parallel", "gantt": "gantt",
    }
    _skey = _SKEY_MAP.get(chart_type, "bar")
    if chart_type == "dist":
        _skey = chart_sub if "chart_sub" in dir() else "bar"

    palette_names = list(_SCHEMES.get(_skey, _SCHEMES["bar"]).keys())
    _palette_display = [_scheme_disp(n) for n in palette_names]
    _display_to_internal = {_scheme_disp(n): n for n in palette_names}
    _scheme_name_disp = st.selectbox(T("analytics_color_scheme"), options=_palette_display,
                                      key=f"an_scheme_{_skey}")
    scheme_name = _display_to_internal.get(_scheme_name_disp, palette_names[0])
    active_scheme = (
        st.session_state.get("custom_palette") or
        _SCHEMES.get(_skey, _SCHEMES["bar"])[scheme_name]
    )
    if st.session_state.get("custom_palette"):
        st.caption(f"\U0001f3a8 {T('analytics_using_custom_palette')}")


# ── Palette Studio (right column) ─────────────────────────────────────────

with palette_col:
    with st.expander(f"\U0001f3a8 {T('analytics_palette_studio')}", expanded=False):
        num_colors = st.slider(T("analytics_num_colors"), 3, 12, 8, key="an_num_colors")

        _defaults = ["#FF6B6B","#4ECDC4","#45B7D1","#96CEB4",
                     "#FFEAA7","#DDA0DD","#F39B7F","#8491B4",
                     "#91D1C2","#B09C85","#E64B35","#4DBBD5"]

        custom_colors = []
        cols_per_row = 4
        for row_i in range((num_colors + cols_per_row - 1) // cols_per_row):
            cols = st.columns(cols_per_row)
            for col_i in range(cols_per_row):
                ci = row_i * cols_per_row + col_i
                if ci < num_colors:
                    with cols[col_i]:
                        c = st.color_picker(f"C{ci+1}",
                                            value=_defaults[ci % len(_defaults)],
                                            key=f"an_cp_{ci}")
                        custom_colors.append(c)

        st.markdown("---")
        qa1, qa2, qa3 = st.columns(3)

        with qa1:
            if st.button(T("analytics_apply_palette"), use_container_width=True,
                         key="an_apply_pal"):
                st.session_state["custom_palette"] = custom_colors
                st.success(T("analytics_palette_applied"))
                st.rerun()

        with qa2:
            if st.button(T("analytics_dna_colors"), use_container_width=True,
                         key="an_dna_pal"):
                if "sequence" in _df.columns and len(_df) > 0:
                    sample_seq = str(_df["sequence"].iloc[0])[:200]
                    total = max(len(sample_seq), 1)
                    props = {
                        "A": sample_seq.count("A") / total,
                        "T": sample_seq.count("T") / total,
                        "G": sample_seq.count("G") / total,
                        "C": sample_seq.count("C") / total,
                    }
                    base_hues = {"A": 120, "T": 240, "G": 30, "C": 0}
                    dna_colors = []
                    for _ in range(num_colors):
                        base = random.choices(list(base_hues.keys()),
                                              weights=list(props.values()))[0]
                        hue = (base_hues[base] + random.randint(-20, 20)) % 360
                        s = random.uniform(0.6, 0.9)
                        l = random.uniform(0.45, 0.65)
                        r, g, b = colorsys.hls_to_rgb(hue / 360, l, s)
                        dna_colors.append(
                            f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                        )
                    st.session_state["custom_palette"] = dna_colors
                    st.success(T("analytics_dna_applied"))
                    st.rerun()
                else:
                    st.warning(T("analytics_no_seq_for_dna"))

        with qa3:
            if st.button(T("analytics_randomize"), use_container_width=True,
                         key="an_rand_pal"):
                rand_colors = []
                for _ in range(num_colors):
                    h = random.randint(0, 360)
                    s = random.uniform(0.65, 0.95)
                    l = random.uniform(0.50, 0.70)
                    r, g, b = colorsys.hls_to_rgb(h / 360, l, s)
                    rand_colors.append(
                        f"#{int(r*255):02x}{int(g*255):02x}{int(b*255):02x}"
                    )
                st.session_state["custom_palette"] = rand_colors
                st.success(T("analytics_randomized"))
                st.rerun()

        cur_pal = st.session_state.get("custom_palette")
        if cur_pal:
            st.markdown("---")
            st.markdown(f"**{T('analytics_current_palette')}**")
            swatch_cols = st.columns(min(8, len(cur_pal)))
            for si, sc in enumerate(cur_pal[:8]):
                with swatch_cols[si]:
                    st.markdown(
                        f"<div style='background:{sc};width:100%;height:60px;"
                        f"border-radius:8px;border:1px solid rgba(0,0,0,.15);"
                        f"display:flex;align-items:flex-end;justify-content:center;"
                        f"padding:4px'>"
                        f"<span style='background:rgba(255,255,255,.9);color:#333;"
                        f"padding:2px 4px;border-radius:4px;"
                        f"font-size:9px;font-family:monospace'>"
                        f"{sc.upper()}</span></div>",
                        unsafe_allow_html=True,
                    )
            if len(cur_pal) > 8:
                st.caption(f"+{len(cur_pal)-8} {T('analytics_more_colors')}")
            st.markdown("<br>", unsafe_allow_html=True)

            palette_json = json.dumps({
                "colors": cur_pal, "name": "VirSift Custom Palette",
                "count": len(cur_pal), "created": pd.Timestamp.now().isoformat(),
            }, indent=2)
            st.download_button(
                label=T("analytics_export_palette"),
                data=palette_json.encode("utf-8"),
                file_name="virsift_palette.json",
                mime="application/json",
                use_container_width=True, key="an_dl_palette",
            )
            if st.button(T("analytics_clear_palette"), use_container_width=True,
                         key="an_clear_pal"):
                st.session_state.pop("custom_palette", None)
                st.rerun()


# ---------------------------------------------------------------------------
# Generate chart
# ---------------------------------------------------------------------------

st.divider()
gc1, gc2 = st.columns([3, 1])
with gc1:
    gen_btn = st.button(T("analytics_generate"), type="primary",
                        use_container_width=True, key="an_generate")
with gc2:
    if st.button(T("analytics_clear_chart"), use_container_width=True, key="an_clear"):
        st.session_state.pop("an_fig", None)
        st.session_state.pop("an_fig_title", None)
        st.rerun()

if gen_btn:
    with st.spinner(T("analytics_generating")):
        try:
            fig = None
            title = ""

            if chart_type == "dist":
                resolved_field = _FIELD_MAP.get(field_label, "")
                if resolved_field not in _df_enriched.columns:
                    st.error(T("analytics_no_data"))
                else:
                    fig = _make_distribution(_df_enriched, resolved_field,
                                             chart_sub, int(top_n), active_scheme)
                    title = f"{field_label} {T('analytics_dist_title')}"

            elif chart_type == "temporal":
                interval_code = _INTERVALS[interval_label]
                fig = _make_temporal(_df, interval_code, active_scheme)
                title = f"{T('analytics_temporal')} — {interval_label}"

            elif chart_type == "stacked":
                if cat1_label == cat2_label:
                    st.error(T("analytics_same_category_warning"))
                else:
                    f1 = _FIELD_MAP.get(cat1_label, "")
                    f2 = _FIELD_MAP.get(cat2_label, "")
                    fig = _make_stacked(_df_enriched, f1, f2, int(top_n_s), active_scheme)
                    title = f"{cat2_label} \u00d7 {cat1_label}"

            elif chart_type == "epi":
                fig = _make_epi_curve(_df, sensitivity, active_scheme)
                title = T("analytics_epi_curve")

            elif chart_type == "sunburst":
                fig = _make_sunburst(_df_enriched, int(depth), int(top_n_h), active_scheme)
                title = T("analytics_chart_type_sunburst")

            elif chart_type == "treemap":
                fig = _make_treemap(_df_enriched, int(depth), int(top_n_h), active_scheme)
                title = T("analytics_chart_type_treemap")

            elif chart_type == "violin":
                grp_col = _FIELD_MAP.get(violin_group_label, "")
                fig = _make_violin(_df_enriched, grp_col, active_scheme)
                title = f"{T('analytics_chart_type_violin')} — {violin_group_label}"

            elif chart_type == "bubble":
                bbl_y_col = _FIELD_MAP.get(bbl_y_label, "")
                bbl_int = _INTERVALS.get(bbl_interval, "Y")
                fig = _make_bubble(_df_enriched, bbl_int, bbl_y_col,
                                    int(top_n_bb), active_scheme)
                title = f"{T('analytics_chart_type_bubble')} — {bbl_y_label}"

            elif chart_type == "parallel":
                # all_cat_fields contains resolved column names (from label→col map)
                fig = _make_parallel(_df_enriched, all_cat_fields if all_cat_fields else [])
                title = T("analytics_chart_type_parallel")

            elif chart_type == "gantt":
                _gantt_y_col = _FIELD_MAP.get(gantt_y_label, "subtype_clean")
                fig = _make_gantt(_df_enriched, int(top_n_gantt), active_scheme, y_field=_gantt_y_col)
                title = f"{T('analytics_chart_type_gantt')} — {gantt_y_label}"

            elif chart_type == "heatmap":
                hm_col = _FIELD_MAP.get(hm_field_label, "location")
                fig = _make_heatmap(_df_enriched, hm_col, int(top_n_hm), active_scheme)
                title = f"{T('analytics_chart_type_heatmap')} — {hm_field_label}"

            if fig is not None:
                fig.update_layout(title=title)
                st.session_state["an_fig"] = fig
                st.session_state["an_fig_title"] = title

        except Exception as e:
            st.error(f"{T('analytics_chart_error')}: {e}")


# ---------------------------------------------------------------------------
# Display chart + IMMEDIATE download (at the stage you see the chart)
# ---------------------------------------------------------------------------

if "an_fig" in st.session_state:
    # ── Inline chart title editor ─────────────────────────────────────────────
    _cur_title = st.session_state.get("an_fig_title", "")
    _edited_title = st.text_input(
        T("analytics_chart_title_edit"),
        value=_cur_title,
        max_chars=120,
        key="an_title_edit",
        label_visibility="visible",
    )
    if _edited_title and _edited_title != _cur_title:
        st.session_state["an_fig_title"] = _edited_title
        st.session_state["an_fig"].update_layout(title=_edited_title)

    st.plotly_chart(st.session_state["an_fig"], use_container_width=True)

    # Download row immediately below chart — no scrolling needed
    title_slug = (st.session_state.get("an_fig_title", "chart")
                  .lower().replace(" ", "_")
                  .replace("/", "_").replace("×", "x")[:40])
    html_bytes = st.session_state["an_fig"].to_html(
        include_plotlyjs="cdn"
    ).encode("utf-8")

    dl_html_col, dl_csv_col = st.columns(2)
    with dl_html_col:
        st.download_button(
            label=T("analytics_download_html"),
            data=html_bytes,
            file_name=f"virsift_{title_slug}.html",
            mime="text/html",
            help=T("analytics_download_html_help"),
            key="an_dl_html",
            type="primary",
            use_container_width=True,
        )
    with dl_csv_col:
        # Extract underlying data from the figure for CSV export
        try:
            _fig_data = st.session_state["an_fig"].data
            _frames = []
            for _trace in _fig_data:
                _td = {}
                for _attr in ("x", "y", "labels", "values", "ids", "parents"):
                    _val = getattr(_trace, _attr, None)
                    if _val is not None and len(_val) > 0:
                        _td[_attr] = list(_val)
                if _td:
                    _frames.append(pd.DataFrame(_td))
            _csv_df = pd.concat(_frames, ignore_index=True) if _frames else pd.DataFrame()
        except Exception:
            _csv_df = pd.DataFrame()

        _csv_bytes = _csv_df.to_csv(index=False).encode("utf-8") if not _csv_df.empty else b""
        st.download_button(
            label=T("analytics_download_csv"),
            data=_csv_bytes if _csv_bytes else b"no data",
            file_name=f"virsift_{title_slug}.csv",
            mime="text/csv",
            use_container_width=True,
            key="an_dl_csv",
            disabled=not bool(_csv_bytes),
        )


# ---------------------------------------------------------------------------
# Per-page sidebar — chart type quick-switch + palette preview
# ---------------------------------------------------------------------------

with st.sidebar:
    st.divider()
    st.markdown(f"**{T('sidebar_an_chart_type')}**")
    st.caption(chart_type_label)
    # Show active file scope when a single source file is selected
    _an_sb_scope = st.session_state.get("an_file_scope", T("timeline_scope_all"))
    if _an_sb_scope and _an_sb_scope != T("timeline_scope_all"):
        st.caption(f"📁 {_an_sb_scope[:28]}")

    cur_pal_sb = st.session_state.get("custom_palette")
    if cur_pal_sb:
        st.markdown(f"**{T('sidebar_an_palette')}**")
        swatch_html = "".join(
            f"<span style='background:{c};display:inline-block;"
            f"width:18px;height:18px;border-radius:3px;"
            f"margin:2px;border:1px solid rgba(0,0,0,.15)'></span>"
            for c in cur_pal_sb[:8]
        )
        st.markdown(swatch_html, unsafe_allow_html=True)
        if len(cur_pal_sb) > 8:
            st.caption(f"+{len(cur_pal_sb)-8} {T('analytics_more_colors')}")

# ---------------------------------------------------------------------------
# Sequence-record interpretation disclaimer
# ---------------------------------------------------------------------------

st.divider()
st.caption(T("footer_sequence_disclaimer"))

# ---------------------------------------------------------------------------
# Page navigation arrows
# ---------------------------------------------------------------------------

st.divider()
_an1, _an2 = st.columns(2)
try:
    _an1.page_link("pages/03_🔬_Sequence_Refinery.py",
                   label=f"← 🔬 {T('nav_refinery')}", use_container_width=True)
    _an2.page_link("pages/06_📋_Export.py",
                   label=f"📋 {T('nav_export')} →", use_container_width=True)
except AttributeError:
    pass  # st.page_link available in Streamlit ≥ 1.29
