# -*- coding: utf-8 -*-
"""
app.py — VirSift v1.0.0
Multilingual entry point + minimal sidebar + st.navigation() wiring.

This file is the ONLY place that:
  - Calls init_translations() (once per session)
  - Initializes the full session_state schema
  - Renders the persistent sidebar
  - Wires st.navigation()

No business logic lives here. All analysis logic is in utils/.
All page content is in pages/.
"""

import pandas as pd
import streamlit as st

from utils.minimal_i18n import T, init_translations

# ---------------------------------------------------------------------------
# Page config — must be the first Streamlit call in the script
# ---------------------------------------------------------------------------
try:
    from PIL import Image as _PIL_Image
    _page_icon = _PIL_Image.open("assets/Viral_sift_logo.png")
    _page_icon.load()  # Force full pixel read while file handle is open
except Exception:
    _page_icon = "🧬"

st.set_page_config(
    page_title="VirSift",
    page_icon=_page_icon,
    layout="wide",
    initial_sidebar_state="expanded",
    menu_items={
        "Get Help": None,
        "Report a bug": None,
        "About": "VirSift v1.0.0 — Zero-Lag Epidemiological Surveillance",
    },
)

# ---------------------------------------------------------------------------
# Step 1: Initialize translations (must precede all T() calls)
# ---------------------------------------------------------------------------
init_translations()


# ---------------------------------------------------------------------------
# Step 2: Initialize session state schema (idempotent — safe on every rerun)
# ---------------------------------------------------------------------------
def _init_session_state() -> None:
    """Initialize all session state keys to their defaults.

    Keys are only set if not already present, preserving state across reruns.
    Schema defined in roadmap Section 3.
    """
    defaults: dict = {
        # --- I18N & Regional ---
        "language": "en",
        "region": "RU",
        "translation_cache": {},
        "user_terminology": {},     # Custom Rospotrebnadzor / institutional overrides

        # --- Data Pipeline ---
        "raw_files": [],            # Unicode-safe uploaded file objects
        "active_df": pd.DataFrame(),    # Written ONCE on Activate — never mutated after
        "filtered_df": pd.DataFrame(),  # All filtering writes here only

        # --- Filter State ---
        "global_filters": [],       # List of filter rule dicts (sidebar badge count)
        "selected_peaks": [],       # HITL: Peak Checklist selections
        "lasso_zones": [],          # HITL: Visual Lasso selected ranges
        "checkpoint_targets": [],   # HITL: Custom Time Checkpoint month strings

        # --- Investigation Context ---
        "investigation_mode": "surveillance",  # 'surveillance' | 'research'
        "temporal_baseline": "epi_season",     # Calendar mode for temporal grouping
        "strain_hashes": {},                   # Identity tracking across sessions

        # --- Logging ---
        "action_logs": [],          # Filter operation records for export

        # --- Theme ---
        "theme": "light",           # 'light' | 'dark' | 'auto'

        # --- Data Mode ---
        # 'current'  → filtered_df if available, else active_df
        # 'original' → always active_df (raw snapshot from activation)
        "data_mode": "original",

        # --- Export filename prefix ---
        # Prepended to every downloaded file name across all pages.
        # E.g. "myproject" → myproject_20250225_1430.fasta
        "export_prefix": "virsift",
    }
    for key, default in defaults.items():
        if key not in st.session_state:
            st.session_state[key] = default


_init_session_state()


# ---------------------------------------------------------------------------
# Step 3: Wire navigation pages
# ---------------------------------------------------------------------------
_PAGES = [
    st.Page("pages/01_🌍_Observatory.py",        title=T("nav_observatory"),   icon="🌍", url_path="observatory"),
    st.Page("pages/02_📁_Workspace.py",          title=T("nav_workspace"),     icon="📁", url_path="workspace"),
    st.Page("pages/03_🔬_Sequence_Refinery.py",  title=T("nav_refinery"),      icon="🔬", url_path="refinery"),
    st.Page("pages/04_🧬_Molecular_Timeline.py", title=T("nav_timeline"),      icon="🧬", url_path="timeline"),
    st.Page("pages/05_📊_Analytics.py",          title=T("nav_analytics"),     icon="📊", url_path="analytics"),
    st.Page("pages/06_📋_Export.py",             title=T("nav_export"),        icon="📋", url_path="export"),
    st.Page("pages/07_📚_Documentation.py",      title=T("nav_documentation"), icon="📚", url_path="documentation"),
]

