# -*- coding: utf-8 -*-
"""
utils/ui_helpers.py

Shared Streamlit rendering helpers used across pages. Kept separate from the
pure-logic utils/ modules (this one DOES depend on Streamlit) so pages don't
each reimplement the same top-N/"show all"/drill-down table pattern.
"""

import pandas as pd
import streamlit as st


def humanize_field(col: str) -> str:
    """Turn a raw internal column/field name into a readable fallback label.

    Used as the LAST resort when no translated label exists for a field —
    "_year" -> "Year", "sequence_clone" -> "Sequence Clone", "host_tier" ->
    "Host Tier" — so an untranslated or newly-added internal identifier never
    leaks into the UI as a raw snake_case/underscore-prefixed string. This is
    a fallback, not a substitute for a real T() label: prefer an explicit
    translation key wherever one exists, and use this only as the `.get(col,
    humanize_field(col))` default so nothing is ever shown un-prettified.
    """
    return col.lstrip("_").replace("_", " ").strip().title()


_TIER_SLUGS = {
    "Wild Birds": "wild_birds",
    "Intermediate": "intermediate",
    "Poultry": "poultry",
    "Unclassified": "unclassified",
}


def render_host_tier_glossary(expanded: bool = False) -> None:
    """Info panel explaining the Wild Birds / Intermediate / Poultry tiers.

    Rendered wherever the host_tier filter dimension is exposed, so the
    surveillance rationale is never just an unexplained dropdown value.
    Translated copy lives in assets/translations/*.json (host_tier_label_*
    / host_tier_body_*); utils/host_tier_classifier.py's TIER_GLOSSARY is
    the canonical English source those keys were derived from.
    """
    from utils.minimal_i18n import T
    with st.expander(f"ℹ️ {T('host_tier_glossary_header')}", expanded=expanded):
        for tier, slug in _TIER_SLUGS.items():
            st.markdown(f"**{T(f'host_tier_label_{slug}')}**")
            st.caption(T(f"host_tier_body_{slug}"))


def slider_with_number_input(
    label: str,
    min_value: int,
    max_value: int,
    default: int,
    step: int = 1,
    help: str | None = None,
    key_prefix: str = "swn",
) -> int:
    """Render a slider paired with a synced numeric entry box.

    Either control can set the value; changing one updates the other via
    session_state on_change callbacks, so the returned value always reflects
    whichever widget the user touched most recently.
    """
    slider_key = f"{key_prefix}_slider"
    num_key = f"{key_prefix}_num"

    if slider_key not in st.session_state:
        st.session_state[slider_key] = default
    if num_key not in st.session_state:
        st.session_state[num_key] = st.session_state[slider_key]

    def _sync_from_slider():
        st.session_state[num_key] = st.session_state[slider_key]

    def _sync_from_number():
        v = max(min_value, min(max_value, st.session_state[num_key]))
        st.session_state[slider_key] = v
        st.session_state[num_key] = v

    sc, nc = st.columns([4, 1])
    with sc:
        st.slider(
            label, min_value=min_value, max_value=max_value, step=step,
            help=help, key=slider_key, on_change=_sync_from_slider,
        )
    with nc:
        st.number_input(
            label, min_value=min_value, max_value=max_value, step=step,
            key=num_key, on_change=_sync_from_number, label_visibility="collapsed",
        )
    return st.session_state[slider_key]


def render_top_n_table(
    df: pd.DataFrame,
    column: str,
    label: str,
    default_n: int = 8,
    drilldown_column: str | None = None,
    key_prefix: str = "",
) -> None:
    """Render a top-N value_counts() table with a "show all" escape hatch.

    Always shows the top `default_n` rows. Below it, an expander reveals the
    FULL value_counts() breakdown (not capped) plus a CSV download — so a
    category beyond the top-N is never simply invisible.

    If `drilldown_column` is given (e.g. drilling `host` -> `host_species`),
    also renders a compact selectbox letting the user pick one top-level
    category and see its sub-breakdown by the drilldown column. Chosen over
    per-row nested expanders because it composes cleanly inside st.columns()
    without breaking narrow-column layouts (e.g. Observatory's 3-column Row 3).

    Args:
        df: source DataFrame.
        column: column to count.
        label: human-readable (already-translated) label for headers/captions.
        default_n: rows shown in the always-visible top table.
        drilldown_column: optional second column to drill into per top-level value.
        key_prefix: unique prefix for widget keys (avoid collisions across calls).
    """
    if column not in df.columns:
        return

    counts = df[column].dropna()
    if counts.empty:
        return

    vc = counts.value_counts()
    top = vc.head(default_n)
    top_df = pd.DataFrame({label: top.index.tolist(), "Count": top.values.tolist()})
    st.dataframe(top_df, use_container_width=True, hide_index=True)

    n_unique = len(vc)
    if n_unique > default_n:
        with st.expander(f"Show all {n_unique} {label} values"):
            full_df = pd.DataFrame({label: vc.index.tolist(), "Count": vc.values.tolist()})
            st.dataframe(full_df, use_container_width=True, hide_index=True)
            st.download_button(
                label=f"⬇ Download full {label} breakdown (CSV)",
                data=full_df.to_csv(index=False).encode("utf-8"),
                file_name=f"{key_prefix or column}_full_breakdown.csv",
                mime="text/csv",
                key=f"{key_prefix}_{column}_dl",
                use_container_width=True,
            )

    if drilldown_column and drilldown_column in df.columns:
        # Every category is selectable, not just the visible top-N rows —
        # drilling into a category outside the top-N is exactly the case
        # the "show all" expander above exists for; the drill-down shouldn't
        # be limited to less than that.
        drill_options = vc.index.tolist()
        if drill_options:
            chosen = st.selectbox(
                f"Drill into {label}:",
                options=drill_options,
                key=f"{key_prefix}_{column}_drill",
            )
            cat_rows = df.loc[df[column] == chosen]
            sub = cat_rows[drilldown_column].dropna()
            if not sub.empty:
                sub_vc = sub.value_counts()
                sub_df = pd.DataFrame({
                    drilldown_column: sub_vc.index.tolist(),
                    "Count": sub_vc.values.tolist(),
                })
                st.caption(f"{chosen} → {drilldown_column} breakdown ({len(sub_vc)} distinct)")
                st.dataframe(sub_df, use_container_width=True, hide_index=True)

            # Scan/download the actual underlying records for this category,
            # not just its counts — e.g. see every isolate classified as
            # "Wild Birds", not only how many there are.
            with st.expander(f"🔍 View {len(cat_rows):,} records where {label} = \"{chosen}\""):
                _preview_cols = [c for c in [
                    "isolate", "subtype_clean", "segment", "host", "host_species",
                    "host_tier", "location", "collection_date", "clade", "accession",
                ] if c in cat_rows.columns]
                st.dataframe(
                    cat_rows[_preview_cols] if _preview_cols else cat_rows,
                    use_container_width=True, hide_index=True, height=320,
                )
                _dl_cols = [c for c in cat_rows.columns if c != "sequence"]
                st.download_button(
                    label=f"⬇ Download these {len(cat_rows):,} records (CSV)",
                    data=cat_rows[_dl_cols].to_csv(index=False).encode("utf-8"),
                    file_name=f"{key_prefix or column}_{column}_{chosen}_records.csv".replace(" ", "_"),
                    mime="text/csv",
                    key=f"{key_prefix}_{column}_{chosen}_records_dl",
                    use_container_width=True,
                )
