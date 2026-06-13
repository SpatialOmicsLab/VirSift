# -*- coding: utf-8 -*-
"""
pages/01_🌍_Observatory.py

Two-mode page:
  • No data loaded  → Rich welcome / landing experience
  • Data loaded     → Live KPI dashboard with epidemic curve

Welcome design adapted from fasta_analysis_app_final.py welcome section,
expanded into a full landing page with workflow pipeline and feature badges.
"""

import base64
import os

import pandas as pd
import streamlit as st

from utils.minimal_i18n import T

# Pre-load logo as base64 for inline HTML embedding
try:
    _logo_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                              "assets", "Viral_sift_logo.png")
    with open(_logo_path, "rb") as _lf:
        _LOGO_B64 = base64.b64encode(_lf.read()).decode()
    _LOGO_HTML = (
        f'<img src="data:image/png;base64,{_LOGO_B64}" '
        f'style="height:6.4rem;width:auto;object-fit:contain;">'
    )
except Exception:
    _LOGO_HTML = '<span style="font-size:3rem;line-height:1;">🧬</span>'

try:
    import plotly.graph_objects as go
    _PLOTLY = True
except ImportError:
    _PLOTLY = False

# ─────────────────────────────────────────────────────────────────────────────
# State
# ─────────────────────────────────────────────────────────────────────────────
_active_df: pd.DataFrame  = st.session_state.get("active_df",   pd.DataFrame())
_filtered_df: pd.DataFrame = st.session_state.get("filtered_df", pd.DataFrame())
_display_df = _filtered_df if not _filtered_df.empty else _active_df
_is_filtered = not _filtered_df.empty