pg = st.navigation(_PAGES)


# ---------------------------------------------------------------------------
# CSS Theme constants (adapted from fasta_analysis_app_final.py)
# ---------------------------------------------------------------------------
_LIGHT_CSS = """
<style>
/* ── Typography: only html/body — never override Streamlit icon spans ── */
html, body {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}
p, label, .stMarkdown, .stCaption, .stText,
[data-testid="stMarkdownContainer"] {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}

/* ── Sidebar background ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #0c4a6e 100%) !important;
    padding: 1rem;
}

/* ── Sidebar text — targeted, never wildcard * ── */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stText"],
[data-testid="stSidebar"] [data-testid="stCaption"] {
    color: #cbd5e1 !important;
    font-size: 0.88rem;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 { color: #bae6fd !important; }
[data-testid="stSidebar"] hr { border-color: #1e40af !important; }

/* ── Sidebar selectbox / radio labels ── */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label {
    color: #e0f2fe !important;
    font-weight: 600;
}

/* ── Sidebar selectbox dropdown text ── */
[data-testid="stSidebar"] [data-testid="stSelectbox"] div[data-baseweb="select"] div {
    color: #0c4a6e !important;
}

/* ── Sidebar buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255, 255, 255, 0.15) !important;
    color: #e0f2fe !important;
    border: 1px solid rgba(255, 255, 255, 0.35) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255, 255, 255, 0.28) !important;
    border-color: rgba(255, 255, 255, 0.60) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button:active,
[data-testid="stSidebar"] .stButton > button:focus {
    background-color: rgba(255, 255, 255, 0.38) !important;
    box-shadow: 0 0 0 2px #7dd3fc !important;
    color: #ffffff !important;
}
/* Primary buttons inside sidebar */
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, #0369a1 0%, #0891b2 100%) !important;
    color: #ffffff !important;
    border: none !important;
}

/* ── Sidebar download button ── */
[data-testid="stSidebar"] .stDownloadButton > button {
    background-color: rgba(255, 255, 255, 0.10) !important;
    color: #7dd3fc !important;
    border: 1.5px solid #38bdf8 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background-color: rgba(56, 189, 248, 0.20) !important;
    color: #ffffff !important;
}

/* ── Sidebar metrics ── */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.12) !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.8rem !important;
    box-shadow: none !important;
}
/* stMetricLabel — target container AND its nested p/div/span to beat the general p-rule (0,1,1) */
[data-testid="stSidebar"] [data-testid="stMetricLabel"],
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p,
[data-testid="stSidebar"] [data-testid="stMetricLabel"] div,
[data-testid="stSidebar"] [data-testid="stMetricLabel"] span {
    color: #bae6fd !important; font-size: 0.82rem !important; font-weight: 600 !important;
}
/* stMetricValue — same pattern */
[data-testid="stSidebar"] [data-testid="stMetricValue"],
[data-testid="stSidebar"] [data-testid="stMetricValue"] p,
[data-testid="stSidebar"] [data-testid="stMetricValue"] div,
[data-testid="stSidebar"] [data-testid="stMetricValue"] span {
    color: #ffffff !important; font-weight: 700 !important; font-size: 1.1rem !important;
}
/* ── Section heading bold/strong: override general p-rule bleed (0,2,1 > 0,1,1) ── */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] b,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
    color: #ffffff !important; font-size: 0.9rem !important;
}
/* ── Page link text: beat the general p-rule ── */
[data-testid="stSidebar"] [data-testid="stPageLink"] p,
[data-testid="stSidebar"] [data-testid="stPageLink"] span {
    color: #e0f2fe !important; font-weight: 700 !important; font-size: 0.9rem !important;
}

/* ── Main content metrics ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
    padding: 0.9rem 1.1rem;
    border-radius: 12px;
    border-left: 4px solid #0ea5e9;
    box-shadow: 0 2px 10px rgba(3,105,161,0.10);
}
[data-testid="metric-container"] > div:first-child { color: #64748b !important; font-size: 0.82rem; }
[data-testid="metric-container"] > div:last-child  { color: #0c4a6e !important; font-weight: 700; }

/* ── Primary buttons (main area) ── */
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, #0369a1 0%, #0891b2 100%) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(3,105,161,0.30) !important;
    transition: all 0.18s ease !important;
}
[data-testid="stBaseButton-primary"]:hover {
    transform: translateY(-1px) !important;
    box-shadow: 0 4px 16px rgba(3,105,161,0.45) !important;
}

/* ── Download buttons (main area) ── */
.stDownloadButton > button {
    border-radius: 8px !important;
    border: 1.5px solid #0ea5e9 !important;
    color: #0369a1 !important; font-weight: 500 !important;
    transition: all 0.15s ease !important;
}
.stDownloadButton > button:hover { background: #e0f2fe !important; border-color: #0369a1 !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid #e2e8f0 !important;
    box-shadow: 0 1px 4px rgba(0,0,0,0.05) !important;
}

hr { border-color: #e2e8f0 !important; }
[data-testid="stDataFrame"] thead th {
    background: #f1f5f9 !important; color: #1e3a8a !important; font-weight: 600 !important;
}

/* ── Hide built-in stSidebarNav (replaced by manual st.page_link() in _render_sidebar) ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Manual nav links (st.page_link) — bold white, hover highlight ── */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    font-weight: 700 !important;
    color: #e0f2fe !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.4rem !important;
    padding: 0.35rem 0.6rem !important;
    border-radius: 8px !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    margin-bottom: 2px !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(255,255,255,0.15) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] p {
    font-weight: 700 !important;
    color: #e0f2fe !important;
}

/* ── Radio/checkbox contrast on dark sidebar ── */
[data-testid="stSidebar"] [data-baseweb="radio"] label p { color: #e0f2fe !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label div:first-child {
    border-color: rgba(125,211,252,0.7) !important;
}
</style>
"""

