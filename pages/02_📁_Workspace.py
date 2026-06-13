# -*- coding: utf-8 -*-
"""
pages/02_📁_Workspace.py — Data Intake

CRITICAL STATE RULE:
  session_state['active_df'] is written HERE and ONLY HERE (Activate button).
  No other page or utility may write to active_df.
  All downstream filtering writes to session_state['filtered_df'] only.
"""

import pandas as pd
import requests
import streamlit as st

from utils.gisaid_parser import decompress_if_needed, parse_gisaid_fasta
from utils.minimal_i18n import T

# Size thresholds (bytes)
_WARN_BYTES = 50 * 1024 * 1024   # 50 MB  — soft warning, still processes
_HARD_BYTES = 200 * 1024 * 1024  # 200 MB — hard block (matches config.toml maxUploadSize)

# Colab availability — non-fatal if running outside Google Colab
try:
    from google.colab import drive as _colab_drive
    COLAB_AVAILABLE = True
except ImportError:
    COLAB_AVAILABLE = False


# ---------------------------------------------------------------------------
# Page header
# ---------------------------------------------------------------------------
st.title(f"📁 {T('nav_workspace')}")

# ---------------------------------------------------------------------------
# Section 1 — File Upload
# ---------------------------------------------------------------------------
st.subheader(T("upload_header"))
st.caption(T("upload_instruction"))

uploaded_files = st.file_uploader(
    label=T("upload_instruction"),
    type=["fasta", "fa", "fas", "fna", "txt", "gz", "zip", "aln-fasta"],
    accept_multiple_files=True,
    key="file_uploader",
    label_visibility="collapsed",
)

# Explain where uploaded files are processed in local and hosted deployments.
st.caption(T("footer_hosting_disclaimer"))

# --- Parse any newly uploaded files ---
if uploaded_files:
    existing_names = {rf["name"] for rf in st.session_state.get("raw_files", [])}
    for uf in uploaded_files:
        if uf.name in existing_names:
            continue  # Already parsed — @st.cache_data handles repeat calls anyway
        # ── Size validation ──────────────────────────────────────────────
        _sz = getattr(uf, "size", None)
        if _sz is not None:
            if _sz > _HARD_BYTES:
                st.error(T("upload_file_too_large",
                           mb=f"{_sz / 1024 / 1024:.0f}",
                           max_mb=int(_HARD_BYTES / 1024 / 1024)))
                continue
            if _sz > _WARN_BYTES:
                st.warning(T("upload_file_large_warn",
                             mb=f"{_sz / 1024 / 1024:.0f}"))
        with st.spinner(f"Parsing `{uf.name}`…"):
            raw_bytes = uf.read()

            # ── ZIP: expand each member as its own raw_files entry (batch mode) ──
            if uf.name.lower().endswith(".zip"):
                from utils.gisaid_parser import decompress_zip_to_files
                import pathlib as _pl
                _zip_members = decompress_zip_to_files(raw_bytes)
                if not _zip_members:
                    st.error(T("upload_zip_no_fasta", fname=uf.name))
                    continue
                _zip_added = 0
                for _member_path, _member_content in _zip_members.items():
                    _short = _pl.Path(_member_path).name  # strip internal folder
                    if _short in existing_names:
                        continue
                    _parsed, _pt = parse_gisaid_fasta(_member_content, _short)
                    if not _parsed:
                        continue
                    st.session_state["raw_files"].append({
                        "name":        _short,
                        "parsed":      _parsed,
                        "parse_time":  _pt,
                        "n_sequences": len(_parsed),
                    })
                    existing_names.add(_short)
                    st.session_state["action_logs"].append({
                        "action":    "parse",
                        "file":      _short,
                        "sequences": len(_parsed),
                        "time_s":    round(_pt, 3),
                        "timestamp": pd.Timestamp.now().isoformat(),
                    })
                    _zip_added += 1
                if _zip_added:
                    st.success(T("workspace_zip_expanded", n=_zip_added, zip=uf.name))
                continue  # Skip single-file path below
            # ── Single FASTA / .gz ────────────────────────────────────────────────
            content = decompress_if_needed(raw_bytes, uf.name)
            parsed_list, parse_time = parse_gisaid_fasta(content, uf.name)

        if not parsed_list:
            st.error(f"No sequences found in `{uf.name}`. Check the file format.")
            continue

        st.session_state["raw_files"].append({
            "name":        uf.name,
            "parsed":      parsed_list,
            "parse_time":  parse_time,
            "n_sequences": len(parsed_list),
        })
        st.success(T("upload_parse_success", count=len(parsed_list), time=parse_time))
        st.session_state["action_logs"].append({
            "action":    "parse",
            "file":      uf.name,
            "sequences": len(parsed_list),
            "time_s":    round(parse_time, 3),
            "timestamp": pd.Timestamp.now().isoformat(),
        })