# ─────────────────────────────────────────────────────────────────────────────
# WELCOME LANDING  (shown when no dataset is loaded)
# ─────────────────────────────────────────────────────────────────────────────
if _active_df.empty:

    # ── Hero banner ──────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #0c4a6e 0%, #0369a1 45%, #0891b2 100%);
        padding: 2.5rem 2rem 2rem;
        border-radius: 16px;
        margin-bottom: 1.5rem;
        box-shadow: 0 8px 32px rgba(3,105,161,0.35);
    ">
        <div style="display:flex; align-items:center; gap:1rem; margin-bottom:.75rem;">
            <div style="flex-shrink:0;">{_LOGO_HTML}</div>
            <div>
                <h1 style="color:#f0f9ff; margin:0; font-size:1.9rem; font-weight:700;
                            letter-spacing:-.5px;">
                    {T('app_title')}
                </h1>
                <p style="color:#bae6fd; margin:0; font-size:1rem;">
                    {T('app_subtitle')} &nbsp;·&nbsp; {T('app_version')}
                </p>
            </div>
        </div>
        <p style="color:#e0f2fe; font-size:1.05rem; margin:0; line-height:1.55;">
            {T('welcome_tagline')}
        </p>
    </div>
    """, unsafe_allow_html=True)

    # ── Welcome message card (adapted from original) ──────────────────────
    st.markdown(f"""
    <div style="
        background: linear-gradient(135deg, #e0f2fe 0%, #ccfbf1 100%);
        color: #0c4a6e;
        padding: 1.5rem 2rem;
        border-radius: 12px;
        border-left: 5px solid #0ea5e9;
        margin-bottom: 1.5rem;
    ">
        <h3 style="color:#0c4a6e; margin-top:0; font-size:1.2rem;">
            {T('welcome_title')}
        </h3>
        <p style="margin:.25rem 0; font-size:1rem;">{T('welcome_message')}</p>
        <p style="margin:.25rem 0; color:#0369a1; font-size:.9rem;">{T('welcome_formats')}</p>
    </div>
    """, unsafe_allow_html=True)

    # ── Workflow pipeline ─────────────────────────────────────────────────
    st.markdown(f"### {T('welcome_how_title')}")

    steps = [
        ("📁", T("nav_workspace"),  T("welcome_step1_desc"), "#0ea5e9",
         "pages/02_📁_Workspace.py"),
        ("🔬", T("nav_refinery"),   T("welcome_step2_desc"), "#10b981",
         "pages/03_🔬_Sequence_Refinery.py"),
        ("📊", T("nav_analytics"),  T("welcome_step3_desc"), "#8b5cf6",
         "pages/05_📊_Analytics.py"),
        ("📋", T("nav_export"),     T("welcome_step4_desc"), "#f59e0b",
         "pages/06_📋_Export.py"),
    ]

    cols = st.columns(4)
    for col, (icon, title, desc, color, page_path) in zip(cols, steps):
        col.markdown(f"""
        <div style="
            background:#fff;
            border-top: 4px solid {color};
            border-radius:10px;
            padding:1.1rem .9rem .6rem;
            box-shadow:0 2px 8px rgba(0,0,0,.07);
            min-height:130px;
        ">
            <div style="font-size:1.6rem; margin-bottom:.3rem;">{icon}</div>
            <div style="font-weight:700; color:#1e3a8a; font-size:.95rem;
                        margin-bottom:.3rem;">{title}</div>
            <div style="color:#6b7280; font-size:.82rem; line-height:1.4;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)
        try:
            col.page_link(page_path, label=f"→ {title}",
                          use_container_width=True)
        except AttributeError:
            pass  # st.page_link available in Streamlit ≥ 1.29

    st.markdown("<br>", unsafe_allow_html=True)

    # ── Connector arrow row ───────────────────────────────────────────────
    st.markdown(
        "<p style='text-align:center; color:#94a3b8; font-size:1.4rem; "
        "letter-spacing:.6rem; margin:-0.5rem 0 1rem;'>→ → → →</p>",
        unsafe_allow_html=True,
    )

    # ── Feature badges ────────────────────────────────────────────────────
    st.markdown(f"### {T('welcome_features_title')}")

    features = [
        ("⚡", T("welcome_feat1"),    T("welcome_feat1_desc"), "#fef3c7", "#92400e"),
        ("🌐", T("welcome_feat2"),    T("welcome_feat2_desc"), "#dbeafe", "#1e40af"),
        ("🧠", T("welcome_feat3"),    T("welcome_feat3_desc"), "#d1fae5", "#065f46"),
        ("📦", T("welcome_feat4"),    T("welcome_feat4_desc"), "#ede9fe", "#4c1d95"),
    ]

    f_cols = st.columns(4)
    for col, (icon, title, desc, bg, fg) in zip(f_cols, features):
        col.markdown(f"""
        <div style="
            background:{bg}; color:{fg};
            border-radius:10px;
            padding:1rem .9rem;
            box-shadow:0 1px 4px rgba(0,0,0,.06);
        ">
            <div style="font-size:1.5rem; margin-bottom:.35rem;">{icon}</div>
            <div style="font-weight:700; font-size:.92rem;
                        margin-bottom:.3rem;">{title}</div>
            <div style="font-size:.80rem; opacity:.85;
                        line-height:1.4;">{desc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.divider()

    # ── CTA ───────────────────────────────────────────────────────────────
    cta_col, info_col = st.columns([2, 3])
    with cta_col:
        st.markdown(f"""
        <div style="
            background: linear-gradient(90deg,#0369a1 0%,#0891b2 100%);
            color:white; padding:1.2rem 1.5rem; border-radius:12px;
            box-shadow:0 4px 14px rgba(3,105,161,.3);
            text-align:center; margin-bottom:.6rem;
        ">
            <div style="font-size:1.4rem; margin-bottom:.4rem;">📁</div>
            <div style="font-weight:700; font-size:1rem; margin-bottom:.3rem;">
                {T('welcome_cta_title')}
            </div>
            <div style="font-size:.85rem; opacity:.9;">
                {T('welcome_cta_desc')}
            </div>
        </div>
        """, unsafe_allow_html=True)
        try:
            st.page_link("pages/02_📁_Workspace.py",
                         label=f"📁 {T('nav_workspace')} →",
                         use_container_width=True)
        except AttributeError:
            pass

    with info_col:
        st.markdown(f"""
        <div style="background:#f8fafc; border:1px solid #e2e8f0;
                    border-radius:12px; padding:1.2rem 1.5rem;">
            <div style="font-weight:700; color:#1e3a8a; font-size:.95rem;
                        margin-bottom:.6rem;">
                ℹ️ {T('welcome_info_title')}
            </div>
            <ul style="margin:0; padding-left:1.2rem; color:#475569;
                       font-size:.87rem; line-height:1.7;">
                <li>{T('welcome_info_2')}</li>
                <li>{T('welcome_info_3')}</li>
                <li>{T('welcome_info_4')}</li>
                <li>{T('welcome_info_5')}</li>
                <li>{T('welcome_info_batch')}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

    # ── Supported GISAID header formats — full-width centred block ────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"""
    <div style="text-align:center; margin-bottom:.9rem;">
        <span style="font-size:.82rem; color:#1e40af; font-weight:700;
                     letter-spacing:.3px; text-transform:uppercase;">
            {T('welcome_header_formats_title')}
        </span>
    </div>
    <div style="display:flex; gap:1.2rem; justify-content:center; flex-wrap:wrap;">
        <div style="flex:1; min-width:240px; max-width:380px;
                    background:#eff6ff; border-left:4px solid #0891b2;
                    border-radius:8px; padding:1rem 1.2rem;">
            <div style="font-size:.78rem; color:#0891b2; font-weight:700;
                        margin-bottom:.5rem;">🫁 {T('welcome_hrsv_format_label')}</div>
            <code style="font-size:.70rem; color:#0369a1; background:rgba(255,255,255,.6);
                         padding:.3rem .5rem; border-radius:4px; display:block;
                         word-break:break-all; line-height:1.6; white-space:normal;">&#62;Isolate_Name|GISAID_Accession|Collection_Date</code>
        </div>
        <div style="flex:1; min-width:240px; max-width:380px;
                    background:#ecfdf5; border-left:4px solid #059669;
                    border-radius:8px; padding:1rem 1.2rem;">
            <div style="font-size:.78rem; color:#059669; font-weight:700;
                        margin-bottom:.5rem;">🐦 {T('welcome_flu_format_label')}</div>
            <code style="font-size:.65rem; color:#065f46; background:rgba(255,255,255,.6);
                         padding:.3rem .5rem; border-radius:4px; display:block;
                         word-break:break-all; line-height:1.6; white-space:normal;">&#62;Isolate_Name|Virus_Type/Subtype|Gene_Segment|Collection_Date|GISAID_Accession|Clade</code>
        </div>
        <div style="flex:1; min-width:240px; max-width:380px;
                    background:#f5f3ff; border-left:4px solid #7c3aed;
                    border-radius:8px; padding:1rem 1.2rem;">
            <div style="font-size:.78rem; color:#7c3aed; font-weight:700;
                        margin-bottom:.5rem;">🧬 {T('welcome_aln_format_label')}</div>
            <code style="font-size:.65rem; color:#5b21b6; background:rgba(255,255,255,.6);
                         padding:.3rem .5rem; border-radius:4px; display:block;
                         word-break:break-all; line-height:1.6; white-space:normal;">&#62;Isolate_Name|Subtype|Segment|Date|Accession|Clade<br>ATGCGT---ATCG--GCTAA&nbsp;(gaps stripped automatically)</code>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # ── Supported segments note ────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:#f8fafc; border:1px solid #e2e8f0; border-radius:8px;
                padding:.7rem 1.2rem; margin-top:.8rem; margin-bottom:.4rem;">
        <span style="font-weight:700; color:#1e3a8a; font-size:.85rem;">
            🧬 {T('welcome_segments_note_title')}:
        </span>
        <span style="color:#475569; font-size:.84rem; margin-left:.4rem;">
            HA · NA · PB2 · PB1 · PA · NP · MP · NS · HE · P3
            — {T('welcome_segments_note_suffix')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── Supported Viruses & RSV Info ──────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown(f"### 🦠 {T('welcome_virus_support_title')}")
    v1, v2, v3, v4 = st.columns(4)
    for vcol, (vicon, vname, vdesc, vbg) in zip(
        [v1, v2, v3, v4],
        [
            ("🐦", "Influenza A/B", "H3N2, H1N1, H5N1\nand all subtypes", "#fef3c7"),
            ("🫁", "RSV A & B",     "Respiratory Syncytial\nVirus — full genome", "#dbeafe"),
            ("🦠", "SARS-CoV-2",    "Coronaviruses\nwith date metadata", "#d1fae5"),
            ("🧬", "Any Virus",     "Any FASTA with\nGISAID-style headers", "#ede9fe"),
        ],
    ):
        vcol.markdown(f"""
        <div style="background:{vbg}; border-radius:10px; padding:.9rem .8rem;
                    text-align:center; min-height:110px;">
            <div style="font-size:1.8rem;">{vicon}</div>
            <div style="font-weight:700; font-size:.9rem; margin:.3rem 0 .2rem;">{vname}</div>
            <div style="font-size:.78rem; color:#475569; white-space:pre-line;">{vdesc}</div>
        </div>
        """, unsafe_allow_html=True)

    st.caption(T("rsv_support_note"))

    # ── Quick Use Case Cues ────────────────────────────────────────────────
    st.markdown("<br>", unsafe_allow_html=True)
    with st.expander(f"💡 {T('welcome_tips_header')}", expanded=False):
        st.markdown(f"""
**{T('use_case_label_h3n2_filter')}**
> {T('use_case_tip_h3n2_filter')}

**{T('use_case_label_rsv_length')}**
> {T('use_case_tip_rsv_length')}

**{T('use_case_label_rsv_overwinter')}**
> {T('use_case_tip_timeline')}

**{T('use_case_label_rsv_ab')}**
> {T('use_case_tip_analytics')}

**{T('use_case_label_flu_clades')}**
> {T('use_case_tip_flu_clades')}

**{T('use_case_label_temporal')}**
> {T('use_case_tip_temporal')}

**{T('use_case_label_segment')}**
> {T('use_case_tip_segment')}

**{T('use_case_label_h5n1_host')}**
> {T('use_case_tip_h5n1_host')}

{T('welcome_tips_full_guide')}
        """)
        try:
            st.page_link("pages/07_📚_Documentation.py",
                         label=f"📚 {T('nav_documentation')} →",
                         use_container_width=False)
        except Exception:
            pass

    # Guide expander (adapted from original docs_header)
    with st.expander(f"📖 {T('welcome_guide_title')}", expanded=False):
        st.markdown(T("welcome_guide_body"))

    st.stop()


# ─────────────────────────────────────────────────────────────────────────────
# KPI DASHBOARD  (shown when a dataset is loaded)
# ─────────────────────────────────────────────────────────────────────────────
st.title(f"\U0001f30d {T('obs_header')}")

if _is_filtered:
    st.caption(T("obs_showing_filtered", n=len(_display_df), total=len(_active_df)))
else:
    st.caption(T("obs_showing_active"))

if len(_display_df) > 10_000:
    st.warning(T("sidebar_large_dataset_warning"))

# ── Platform overview — accessible from dashboard mode ───────────────────────
with st.expander(f"ℹ️ {T('obs_platform_overview')}", expanded=False):
    _ov1, _ov2, _ov3 = st.columns(3)
    with _ov1:
        st.markdown(f"""**{T('obs_overview_workflow')}**
1. 📁 **{T('nav_workspace')}** — {T('obs_overview_step1')}
2. 🔬 **{T('nav_refinery')}** — {T('obs_overview_step2')}
3. 🧬 **{T('nav_timeline')}** — {T('obs_overview_step3')}
4. 📊 **{T('nav_analytics')}** — {T('obs_overview_step4')}
5. 📋 **{T('nav_export')}** — {T('obs_overview_step5')}""")
    with _ov2:
        st.markdown(f"""**{T('obs_overview_tips_header')}**
- ✅ {T('obs_tip_activation')}
- 💾 {T('obs_tip_session')}
- ⚡ {T('obs_tip_cache')}
- 📦 {T('obs_tip_export_before_close')}""")
    with _ov3:
        st.markdown(f"""**{T('obs_overview_viruses')}**
🐦 Influenza A/B (H3N2, H1N1, H5N1)
🫁 RSV A & B
🦠 SARS-CoV-2
🧬 {T('obs_any_gisaid_header')}""")
    try:
        st.page_link("pages/07_📚_Documentation.py",
                     label=f"📚 {T('nav_documentation')} →",
                     use_container_width=False)
    except Exception:
        pass

# ── Per-page sidebar — section visibility toggles ────────────────────────────
with st.sidebar:
    st.divider()
    st.markdown(f"**{T('sidebar_obs_sections')}**")
    _show_kpis       = st.checkbox(T("sidebar_obs_kpis"),        value=True,  key="obs_show_kpis")
    _show_gauges     = st.checkbox(T("sidebar_obs_gauges"),      value=True,  key="obs_show_gauges")
    _show_epi        = st.checkbox(T("sidebar_obs_epi"),         value=True,  key="obs_show_epi")
    _show_locs       = st.checkbox(T("sidebar_obs_locs"),        value=True,  key="obs_show_locs")
    _show_clades     = st.checkbox(T("sidebar_obs_clades"),      value=True,  key="obs_show_clades")
    _show_batch      = st.checkbox(T("sidebar_obs_batch"),       value=True,  key="obs_show_batch")
    _show_new_charts = st.checkbox(T("sidebar_obs_new_charts"),  value=True,  key="obs_show_new_charts")

# ── Row 1: Core KPIs ─────────────────────────────────────────────────────────
if _show_kpis:
    k1, k2, k3, k4 = st.columns(4)
    k1.metric(T("sidebar_active_seqs"), f"{len(_display_df):,}")

    if "sequence_length" in _display_df.columns:
        k2.metric(T("sidebar_avg_length"),
                  f"{_display_df['sequence_length'].mean():.0f} bp")
    else:
        k2.metric(T("sidebar_avg_length"), "—")

    if "subtype_clean" in _display_df.columns:
        k3.metric(T("obs_kpi_subtypes"), str(_display_df["subtype_clean"].nunique()))
    else:
        k3.metric(T("obs_kpi_subtypes"), "—")

    if "collection_date" in _display_df.columns:
        dates = pd.to_datetime(_display_df["collection_date"], errors="coerce").dropna()
        k4.metric(T("obs_kpi_date_span"),
                  f"{(dates.max()-dates.min()).days} d" if not dates.empty else "—")

# ── Gauge KPI panel ───────────────────────────────────────────────────────────
if _show_gauges and _PLOTLY:
    with st.expander(f"\U0001f4ca {T('analytics_overview_header')}", expanded=False):
        _avg_len_obs = (
            float(_display_df["sequence_length"].dropna().mean())
            if "sequence_length" in _display_df.columns
               and not _display_df["sequence_length"].dropna().empty
            else 0.0
        )
        _n = max(len(_display_df), 1)
        _has_date    = _display_df.get("collection_date", pd.Series(dtype=str)).notna().sum()
        _has_sub     = _display_df.get("subtype_clean",   pd.Series(dtype=str)).notna().sum()
        _has_host    = _display_df.get("host",            pd.Series(dtype=str)).notna().sum()
        _comp_obs    = round(((_has_date + _has_sub + _has_host) / (3 * _n)) * 100, 1)
        _max_len_obs = max(3000, int(_avg_len_obs * 1.5) if _avg_len_obs > 0 else 2000)

        g1, g2, g3 = st.columns(3)

        with g1:
            _f_cnt = go.Figure(go.Indicator(
                mode="number", value=len(_display_df),
                title={"text": T("analytics_gauge_sequences"), "font": {"size": 13}},
                number={"font": {"color": "#0891b2", "size": 46}},
                domain={"x": [0, 1], "y": [0, 1]},
            ))
            _f_cnt.update_layout(height=165, margin=dict(l=8,r=8,t=40,b=8),
                                 paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(_f_cnt, use_container_width=True, key="obs_g_cnt")

        with g2:
            _f_len = go.Figure(go.Indicator(
                mode="gauge+number+delta", value=_avg_len_obs,
                number={"suffix": " bp", "font": {"color": "#0891b2", "size": 26}},
                delta={"reference": 1600, "position": "top",
                       "increasing": {"color": "#22c55e"},
                       "decreasing": {"color": "#ef4444"}},
                title={"text": T("analytics_gauge_length"), "font": {"size": 12}},
                gauge={
                    "axis": {"range": [0, _max_len_obs], "tickfont": {"size": 9}},
                    "bar": {"color": "#0891b2", "thickness": 0.7},
                    "steps": [
                        {"range": [0, 500],             "color": "#fca5a5"},
                        {"range": [500, 1500],          "color": "#fde68a"},
                        {"range": [1500, _max_len_obs], "color": "#86efac"},
                    ],
                    "threshold": {"line": {"color": "#dc2626", "width": 3},
                                  "thickness": 0.75, "value": 1600},
                },
                domain={"x": [0, 1], "y": [0.1, 1]},
            ))
            _f_len.update_layout(height=215, margin=dict(l=12,r=12,t=40,b=5),
                                 paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(_f_len, use_container_width=True, key="obs_g_len")

        with g3:
            _f_comp = go.Figure(go.Indicator(
                mode="gauge+number", value=_comp_obs,
                number={"suffix": "%", "font": {"color": "#059669", "size": 32}},
                title={"text": T("analytics_gauge_completeness"), "font": {"size": 12}},
                gauge={
                    "axis": {"range": [0, 100], "tickfont": {"size": 9}},
                    "bar": {"color": "#059669", "thickness": 0.7},
                    "steps": [
                        {"range": [0, 40],   "color": "#fca5a5"},
                        {"range": [40, 70],  "color": "#fde68a"},
                        {"range": [70, 100], "color": "#86efac"},
                    ],
                },
                domain={"x": [0, 1], "y": [0.1, 1]},
            ))
            _f_comp.update_layout(height=215, margin=dict(l=12,r=12,t=40,b=5),
                                  paper_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(_f_comp, use_container_width=True, key="obs_g_comp")
            st.caption(T("analytics_completeness_label"))

st.divider()

# ── Row 2: Date range + Epidemic curve ───────────────────────────────────────
if _show_epi:
    col_dates, col_curve = st.columns([1, 2])

    with col_dates:
        st.subheader(T("obs_date_range_header"))
        if "collection_date" in _display_df.columns:
            dates = pd.to_datetime(_display_df["collection_date"], errors="coerce").dropna()
            if not dates.empty:
                st.metric(T("obs_earliest"),   dates.min().strftime("%Y-%m-%d"))
                st.metric(T("obs_latest"),     dates.max().strftime("%Y-%m-%d"))
                st.metric(T("obs_dated_seqs"), f"{len(dates):,} / {len(_display_df):,}")
            else:
                st.info(T("obs_no_parseable_dates"))
        else:
            st.info(T("obs_no_date_col"))

    with col_curve:
        st.subheader(T("obs_epi_curve_header"))
        if "collection_date" in _display_df.columns:
            try:
                from utils.peak_detector import EpiWaveDetector
                ts = EpiWaveDetector()._build_weekly_counts(_display_df)
                if not ts.empty:
                    fig = go.Figure(go.Bar(
                        x=ts.index.tolist(), y=ts.values.tolist(),
                        marker_color="#0891b2", name=T("obs_epi_curve_header"),
                    ))
                    fig.update_layout(
                        xaxis_title=T("obs_epi_x"), yaxis_title=T("obs_epi_y"),
                        height=230, margin=dict(t=10, b=40, l=40, r=10),
                        showlegend=False,
                        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    )
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info(T("obs_no_dated_seqs"))
            except ImportError:
                st.info(T("obs_no_dated_seqs"))

    st.divider()

# ── Row 3: Subtypes | Hosts | Segments (always shown — part of KPI context) ──
col_sub, col_host, col_seg = st.columns(3)

with col_sub:
    st.subheader(T("obs_top_subtypes"))
    if "subtype_clean" in _display_df.columns:
        _vc = _display_df["subtype_clean"].value_counts().head(8)
        top = pd.DataFrame({T("obs_col_subtype"): _vc.index.tolist(),
                            T("obs_col_count"):   _vc.values.tolist()})
        st.dataframe(top, use_container_width=True, hide_index=True)

with col_host:
    st.subheader(T("obs_top_hosts"))
    if "host" in _display_df.columns:
        _vc = _display_df["host"].value_counts().head(8)
        top = pd.DataFrame({T("obs_col_host"):  _vc.index.tolist(),
                            T("obs_col_count"): _vc.values.tolist()})
        st.dataframe(top, use_container_width=True, hide_index=True)

with col_seg:
    st.subheader(T("obs_top_segments"))
    if "segment" in _display_df.columns:
        _vc = _display_df["segment"].value_counts().head(8)
        top = pd.DataFrame({T("obs_col_segment"): _vc.index.tolist(),
                            T("obs_col_count"):    _vc.values.tolist()})
        st.dataframe(top, use_container_width=True, hide_index=True)

# ── Row 4: Top [any field] bar chart (user-selectable) ───────────────────────
if _show_locs:
    st.divider()
    # Build map of available categorical columns in priority order
    _loc_field_map = {k: v for k, v in [
        (T("obs_col_location"),  "location"),
        (T("obs_col_host"),      "host"),
        (T("obs_col_subtype"),   "subtype_clean"),
        (T("obs_col_segment"),   "segment"),
        (T("obs_col_clade_l1"),  "clade_l1"),
        (T("obs_col_clade"),     "clade"),
    ] if v in _display_df.columns and _display_df[v].notna().any()}

    _OBS_BAR_PALETTES = {
        T("obs_palette_teal"):    "Teal",
        T("obs_palette_viridis"): "Viridis",
        T("obs_palette_plasma"):  "Plasma",
        T("obs_palette_blues"):   "Blues",
        T("obs_palette_greens"):  "Greens",
        T("obs_palette_reds"):    "Reds",
        T("obs_palette_sunset"):  "RdBu",
        T("obs_palette_orange"):  "Oranges",
    }
    _lf_hdr_col, _lf_ctrl_col, _lf_pal_col = st.columns([3, 1, 1])
    with _lf_ctrl_col:
        _lf_lbl = st.selectbox(
            T("obs_top_field_selector"),
            list(_loc_field_map.keys()),
            index=0, key="obs_loc_field",
        )
    with _lf_pal_col:
        _lf_pal_name = st.selectbox(
            T("obs_bar_palette_label"),
            list(_OBS_BAR_PALETTES.keys()),
            index=0, key="obs_loc_palette",
        )
    _lf_col = _loc_field_map.get(_lf_lbl, "location")
    _lf_scale = _OBS_BAR_PALETTES[_lf_pal_name]
    with _lf_hdr_col:
        st.subheader(T("obs_top_bar_header", field=_lf_lbl))

    if _lf_col in _display_df.columns:
        _vc_loc = _display_df[_lf_col].dropna().value_counts().head(15)
        top_loc = pd.DataFrame({_lf_lbl: _vc_loc.index.tolist(),
                                T("obs_col_count"): _vc_loc.values.tolist()})
        try:
            import plotly.express as px
            fig = px.bar(
                top_loc, x=T("obs_col_count"), y=_lf_lbl,
                orientation="h", height=max(320, min(len(_vc_loc) * 28, 520)),
                color=T("obs_col_count"), color_continuous_scale=_lf_scale,
            )
            fig.update_layout(
                yaxis={"categoryorder": "total ascending"},
                margin=dict(t=10, b=40, l=140, r=10),
                coloraxis_showscale=False,
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            )
            st.plotly_chart(fig, use_container_width=True)
        except ImportError:
            st.dataframe(top_loc, use_container_width=True, hide_index=True)

# ── Row 5: Donut chart — user-selectable field ───────────────────────────────
_donut_field_map = {k: v for k, v in [
    (T("obs_col_clade"),         "clade"),
    (T("obs_col_clade_l1"),      "clade_l1"),
    (T("obs_col_subtype"),       "subtype_clean"),
    (T("obs_col_host"),          "host"),
    (T("obs_col_host_species"),  "host_species"),
    (T("obs_col_segment"),       "segment"),
    (T("obs_col_location"),      "location"),
] if v in _display_df.columns and _display_df[v].notna().any()}

if _show_clades and _donut_field_map:
    st.divider()
    _dnt_hdr_col, _dnt_ctrl_col = st.columns([3, 1])
    with _dnt_ctrl_col:
        _dnt_lbl = st.selectbox(
            T("obs_donut_field_selector"),
            list(_donut_field_map.keys()),
            index=0, key="obs_donut_field",
        )
    _dnt_col = _donut_field_map.get(_dnt_lbl, "clade")
    with _dnt_hdr_col:
        st.subheader(T("obs_top_dist_header", field=_dnt_lbl))

    _vc_donut = _display_df[_dnt_col].dropna().value_counts().head(12)
    top_donut = pd.DataFrame({_dnt_lbl: _vc_donut.index.tolist(),
                              T("obs_col_count"): _vc_donut.values.tolist()})
    try:
        import plotly.express as px
        fig = px.pie(
            top_donut, names=_dnt_lbl, values=T("obs_col_count"),
            hole=0.42, height=340,
            color_discrete_sequence=px.colors.qualitative.Set2,
        )
        fig.update_layout(
            margin=dict(t=20, b=20),
            paper_bgcolor="rgba(0,0,0,0)",
            legend=dict(orientation="v", x=1.02, y=0.5),
        )
        st.plotly_chart(fig, use_container_width=True)
    except ImportError:
        st.dataframe(top_donut, use_container_width=True, hide_index=True)

# ── Extended Epidemiological Charts (Advanced) ────────────────────────────────
if _show_new_charts and _PLOTLY:
    import plotly.express as _px_ext
    import plotly.graph_objects as _go_ext

    st.divider()
    st.subheader(f"🔬 {T('obs_new_charts_header')}")

    # ── Auto-detect available categorical and numeric fields ──────────────────
    _ADV_CAT = {k: v for k, v in [
        (T("obs_col_host"),         "host"),
        (T("obs_col_host_species"), "host_species"),
        (T("obs_col_subtype"),      "subtype_clean"),
        (T("obs_col_segment"),      "segment"),
        (T("obs_col_clade"),        "clade"),
        (T("obs_col_clade_l1"),     "clade_l1"),
        (T("obs_col_location"),     "location"),
    ] if v in _display_df.columns and _display_df[v].notna().any()}
    _ADV_CAT_LBLS = list(_ADV_CAT.keys())

    # Numeric fields (always includes sequence_length if present; year computed later)
    _ADV_NUM = {}
    if "sequence_length" in _display_df.columns:
        _ADV_NUM[T("obs_3d_y")] = "sequence_length"
    if "collection_date" in _display_df.columns:
        _ADV_NUM[T("obs_3d_x")] = "_year_f"   # computed below
    _ADV_NUM_LBLS = list(_ADV_NUM.keys())

    _nc_tab1, _nc_tab2, _nc_tab3 = st.tabs([
        T("obs_sankey_tab"),
        T("obs_icicle_tab"),
        T("obs_3d_tab"),
    ])

    # ── Tab 1: Sankey — configurable N-level flow (up to 5 levels) ────────────
    with _nc_tab1:
        st.caption(T("obs_sankey_cue"))
        _none_opt = T("obs_none_option")
        _opt_required = _ADV_CAT_LBLS
        _opt_optional = [_none_opt] + _ADV_CAT_LBLS

        # ── Level selectors (5 slots; levels 1-2 required, 3-5 optional) ─────
        _s_def1 = _ADV_CAT_LBLS.index(T("obs_col_host")) if T("obs_col_host") in _ADV_CAT_LBLS else 0
        _s_def2 = (_ADV_CAT_LBLS.index(T("obs_col_subtype"))
                   if T("obs_col_subtype") in _ADV_CAT_LBLS else min(1, len(_ADV_CAT_LBLS) - 1))
        # Level 3 default: prefer Clade → Clade L1 → none
        _s_def3 = next(
            (i + 1 for i, v in enumerate(_ADV_CAT_LBLS)
             if v in (T("obs_col_clade"), T("obs_col_clade_l1"))),
            0,
        )
        _san_lv_cols = st.columns(5)
        with _san_lv_cols[0]:
            _san_l1 = st.selectbox(T("obs_sankey_level1"), _opt_required,
                                   index=_s_def1, key="adv_san_f1")
        with _san_lv_cols[1]:
            _san_l2 = st.selectbox(T("obs_sankey_level2"), _opt_required,
                                   index=_s_def2, key="adv_san_f2")
        with _san_lv_cols[2]:
            _san_l3 = st.selectbox(T("obs_sankey_level3"), _opt_optional,
                                   index=_s_def3, key="adv_san_f3")
        with _san_lv_cols[3]:
            _san_l4 = st.selectbox(T("obs_sankey_level4"), _opt_optional,
                                   index=0, key="adv_san_f4")
        with _san_lv_cols[4]:
            _san_l5 = st.selectbox(T("obs_sankey_level5"), _opt_optional,
                                   index=0, key="adv_san_f5")

        # ── Row 2: top-N slider, colour palette, title ────────────────────────
        _san_row2 = st.columns([1, 2, 3])
        with _san_row2[0]:
            _san_top_n = st.slider(T("obs_sankey_top_n"), min_value=3,
                                   max_value=20, value=8, key="adv_san_top_n")
        with _san_row2[1]:
            _SAN_PALETTES = {
                T("obs_san_pal_teal"):   ["#0891b2", "#10b981", "#8b5cf6", "#f59e0b", "#ef4444"],
                T("obs_san_pal_ocean"):  ["#1e40af", "#2563eb", "#3b82f6", "#60a5fa", "#93c5fd"],
                T("obs_san_pal_sunset"): ["#dc2626", "#ea580c", "#d97706", "#ca8a04", "#65a30d"],
                T("obs_san_pal_mono"):   ["#1e293b", "#334155", "#475569", "#64748b", "#94a3b8"],
            }
            _san_pal_name = st.selectbox(T("obs_sankey_palette"),
                                         list(_SAN_PALETTES.keys()), key="adv_san_pal")
            _san_pal = _SAN_PALETTES[_san_pal_name]
        with _san_row2[2]:
            _san_title = st.text_input(T("obs_adv_chart_title"),
                                       value=T("obs_sankey_header"),
                                       key="adv_san_title", max_chars=80)

        # ── Resolve columns and validate ─────────────────────────────────────
        def _san_resolve(lbl):
            return _ADV_CAT.get(lbl) if lbl and lbl != _none_opt else None

        _san_level_cols = [c for c in
                           [_san_resolve(l) for l in [_san_l1, _san_l2, _san_l3, _san_l4, _san_l5]]
                           if c]

        if len(set(_san_level_cols)) < len(_san_level_cols):
            st.warning(T("obs_sankey_duplicate_warning"))
        elif len(_san_level_cols) < 2:
            st.info(T("obs_sankey_no_data"))
        else:
            try:
                # Drop rows with any missing value in the selected level columns
                _san_available = [c for c in _san_level_cols if c in _display_df.columns]
                _san_df = (_display_df[_san_available]
                           .dropna(how="any")
                           .head(8000))

                # Per-level top-N value lists
                _san_lv_vals = [
                    _san_df[c].value_counts().head(_san_top_n).index.tolist()
                    if c in _san_df.columns else []
                    for c in _san_available
                ]

                # Flat node list with per-level offsets
                _san_nodes: list[str] = []
                _san_node_colors: list[str] = []
                _san_lv_offsets: list[int] = []
                _off = 0
                for _li, _vals in enumerate(_san_lv_vals):
                    _san_lv_offsets.append(_off)
                    _san_nodes.extend([str(v) for v in _vals])
                    _san_node_colors.extend(
                        [_san_pal[_li % len(_san_pal)]] * len(_vals)
                    )
                    _off += len(_vals)

                # Links for each adjacent level pair
                _san_links: list[dict] = []
                for _li in range(len(_san_available) - 1):
                    _sfa, _sfb = _san_available[_li], _san_available[_li + 1]
                    _va,  _vb  = _san_lv_vals[_li], _san_lv_vals[_li + 1]
                    _off_a, _off_b = _san_lv_offsets[_li], _san_lv_offsets[_li + 1]
                    _ni_a = {v: _off_a + j for j, v in enumerate(_va)}
                    _ni_b = {v: _off_b + j for j, v in enumerate(_vb)}
                    _mask = _san_df[_sfa].isin(_va) & _san_df[_sfb].isin(_vb)
                    for (_a, _b), _cnt in _san_df[_mask].groupby([_sfa, _sfb]).size().items():
                        if _a in _ni_a and _b in _ni_b:
                            _san_links.append(
                                {"s": _ni_a[_a], "t": _ni_b[_b], "v": int(_cnt)}
                            )

                if _san_links:
                    # Build semi-transparent link colors from source node color
                    def _hex_to_rgba(hex_col: str, alpha: float = 0.45) -> str:
                        h = hex_col.lstrip("#")
                        r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
                        return f"rgba({r},{g},{b},{alpha})"

                    _san_link_colors = [
                        _hex_to_rgba(_san_node_colors[l["s"]])
                        for l in _san_links
                    ]

                    _san_fig = _go_ext.Figure(_go_ext.Sankey(
                        arrangement="snap",
                        node=dict(
                            label=_san_nodes,
                            color=_san_node_colors,
                            pad=15,
                            thickness=24,
                            line=dict(color="#475569", width=0.5),
                            hovertemplate="%{label}<br>%{value:,} sequences<extra></extra>",
                        ),
                        link=dict(
                            source=[l["s"] for l in _san_links],
                            target=[l["t"] for l in _san_links],
                            value =[l["v"] for l in _san_links],
                            color=_san_link_colors,
                            hovertemplate=(
                                "%{source.label} \u2192 %{target.label}: "
                                "%{value:,}<extra></extra>"
                            ),
                        ),
                    ))
                    _san_fig.update_layout(
                        title=dict(text=_san_title, font=dict(size=13), x=0),
                        height=max(420, 60 * _san_top_n),
                        paper_bgcolor="rgba(0,0,0,0)",
                        margin=dict(t=40, b=20, l=10, r=10),
                        font=dict(size=11, color="#1e293b"),
                    )
                    st.plotly_chart(_san_fig, use_container_width=True)

                    # ── Download row ──────────────────────────────────────────
                    st.caption(T("obs_sankey_downloads"))
                    _dl_c1, _dl_c2, _dl_c3, _dl_c4 = st.columns(4)
                    with _dl_c1:
                        st.download_button(
                            T("obs_dl_html"),
                            _san_fig.to_html(full_html=True).encode("utf-8"),
                            "sankey.html", "text/html",
                            key="san_dl_html",
                        )
                    with _dl_c2:
                        st.download_button(
                            T("obs_dl_json_plotly"),
                            _san_fig.to_json().encode("utf-8"),
                            "sankey.json", "application/json",
                            key="san_dl_json",
                        )
                    with _dl_c3:
                        try:
                            _san_png = _san_fig.to_image(format="png", scale=2)
                            st.download_button(
                                T("obs_dl_png"), _san_png, "sankey.png", "image/png",
                                key="san_dl_png",
                            )
                        except Exception:
                            st.caption(T("obs_sankey_no_kaleido"))
                    with _dl_c4:
                        _link_rows = [
                            {
                                "Source": _san_nodes[l["s"]],
                                "Target": _san_nodes[l["t"]],
                                "Count":  l["v"],
                            }
                            for l in _san_links
                        ]
                        _link_csv = (
                            pd.DataFrame(_link_rows)
                            .to_csv(index=False)
                            .encode("utf-8")
                        )
                        st.download_button(
                            T("obs_dl_csv_links"),
                            _link_csv, "sankey_links.csv", "text/csv",
                            key="san_dl_csv",
                        )
                else:
                    st.info(T("obs_sankey_no_data"))
            except Exception as _san_err:
                st.warning(T("obs_chart_error", err=str(_san_err)))

    # ── Tab 2: Icicle — configurable path ────────────────────────────────────
    with _nc_tab2:
        st.caption(T("obs_icicle_cue"))
        _ic_c1, _ic_c2 = st.columns([3, 2])
        _ic_defaults = [l for l in [
            T("obs_col_segment"), T("obs_col_subtype"),
            T("obs_col_clade"), T("obs_col_clade_l1"),
        ] if l in _ADV_CAT_LBLS][:3]
        with _ic_c1:
            _ic_path_lbls = st.multiselect(
                T("obs_icicle_path_fields"), _ADV_CAT_LBLS,
                default=_ic_defaults, key="adv_ic_path",
                max_selections=4,
            )
        with _ic_c2:
            _ic_title = st.text_input(T("obs_adv_chart_title"),
                                      value=T("obs_icicle_header"),
                                      key="adv_ic_title", max_chars=80)

        _ic_path = [_ADV_CAT[l] for l in _ic_path_lbls if l in _ADV_CAT]
        if _ic_path:
            try:
                _ic_df  = _display_df[_ic_path].dropna(how="all").head(5000).fillna("Unknown")
                _ic_agg = _ic_df.groupby(_ic_path).size().reset_index(name="count")
                _ic_fig = _px_ext.icicle(
                    _ic_agg, path=_ic_path, values="count",
                    color="count", color_continuous_scale="Viridis",
                )
                _ic_fig.update_traces(
                    textinfo="label+value+percent parent",
                    root_color="rgba(0,0,0,0)",
                )
                _ic_fig.update_layout(
                    title=dict(text=_ic_title, font=dict(size=13), x=0),
                    height=440, paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(t=40, b=10, l=10, r=10),
                    coloraxis_showscale=False,
                )
                st.plotly_chart(_ic_fig, use_container_width=True)
                # Downloads
                st.caption(T("obs_sankey_downloads"))
                _ic_dl1, _ic_dl2, _ic_dl3 = st.columns(3)
                with _ic_dl1:
                    st.download_button(
                        T("obs_dl_html"),
                        _ic_fig.to_html(full_html=True).encode("utf-8"),
                        "icicle.html", "text/html", key="ic_dl_html",
                    )
                with _ic_dl2:
                    st.download_button(
                        T("obs_dl_json_plotly"),
                        _ic_fig.to_json().encode("utf-8"),
                        "icicle.json", "application/json", key="ic_dl_json",
                    )
                with _ic_dl3:
                    try:
                        st.download_button(
                            T("obs_dl_png"),
                            _ic_fig.to_image(format="png", scale=2),
                            "icicle.png", "image/png", key="ic_dl_png",
                        )
                    except Exception:
                        st.caption(T("obs_sankey_no_kaleido"))
            except Exception as _ic_err:
                st.warning(T("obs_chart_error", err=str(_ic_err)))
        else:
            st.info(T("obs_icicle_no_data"))

    # ── Tab 3: 3D Scatter — configurable axes ────────────────────────────────
    with _nc_tab3:
        st.caption(T("obs_3d_cue"))
        _d3_c1, _d3_c2, _d3_c3, _d3_c4 = st.columns(4)
        _d3_title_col, _ = st.columns([3, 1])

        _x_def = _ADV_NUM_LBLS.index(T("obs_3d_x")) if T("obs_3d_x") in _ADV_NUM_LBLS else 0
        _y_def = _ADV_NUM_LBLS.index(T("obs_3d_y")) if T("obs_3d_y") in _ADV_NUM_LBLS else 0

        _z_opts    = [T("obs_none_option")] + _ADV_CAT_LBLS
        _z_def     = next((i for i, v in enumerate(_z_opts)
                           if v == T("obs_col_segment")), 0)
        _clr_opts  = [T("obs_none_option")] + _ADV_CAT_LBLS
        _clr_def   = next((i for i, v in enumerate(_clr_opts)
                           if v == T("obs_col_subtype")), 0)

        with _d3_c1:
            _d3_x_lbl = st.selectbox(T("obs_3d_x_axis"), _ADV_NUM_LBLS,
                                     index=_x_def, key="adv_d3_x")
        with _d3_c2:
            _d3_y_lbl = st.selectbox(T("obs_3d_y_axis"), _ADV_NUM_LBLS,
                                     index=min(_y_def, len(_ADV_NUM_LBLS)-1),
                                     key="adv_d3_y")
        with _d3_c3:
            _d3_z_lbl = st.selectbox(T("obs_3d_z_axis"), _z_opts,
                                     index=_z_def, key="adv_d3_z")
        with _d3_c4:
            _d3_clr_lbl = st.selectbox(T("obs_3d_color_field"), _clr_opts,
                                       index=_clr_def, key="adv_d3_clr")
        with _d3_title_col:
            _d3_title = st.text_input(T("obs_adv_chart_title"),
                                      value=T("obs_3d_header"),
                                      key="adv_d3_title", max_chars=80)

        try:
            _sc3d = _display_df.copy()
            if "collection_date" in _sc3d.columns:
                _sc3d["_year_f"] = pd.to_datetime(
                    _sc3d["collection_date"], errors="coerce"
                ).dt.year.astype("Int64")

            _x_col = _ADV_NUM.get(_d3_x_lbl, "sequence_length")
            _y_col = _ADV_NUM.get(_d3_y_lbl, "sequence_length")

            # Z axis: encode categorical field as integer
            _z_col = None; _z_lbl_f = None
            _z_tick_text = None; _z_tick_vals = None
            if _d3_z_lbl != T("obs_none_option") and _d3_z_lbl in _ADV_CAT:
                _z_raw = _ADV_CAT[_d3_z_lbl]
                if _z_raw == "segment":
                    _SEG_ORDER = ["PB2", "PB1", "PA", "HA", "NP", "NA", "MP", "NS", "HE", "P3"]
                    _seg_enc = {s: i + 1 for i, s in enumerate(_SEG_ORDER)}
                    _sc3d["_seg_z"] = _sc3d["segment"].map(_seg_enc).fillna(0)
                    _z_col, _z_lbl_f  = "_seg_z", _d3_z_lbl
                    _z_tick_text = _SEG_ORDER
                    _z_tick_vals = list(range(1, len(_SEG_ORDER) + 1))
                else:
                    _uniq = _sc3d[_z_raw].dropna().unique().tolist()[:20]
                    _enc  = {v: i + 1 for i, v in enumerate(_uniq)}
                    _sc3d["_cat_z"] = _sc3d[_z_raw].map(_enc).fillna(0)
                    _z_col, _z_lbl_f  = "_cat_z", _d3_z_lbl
                    _z_tick_text = [str(u) for u in _uniq]
                    _z_tick_vals = list(range(1, len(_uniq) + 1))

            _clr_col = (_ADV_CAT.get(_d3_clr_lbl)
                        if _d3_clr_lbl != T("obs_none_option") else None)
            _hn_col  = "isolate" if "isolate" in _sc3d.columns else None

            _req = [c for c in [_x_col, _y_col] if c]
            _sc3d_c = _sc3d.dropna(subset=[c for c in _req if c in _sc3d.columns])
            _sc3d_s = _sc3d_c.sample(min(3000, len(_sc3d_c)), random_state=42)

            _z_use = _z_col if _z_col else _y_col
            _z_lbl_use = _z_lbl_f if _z_lbl_f else _d3_y_lbl
            _lbl_map = {_x_col: _d3_x_lbl, _y_col: _d3_y_lbl}
            if _z_col:
                _lbl_map[_z_col] = _z_lbl_f

            _fig_3d = _px_ext.scatter_3d(
                _sc3d_s, x=_x_col, y=_y_col, z=_z_use,
                color=_clr_col, hover_name=_hn_col, opacity=0.65, height=520,
                labels=_lbl_map,
            )
            _fig_3d.update_traces(marker=dict(size=3))
            _layout_3d = dict(
                title=dict(text=_d3_title, font=dict(size=13), x=0),
                paper_bgcolor="rgba(0,0,0,0)",
                scene=dict(
                    xaxis_title=_d3_x_lbl,
                    yaxis_title=_d3_y_lbl,
                    zaxis_title=_z_lbl_use,
                ),
                margin=dict(t=40, b=10, l=10, r=10),
            )
            if _z_tick_text:
                _layout_3d["scene"]["zaxis"] = dict(
                    ticktext=_z_tick_text, tickvals=_z_tick_vals,
                )
            _fig_3d.update_layout(**_layout_3d)
            st.plotly_chart(_fig_3d, use_container_width=True)
            # Downloads
            st.caption(T("obs_sankey_downloads"))
            _d3_dl1, _d3_dl2, _d3_dl3 = st.columns(3)
            with _d3_dl1:
                st.download_button(
                    "⬇ HTML",
                    _fig_3d.to_html(full_html=True).encode("utf-8"),
                    "scatter3d.html", "text/html", key="d3_dl_html",
                )
            with _d3_dl2:
                st.download_button(
                    "⬇ JSON (Plotly)",
                    _fig_3d.to_json().encode("utf-8"),
                    "scatter3d.json", "application/json", key="d3_dl_json",
                )
            with _d3_dl3:
                try:
                    st.download_button(
                        "⬇ PNG",
                        _fig_3d.to_image(format="png", scale=2),
                        "scatter3d.png", "image/png", key="d3_dl_png",
                    )
                except Exception:
                    st.caption(T("obs_sankey_no_kaleido"))
        except Exception as _3d_err:
            st.warning(f"3D scatter error: {_3d_err}")

# ── Batch Source Overview ─────────────────────────────────────────────────────
_raw_files = st.session_state.get("raw_files", [])
action_logs = st.session_state.get("action_logs", [])

if _show_batch and len(_raw_files) > 0:
    # Determine which files contributed to the current active_df
    _last_act = next(
        (lg for lg in reversed(action_logs) if lg.get("action") == "activate"),
        None,
    )
    _active_file_names = (
        _last_act.get("files", []) if _last_act else [_raw_files[0]["name"]]
    )
    _contributing = [rf for rf in _raw_files if rf["name"] in _active_file_names]

    st.divider()
    with st.expander(
        f"📦 {T('obs_batch_header')} ({len(_contributing)} file{'s' if len(_contributing) != 1 else ''})",
        expanded=len(_contributing) > 1,
    ):
        st.caption(T("obs_batch_caption", n=len(_contributing)))

        _total_seqs = max(len(_active_df), 1)
        _batch_rows = []
        for rf in _contributing:
            mini = pd.DataFrame(rf["parsed"])
            n    = rf["n_sequences"]

            # Date span
            _dspan = "—"
            if "collection_date" in mini.columns:
                _d = pd.to_datetime(mini["collection_date"], errors="coerce").dropna()
                if not _d.empty:
                    _dspan = (
                        f"{_d.min().strftime('%Y-%m')} → {_d.max().strftime('%Y-%m')}"
                        f"  ({(_d.max()-_d.min()).days} d)"
                    )

            # Subtypes
            _nsub = (
                ", ".join(sorted(
                    mini["subtype_clean"].dropna().astype(str).unique()
                )[:5])
                if "subtype_clean" in mini.columns else "—"
            )
            if "subtype_clean" in mini.columns and mini["subtype_clean"].nunique() > 5:
                _nsub += f" +{mini['subtype_clean'].nunique()-5} more"

            _batch_rows.append({
                T("obs_batch_file"):    rf["name"],
                T("sidebar_active_seqs"): f"{n:,}",
                T("obs_batch_pct"):     f"{n/_total_seqs*100:.1f}%",
                T("obs_batch_date_span"): _dspan,
                T("workspace_file_subtypes"): _nsub,
            })

        if _batch_rows:
            st.dataframe(
                pd.DataFrame(_batch_rows),
                use_container_width=True,
                hide_index=True,
            )

        # Bar chart: sequence count per file (when >1 file)
        if len(_batch_rows) > 1:
            try:
                import plotly.express as _px_batch
                _bc_df = pd.DataFrame([
                    {"file": rf["name"], "n": rf["n_sequences"]}
                    for rf in _contributing
                ])
                _fig_bc = _px_batch.bar(
                    _bc_df, x="file", y="n",
                    labels={"file": T("obs_batch_file"), "n": T("sidebar_active_seqs")},
                    color="n", color_continuous_scale="Blues",
                    height=220,
                )
                _fig_bc.update_layout(
                    margin=dict(t=10, b=60, l=40, r=10),
                    coloraxis_showscale=False,
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)",
                    xaxis_tickangle=-25,
                )
                st.plotly_chart(_fig_bc, use_container_width=True)
            except Exception:
                pass  # plotly not available — table already shown

        if len(_contributing) < len(_raw_files):
            _not_active = [rf["name"] for rf in _raw_files
                           if rf["name"] not in _active_file_names]
            st.caption(
                f"⚠️ {len(_not_active)} loaded file(s) not in current dataset: "
                + ", ".join(f"`{n}`" for n in _not_active[:3])
                + (" …" if len(_not_active) > 3 else "")
                + f" — go to 📁 Workspace to activate them."
            )
if action_logs:
    st.divider()
    _col_rename = {
        "action":    T("log_col_action"),
        "file":      T("log_col_file"),
        "sequences": T("log_col_sequences"),
        "time_s":    T("log_col_time_s"),
        "timestamp": T("log_col_timestamp"),
        "files":     T("log_col_files"),
    }
    with st.expander(T("obs_action_log_header")):
        _log_df = pd.DataFrame(action_logs).rename(columns=_col_rename)
        _act_col = T("log_col_action")
        if _act_col in _log_df.columns:
            _log_df[_act_col] = _log_df[_act_col].replace({
                "parse": T("log_action_parse"),
                "activate": T("log_action_activate"),
            })
        _log_df = _log_df.fillna("-")
        st.dataframe(_log_df, use_container_width=True, hide_index=True)

# ── Sequence-record interpretation disclaimer ────────────────────────────────
# The landing/home mode exits earlier with st.stop(), so this appears only
# after a dataset has been activated and the Observatory is being displayed.
st.divider()
st.caption(T("footer_sequence_disclaimer"))

# ── Inter-page navigation ─────────────────────────────────────────────────────
st.divider()
_nav1, _nav2 = st.columns(2)
try:
    _nav2.page_link("pages/02_📁_Workspace.py",
                    label=f"📁 {T('nav_workspace')} →",
                    use_container_width=True)
except AttributeError:
    _nav2.markdown(f"[📁 {T('nav_workspace')} →](pages/02_📁_Workspace.py)")