_DARK_CSS = """
<style>
/* ── Typography: only html/body — never override Streamlit icon spans ── */
html, body {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}
p, label, .stMarkdown, .stCaption, .stText,
[data-testid="stMarkdownContainer"] {
    font-family: 'Inter', 'Segoe UI', Arial, sans-serif;
}

.stApp { background: #0f172a !important; color: #e2e8f0 !important; }

/* ── Sidebar background ── */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #020617 0%, #0f172a 100%) !important;
    padding: 1rem;
}

/* ── Sidebar text — targeted, never wildcard * ── */
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] .stMarkdown,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"],
[data-testid="stSidebar"] [data-testid="stText"],
[data-testid="stSidebar"] [data-testid="stCaption"] {
    color: #94a3b8 !important;
    font-size: 0.88rem;
}
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3,
[data-testid="stSidebar"] h4 { color: #93c5fd !important; }
[data-testid="stSidebar"] hr { border-color: #1e293b !important; }

/* ── Sidebar selectbox / radio / checkbox labels ── */
[data-testid="stSidebar"] .stSelectbox label,
[data-testid="stSidebar"] .stRadio label,
[data-testid="stSidebar"] .stCheckbox label {
    color: #e0f2fe !important;
    font-weight: 600;
}

/* ── Sidebar buttons ── */
[data-testid="stSidebar"] .stButton > button {
    background-color: rgba(255, 255, 255, 0.12) !important;
    color: #cbd5e1 !important;
    border: 1px solid rgba(255, 255, 255, 0.25) !important;
    border-radius: 8px !important;
    font-weight: 600 !important;
    transition: all 0.18s ease !important;
}
[data-testid="stSidebar"] .stButton > button:hover {
    background-color: rgba(255, 255, 255, 0.22) !important;
    border-color: rgba(255, 255, 255, 0.50) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] .stButton > button:active,
[data-testid="stSidebar"] .stButton > button:focus {
    background-color: rgba(255, 255, 255, 0.30) !important;
    box-shadow: 0 0 0 2px #60a5fa !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, #1d4ed8 0%, #0891b2 100%) !important;
    color: #ffffff !important;
    border: none !important;
}

/* ── Sidebar download button ── */
[data-testid="stSidebar"] .stDownloadButton > button {
    background-color: rgba(255, 255, 255, 0.08) !important;
    color: #7dd3fc !important;
    border: 1.5px solid #38bdf8 !important;
    border-radius: 8px !important;
    font-weight: 500 !important;
}
[data-testid="stSidebar"] .stDownloadButton > button:hover {
    background-color: rgba(56, 189, 248, 0.18) !important;
    color: #ffffff !important;
}

/* ── Sidebar metrics ── */
[data-testid="stSidebar"] [data-testid="stMetric"] {
    background: rgba(255, 255, 255, 0.08) !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 10px !important;
    padding: 0.6rem 0.8rem !important;
    box-shadow: none !important;
}
/* stMetricLabel — target container AND nested p/div/span to beat general p-rule (0,1,1) */
[data-testid="stSidebar"] [data-testid="stMetricLabel"],
[data-testid="stSidebar"] [data-testid="stMetricLabel"] p,
[data-testid="stSidebar"] [data-testid="stMetricLabel"] div,
[data-testid="stSidebar"] [data-testid="stMetricLabel"] span {
    color: #94a3b8 !important; font-size: 0.82rem !important; font-weight: 600 !important;
}
/* stMetricValue — same pattern */
[data-testid="stSidebar"] [data-testid="stMetricValue"],
[data-testid="stSidebar"] [data-testid="stMetricValue"] p,
[data-testid="stSidebar"] [data-testid="stMetricValue"] div,
[data-testid="stSidebar"] [data-testid="stMetricValue"] span {
    color: #7dd3fc !important; font-weight: 700 !important; font-size: 1.1rem !important;
}
/* ── Section heading bold/strong: override general p-rule bleed (0,2,1 > 0,1,1) ── */
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] b,
[data-testid="stSidebar"] [data-testid="stMarkdownContainer"] strong {
    color: #ffffff !important; font-size: 0.9rem !important;
}
/* ── Page link text: beat the general p-rule ── */
[data-testid="stSidebar"] [data-testid="stPageLink"] p,
[data-testid="stSidebar"] [data-testid="stPageLink"] span {
    color: #bae6fd !important; font-weight: 700 !important; font-size: 0.9rem !important;
}

/* ── Main content metrics ── */
[data-testid="stMetric"] {
    background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%) !important;
    border-left: 4px solid #38bdf8 !important;
    border-radius: 12px !important;
    box-shadow: 0 2px 10px rgba(0,0,0,0.40) !important;
}
[data-testid="metric-container"] > div:first-child { color: #94a3b8 !important; }
[data-testid="metric-container"] > div:last-child  { color: #7dd3fc !important; }

/* ── Primary buttons (main area) ── */
[data-testid="stBaseButton-primary"] {
    background: linear-gradient(90deg, #1d4ed8 0%, #0891b2 100%) !important;
    border: none !important; border-radius: 8px !important;
    font-weight: 600 !important;
    box-shadow: 0 2px 8px rgba(29,78,216,0.40) !important;
}

/* ── Download buttons (main area) ── */
.stDownloadButton > button {
    border-radius: 8px !important;
    border: 1.5px solid #38bdf8 !important;
    color: #7dd3fc !important; font-weight: 500 !important;
}
.stDownloadButton > button:hover { background: #1e293b !important; }

/* ── Expanders ── */
[data-testid="stExpander"] {
    border-radius: 10px !important;
    border: 1px solid #1e293b !important;
    background: #1e293b !important;
}

hr { border-color: #1e293b !important; }
[data-testid="stDataFrame"] thead th {
    background: #1e293b !important; color: #93c5fd !important; font-weight: 600 !important;
}

/* ── Hide built-in stSidebarNav (replaced by manual st.page_link() in _render_sidebar) ── */
[data-testid="stSidebarNav"] { display: none !important; }

/* ── Manual nav links (st.page_link) — bold white, hover highlight ── */
[data-testid="stSidebar"] [data-testid="stPageLink"] a {
    font-weight: 700 !important;
    color: #bae6fd !important;
    text-decoration: none !important;
    display: flex !important;
    align-items: center !important;
    gap: 0.4rem !important;
    padding: 0.35rem 0.6rem !important;
    border-radius: 8px !important;
    transition: background 0.15s ease, color 0.15s ease !important;
    margin-bottom: 2px !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] a:hover {
    background: rgba(56,189,248,0.18) !important;
    color: #ffffff !important;
}
[data-testid="stSidebar"] [data-testid="stPageLink"] p {
    font-weight: 700 !important;
    color: #bae6fd !important;
}

/* ── Radio/checkbox contrast on dark sidebar ── */
[data-testid="stSidebar"] [data-baseweb="radio"] label p { color: #bae6fd !important; }
[data-testid="stSidebar"] div[role="radiogroup"] label div:first-child {
    border-color: rgba(56,189,248,0.7) !important;
}
</style>
"""