# ---------------------------------------------------------------------------
# Section 2 — Loaded Files Table
# ---------------------------------------------------------------------------
raw_files: list = st.session_state.get("raw_files", [])

if not raw_files:
    st.info(T("upload_no_files"))
else:
    st.divider()
    st.subheader(T("workspace_loaded_files"))

    # ── Build enhanced per-file stats table ──────────────────────────────────
    def _file_row(rf: dict) -> dict:
        """Return a stats dict for one raw file entry."""
        mini = pd.DataFrame(rf["parsed"])
        n    = rf["n_sequences"]
        # Date range
        date_str = "—"
        if "collection_date" in mini.columns:
            dates = pd.to_datetime(mini["collection_date"], errors="coerce").dropna()
            if not dates.empty:
                date_str = f"{dates.min().strftime('%Y-%m')} → {dates.max().strftime('%Y-%m')}"
        # Unique subtypes
        n_sub = mini["subtype_clean"].nunique() if "subtype_clean" in mini.columns else "—"
        # Unique segments
        n_seg = mini["segment"].nunique() if "segment" in mini.columns else "—"
        return {
            "File":                       rf["name"],
            T("sidebar_active_seqs"):     f"{n:,}",
            T("workspace_file_subtypes"): n_sub,
            T("workspace_file_segments"): n_seg,
            T("workspace_file_date_range"): date_str,
            "Parse (s)":                  f"{rf['parse_time']:.2f}",
        }

    summary = pd.DataFrame([_file_row(rf) for rf in raw_files])
    st.dataframe(summary, use_container_width=True, hide_index=True)

    file_names = [rf["name"] for rf in raw_files]

    # Initialise multiselect state before quick-action buttons to avoid
    # "created with default but also set via Session State API" warning
    if "ws_file_multiselect" not in st.session_state:
        st.session_state["ws_file_multiselect"] = file_names[:1] if file_names else []

    # ── Batch quick-action row ────────────────────────────────────────────────
    _bq1, _bq2, _bq3 = st.columns([1, 1, 2])

    with _bq1:
        if st.button(T("workspace_select_all"), use_container_width=True,
                     key="ws_sel_all_btn"):
            st.session_state["ws_file_multiselect"] = file_names
            st.rerun()

    with _bq2:
        if st.button(T("workspace_clear_sel"), use_container_width=True,
                     key="ws_clr_btn"):
            st.session_state["ws_file_multiselect"] = []
            st.rerun()

    with _bq3:
        if st.button(
            T("workspace_activate_all_btn", n=len(raw_files)),
            type="primary",
            use_container_width=True,
            key="ws_activate_all_btn",
            help="Merges every loaded file into one active dataset without needing a selection.",
        ):
            with st.spinner(T("workspace_building_df")):
                dfs = [pd.DataFrame(rf["parsed"]) for rf in raw_files]
                merged = pd.concat(dfs, ignore_index=True)
            # THE ONLY PLACE active_df IS WRITTEN
            st.session_state["active_df"] = merged
            st.session_state["filtered_df"] = pd.DataFrame()
            st.session_state["action_logs"].append({
                "action":    "activate",
                "files":     file_names,
                "sequences": len(merged),
                "timestamp": pd.Timestamp.now().isoformat(),
            })
            st.success(T("workspace_activated_success",
                         n=len(merged), files=len(raw_files)))
            st.rerun()

    # ── File selection for activation / merge ────────────────────────────────
    selected = st.multiselect(
        T("workspace_select_activate"),
        options=file_names,
        key="ws_file_multiselect",
    )

    col_activate, col_remove = st.columns([3, 1])

    # --- Activate button (single write to active_df) ---
    with col_activate:
        activate_label = (
            T("upload_activate_button") if len(selected) == 1
            else T("upload_merge_button")
        )
        if st.button(activate_label, type="secondary",
                     disabled=not selected, use_container_width=True):
            selected_parsed = [
                rf["parsed"] for rf in raw_files if rf["name"] in selected
            ]
            with st.spinner(T("workspace_building_df")):
                dfs = [pd.DataFrame(p) for p in selected_parsed]
                merged = pd.concat(dfs, ignore_index=True) if len(dfs) > 1 else dfs[0]

            # THE ONLY PLACE active_df IS WRITTEN
            st.session_state["active_df"] = merged
            st.session_state["filtered_df"] = pd.DataFrame()  # Reset filters on new activation

            st.session_state["action_logs"].append({
                "action":    "activate",
                "files":     selected,
                "sequences": len(merged),
                "timestamp": pd.Timestamp.now().isoformat(),
            })
            st.success(T("workspace_activated_success", n=len(merged), files=len(selected)))
            st.rerun()

    # --- Remove file(s) from loaded list ---
    with col_remove:
        if st.button(T("workspace_remove_btn"), disabled=not selected, use_container_width=True):
            st.session_state["raw_files"] = [
                rf for rf in raw_files if rf["name"] not in selected
            ]
            st.rerun()

# ---------------------------------------------------------------------------
# Section 3 — Active Dataset Status
# ---------------------------------------------------------------------------
active_df: pd.DataFrame = st.session_state.get("active_df", pd.DataFrame())

if not active_df.empty:
    st.divider()
    st.subheader(T("workspace_active_dataset"))

    c1, c2, c3, c4 = st.columns(4)
    c1.metric(T("sidebar_active_seqs"), f"{len(active_df):,}")

    if "sequence_length" in active_df.columns:
        c2.metric(T("sidebar_avg_length"), f"{active_df['sequence_length'].mean():.0f} bp")

    if "collection_date" in active_df.columns:
        dates = pd.to_datetime(active_df["collection_date"], errors="coerce").dropna()
        if not dates.empty:
            c3.metric(T("workspace_earliest"), dates.min().strftime("%Y-%m-%d"))
            c4.metric(T("workspace_latest"),   dates.max().strftime("%Y-%m-%d"))

    # ── Top-N summary panels: Subtypes / Segments / Locations / Clades / Host Species ──
    # Build the ordered list of panels to display (skip columns that are all-null)
    _ws_panel_cfg = [
        ("subtype_clean", T("workspace_top_subtypes_label"), "🧬"),
        ("segment",       T("workspace_top_segments"),       "🧩"),
        ("location",      T("workspace_top_locations"),      "📍"),
        ("host_species",  T("workspace_top_host_species"),   "🦆"),
        ("clade_l1",      T("workspace_top_clades"),         "🌿"),
    ]
    _ws_panels = [
        (col, label, icon)
        for col, label, icon in _ws_panel_cfg
        if col in active_df.columns
        and active_df[col].replace("Unknown", pd.NA).notna().any()
    ]
    # Fall back to host (broad class) if host_species not available
    if len(_ws_panels) < 4 and "host" in active_df.columns:
        _ws_panels.append(("host", T("workspace_top_hosts"), "🐦"))

    if _ws_panels:
        for _row_start in range(0, len(_ws_panels), 2):
            _row_pair = _ws_panels[_row_start : _row_start + 2]
            _pcols = st.columns(len(_row_pair))
            for _ci, (_field, _label, _icon) in enumerate(_row_pair):
                with _pcols[_ci]:
                    _vc = (
                        active_df[_field]
                        .replace("Unknown", pd.NA)
                        .dropna()
                        .value_counts()
                        .head(5)
                        .reset_index()
                    )
                    _vc.columns = [_label, T("workspace_count")]
                    st.markdown(f"**{_icon} {_label}**")
                    st.dataframe(_vc, use_container_width=True, hide_index=True)

    if len(active_df) > 10_000:
        st.warning(T("sidebar_large_dataset_warning"))

    # --- URL Download ---
    with st.expander(T("workspace_url_expander")):
        url = st.text_input(T("workspace_url_input_label"), key="url_input")
        if st.button(T("workspace_url_fetch_btn"), disabled=not url):
            _blocked = False
            # ── HEAD check: get Content-Length before pulling the body ────
            try:
                _head = requests.head(url, timeout=10, allow_redirects=True)
                _cl = _head.headers.get("Content-Length")
                if _cl:
                    _remote_mb = int(_cl) / 1024 / 1024
                    if _remote_mb > _HARD_BYTES / 1024 / 1024:
                        st.error(T("upload_url_too_large",
                                   mb=f"{_remote_mb:.0f}",
                                   max_mb=int(_HARD_BYTES / 1024 / 1024)))
                        _blocked = True
                    elif _remote_mb > _WARN_BYTES / 1024 / 1024:
                        st.warning(T("upload_url_large_warn",
                                     mb=f"{_remote_mb:.0f}"))
            except Exception:
                pass  # HEAD unsupported — proceed; GET timeout guards the rest

            if not _blocked:
                try:
                    with st.spinner(f"Fetching {url}…"):
                        r = requests.get(url, timeout=60)
                        r.raise_for_status()
                        fname = url.split("/")[-1].split("?")[0] or "downloaded.fasta"
                        content = decompress_if_needed(r.content, fname)
                        parsed_list, parse_time = parse_gisaid_fasta(content, fname)
                    if parsed_list:
                        st.session_state["raw_files"].append({
                            "name":        fname,
                            "parsed":      parsed_list,
                            "parse_time":  parse_time,
                            "n_sequences": len(parsed_list),
                        })
                        st.success(T("upload_parse_success",
                                     count=len(parsed_list), time=parse_time))
                        st.rerun()
                    else:
                        st.error(T("workspace_url_no_seqs"))
                except Exception as e:
                    st.error(T("workspace_url_fetch_failed", error=e))