# ---------------------------------------------------------------------------
# Step 4: Render persistent sidebar
# ---------------------------------------------------------------------------
def _render_sidebar() -> None:
    """Persistent sidebar: branding → lang/theme → nav → filters → dataset status → actions."""
    with st.sidebar:
        # ── Logo ─────────────────────────────────────────────────────────────
        try:
            st.image("assets/Viral_sift_logo.png", use_container_width=True)
        except Exception:
            pass  # Silently skip if logo not found

        # ── App branding — very top, above all controls ──────────────────────
        st.markdown(f"## 🧬 {T('app_title')}")
        st.markdown(f"<span style='color:#7dd3fc;font-size:0.85rem;font-style:italic'>{T('app_subtitle')}</span>", unsafe_allow_html=True)

        st.divider()

        # ── Language — bold white label + collapsed widget label ────────────
        st.markdown(f"<b style='color:#ffffff;font-size:0.9rem'>{T('sidebar_language')}</b>", unsafe_allow_html=True)
        _lang_map = {
            "🇬🇧 English":  "en",
            "🇷🇺 Русский":  "ru",
            "🇫🇷 Français": "fr",
            "🇪🇸 Español":  "es",
            "🇨🇳 中文":     "zh",
            "🇸🇦 العربية":  "ar",
        }
        _current = st.session_state.get("language", "en")
        _lang_opts = list(_lang_map.keys())
        _reverse_map = {v: k for k, v in _lang_map.items()}
        _current_label = _reverse_map.get(_current, _lang_opts[0])
        _selected = st.selectbox(
            T("sidebar_language"),
            options=_lang_opts,
            index=_lang_opts.index(_current_label) if _current_label in _lang_opts else 0,
            key="language_selector",
            label_visibility="collapsed",
        )
        if _lang_map[_selected] != _current:
            st.session_state["language"] = _lang_map[_selected]
            st.rerun()

        # ── Theme — Light / Dark / 🔄 Auto (time-based) ────────────────────
        st.markdown(f"<b style='color:#ffffff;font-size:0.9rem'>{T('sidebar_theme')}</b>", unsafe_allow_html=True)
        _current_theme = st.session_state.get("theme", "light")
        _hour_now = pd.Timestamp.now().hour
        _auto_icon  = "🌙" if (_hour_now < 8 or _hour_now >= 20) else "☀️"
        _auto_lbl   = f"{T('theme_auto')} ({_auto_icon} {pd.Timestamp.now().strftime('%H:%M')})"
        _theme_opts = [T("theme_light"), T("theme_dark"), _auto_lbl]
        _theme_idx  = 1 if _current_theme == "dark" else (2 if _current_theme == "auto" else 0)
        _theme_selected = st.radio(
            T("sidebar_theme"),
            options=_theme_opts,
            index=_theme_idx,
            horizontal=False,
            key="theme_selector",
            label_visibility="collapsed",
        )
        if _theme_selected == T("theme_light"):
            _new_theme = "light"
        elif _theme_selected == T("theme_dark"):
            _new_theme = "dark"
        else:
            _new_theme = "auto"
        if _new_theme != _current_theme:
            st.session_state["theme"] = _new_theme
            st.rerun()

        st.divider()

        # ── Data Mode — Current (filtered) vs Original (pre-filter) ─────────
        st.markdown(f"<b style='color:#ffffff;font-size:0.9rem'>{T('sidebar_data_mode')}</b>", unsafe_allow_html=True)
        _cur_mode  = st.session_state.get("data_mode", "current")
        _mode_opts = [T("sidebar_mode_current"), T("sidebar_mode_original")]
        _mode_sel  = st.radio(
            T("sidebar_data_mode"),
            options=_mode_opts,
            index=1 if _cur_mode == "original" else 0,
            key="data_mode_radio",
            label_visibility="collapsed",
            help=T("sidebar_mode_current_help") if _cur_mode == "current" else T("sidebar_mode_original_help"),
        )
        _new_mode = "original" if _mode_sel == T("sidebar_mode_original") else "current"
        if _new_mode != _cur_mode:
            st.session_state["data_mode"] = _new_mode
            st.rerun()

        st.divider()

        # ── Navigation — bold page links ABOVE Global Filters ────────────────
        st.markdown(f"<b style='color:#ffffff;font-size:0.9rem'>{T('sidebar_navigation')}</b>", unsafe_allow_html=True)
        st.page_link("pages/01_🌍_Observatory.py",        label=f"🌍 {T('nav_observatory')}")
        st.page_link("pages/02_📁_Workspace.py",          label=f"📁 {T('nav_workspace')}")
        st.page_link("pages/03_🔬_Sequence_Refinery.py",  label=f"🔬 {T('nav_refinery')}")
        st.page_link("pages/04_🧬_Molecular_Timeline.py", label=f"🧬 {T('nav_timeline')}")
        st.page_link("pages/05_📊_Analytics.py",          label=f"📊 {T('nav_analytics')}")
        st.page_link("pages/06_📋_Export.py",             label=f"📋 {T('nav_export')}")
        st.page_link("pages/07_📚_Documentation.py",      label=f"📚 {T('nav_documentation')}")

        st.divider()

        # --- Global Filter Badge ---
        _active_filters = st.session_state.get("global_filters", [])
        _filter_count = len(_active_filters)
        with st.expander(T("sidebar_global_filters", count=_filter_count), expanded=False):
            if _active_filters:
                for _f in _active_filters:
                    st.write(f"• {_f.get('field', '')} {_f.get('operator', '')} {_f.get('value', '')}")
                if st.button(T("sidebar_clear_filters"), use_container_width=True):
                    st.session_state["global_filters"] = []
                    st.rerun()
            else:
                st.caption(T("sidebar_no_filters"))

        st.divider()

        # --- Dataset Status ---
        st.markdown(f"**{T('sidebar_dataset_status')}**")
        _active_df = st.session_state.get("active_df", pd.DataFrame())
        _filtered_df = st.session_state.get("filtered_df", pd.DataFrame())

        if not _active_df.empty:
            st.metric(T("sidebar_active_seqs"), f"{len(_active_df):,}")
            if not _filtered_df.empty:
                st.metric(T("sidebar_filtered_seqs"), f"{len(_filtered_df):,}")
            if "sequence_length" in _active_df.columns:
                st.metric(
                    T("sidebar_avg_length"),
                    f"{_active_df['sequence_length'].mean():.0f} bp",
                )
            # Source file count — derived from last activation log
            _all_logs = st.session_state.get("action_logs", [])
            _last_act = next(
                (lg for lg in reversed(_all_logs) if lg.get("action") == "activate"),
                None,
            )
            if _last_act:
                _n_src = len(_last_act.get("files", []))
                if _n_src > 1:
                    st.caption(
                        T(
                            "sidebar_sources_merged",
                            count=_n_src,
                            timeline=T("nav_timeline"),
                        )
                    )
                else:
                    st.caption(T("sidebar_one_source"))
            if len(_active_df) > 10_000:
                st.warning(T("sidebar_large_dataset_warning"))
        else:
            st.info(T("sidebar_no_dataset"))

        st.divider()

        # --- Export filename prefix ---
        _cur_pfx = st.session_state.get("export_prefix", "virsift")
        _new_pfx = st.text_input(
            T("sidebar_export_prefix_label"),
            value=_cur_pfx,
            max_chars=40,
            help=T("sidebar_export_prefix_help"),
            key="export_prefix_input",
        )
        st.caption(f"↵ {T('sidebar_export_prefix_enter_hint')}")
        if _new_pfx and _new_pfx.strip():
            # Sanitise: keep alphanumeric, hyphen, underscore only
            import re as _re
            _safe = _re.sub(r"[^\w\-]", "_", _new_pfx.strip())
            st.session_state["export_prefix"] = _safe
        else:
            st.session_state["export_prefix"] = "virsift"

        # --- Quick Actions ---
        st.markdown(f"**{T('sidebar_quick_actions')}**")

        # Quick FASTA export (only when filtered data is available)
        if not _filtered_df.empty:
            try:
                from utils.gisaid_parser import convert_df_to_fasta
                _fasta_out = convert_df_to_fasta(_filtered_df)
                _pfx = st.session_state.get("export_prefix", "virsift") or "virsift"
                st.download_button(
                    label=T("download_fasta_label", count=len(_filtered_df)),
                    data=_fasta_out,
                    file_name=f"{_pfx}_filtered.fasta",
                    mime="text/plain",
                    use_container_width=True,
                    type="primary",
                    help=T("download_tooltip_fasta"),
                )
            except Exception:
                pass  # Parser not yet implemented — silently skip

        if st.button(T("sidebar_reset_session"), use_container_width=True):
            for _key in list(st.session_state.keys()):
                del st.session_state[_key]
            st.rerun()

        pass  # brand is rendered as a fixed-bottom CSS strip (see below)