# ---------------------------------------------------------------------------
# Section 4 — Google Drive / Colab Integration (conditional)
# ---------------------------------------------------------------------------
if COLAB_AVAILABLE:
    st.divider()
    with st.expander(T("upload_colab_header")):
        st.info("Google Colab Drive detected. Mount your drive to access large FASTA files.")
        if st.button("Mount Google Drive"):
            try:
                _colab_drive.mount("/content/drive")
                st.success("Drive mounted at /content/drive")
            except Exception as e:
                st.error(f"Mount failed: {e}")
        drive_path = st.text_input("Path to FASTA file on Drive:",
                                   placeholder="/content/drive/MyDrive/sequences.fasta")
        if st.button("Load from Drive", disabled=not drive_path):
            try:
                with open(drive_path, "rb") as f:
                    raw_bytes = f.read()
                fname = drive_path.split("/")[-1]
                content = decompress_if_needed(raw_bytes, fname)
                parsed_list, parse_time = parse_gisaid_fasta(content, fname)
                if parsed_list:
                    st.session_state["raw_files"].append({
                        "name":        fname,
                        "parsed":      parsed_list,
                        "parse_time":  parse_time,
                        "n_sequences": len(parsed_list),
                    })
                    st.success(T("upload_parse_success", count=len(parsed_list), time=parse_time))
                    st.rerun()
                else:
                    st.error("No sequences found in that file.")
            except Exception as e:
                st.error(f"Drive load failed: {e}")

# ---------------------------------------------------------------------------
# Inter-page navigation
# ---------------------------------------------------------------------------
st.divider()
_ws_nav1, _ws_nav2 = st.columns(2)
try:
    _ws_nav1.page_link("pages/01_🌍_Observatory.py",
                       label=f"← 🌍 {T('nav_observatory')}",
                       use_container_width=True)
    _ws_nav2.page_link("pages/03_🔬_Sequence_Refinery.py",
                       label=f"🔬 {T('nav_refinery')} →",
                       use_container_width=True)
except AttributeError:
    _ws_nav1.markdown(f"[← 🌍 {T('nav_observatory')}](pages/01_🌍_Observatory.py)")
    _ws_nav2.markdown(f"[🔬 {T('nav_refinery')} →](pages/03_🔬_Sequence_Refinery.py)")