# ---------------------------------------------------------------------------
# Step 4b: Inject CSS theme
# ---------------------------------------------------------------------------
_stored_theme = st.session_state.get("theme", "light")
if _stored_theme == "auto":
    _hour_now = pd.Timestamp.now().hour
    _active_theme = "dark" if (_hour_now < 8 or _hour_now >= 20) else "light"
else:
    _active_theme = _stored_theme
st.markdown(_DARK_CSS if _active_theme == "dark" else _LIGHT_CSS, unsafe_allow_html=True)

_render_sidebar()

# ---------------------------------------------------------------------------
# Step 4c: Fixed-bottom sidebar brand strip + page footer
# ---------------------------------------------------------------------------
_brand_text = f"{T('app_title')} {T('app_version')} · {T('app_arch')}"
_footer_text = f"{T('app_title')} {T('app_version')} — {T('app_tagline')}"
st.markdown(f"""
<style>
/* ── Fixed-bottom sidebar brand ─────────────────────────────────────── */
.sidebar-brand-strip {{
    position: fixed;
    bottom: 0;
    left: 0;
    width: 21rem;
    padding: .45rem 1rem .5rem;
    font-size: .7rem;
    color: #94a3b8;
    z-index: 9999;
    pointer-events: none;
    background: var(--secondary-background-color, rgba(240,242,246,0.95));
    border-top: 1px solid rgba(148,163,184,.15);
}}
/* ── Page footer ─────────────────────────────────────────────────────── */
.page-footer-strip {{
    position: fixed;
    bottom: 0;
    left: 22rem;
    padding: .3rem .9rem;
    font-size: .72rem;
    font-weight: 700;
    color: #64748b;
    z-index: 9990;
    pointer-events: none;
}}
</style>
<div class="sidebar-brand-strip">{_brand_text}</div>
<div class="page-footer-strip">{_footer_text}</div>
""", unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# Step 5: Run the current page
# ---------------------------------------------------------------------------
pg.run()
