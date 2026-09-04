# -*- coding: utf-8 -*-
"""
utils/name_normalizer.py

Shared canonicalization + content-sniffing helpers used by gisaid_parser.py
and the Header Converter tool (pages/03_🔬_Sequence_Refinery.py).

Core purpose: different labs submit the same host/accession inconsistently
in raw GISAID headers (mallard / Mallard_Duck / Mallard / Anas platyrhynchos
all naming the same animal; EPI_ISL_123 / EPI ISL 123 / EPI-ISL-123 all
naming the same accession). Left uncorrected, downstream phylogenetic tools
(Nextstrain, BEAST) read these as separate groups, inflating apparent host
diversity and silently breaking filters. Collapsing them to one canonical
form is a core VirSift responsibility, not cosmetic cleanup.

Pure logic layer — zero UI/Streamlit dependencies (mirrors utils/__init__.py
convention: importable without a running Streamlit session).
"""

import re

_SEP_RE = re.compile(r"[\s_\-]+")

# Redundant qualifier words that, when appended/prepended to an already-
# specific species token, should be stripped before re-attempting a lookup.
# e.g. "Mallard_Duck" -> strip "_duck" -> "mallard" (already canonical).
_REDUNDANT_QUALIFIERS = frozenset({"duck", "goose", "bird", "swan", "species", "sp"})

# Common Cyrillic host terms seen in real avian-flu surveillance data
# (VirSift already explicitly supports Cyrillic location names, e.g.
# Novosibirsk — the same data sources carry Cyrillic host terms too).
# Maps normalized Cyrillic token -> canonical English host-species/keyword.
_COMPOUND_LABEL_RE = re.compile(r"^(.*?)\(([A-Za-z][A-Za-z_\-\s\.]+)\)\s*$")

# Common-name synonyms that don't share a normalized-key match with any
# _SPECIES_COMMON_NAMES entry (so redundant-qualifier stripping alone can't
# merge them) — e.g. "turnstone" is a shorter form of the dictionary's
# "ruddy_turnstone", not "ruddy_turnstone" with an extra word appended.
# Checked before the qualifier-stripping step. Confirmed against real
# surveillance data where these exact fragments co-occurred as separate
# host_species categories for the same bird.
_COMMON_NAME_ALIASES: dict = {
    "turnstone":            "ruddy_turnstone",
    "northern_pintail":     "pintail",
    "northern_shoveler":    "shoveler",
    "eurasian_teal":        "common_teal",
    "teal":                 "common_teal",
    "european_wigeon":      "wigeon",
}

_MIXED_LANGUAGE_HOST_TERMS: dict = {
    "утка":        "duck",
    "дикая_утка":  "duck",
    "кряква":      "mallard",
    "гусь":        "goose",
    "лебедь":      "swan",
    "курица":      "chicken",
    "цыпленок":    "chicken",
    "индейка":     "turkey",
    "индюк":       "turkey",
    "дикая_птица": "wild_bird",
    "птица":       "bird",
    "чайка":       "gull",
    "голубь":      "pigeon",
    "свинья":      "pig",
    "хорек":       "ferret",
}


def _norm_key(s: str) -> str:
    """Collapse case + separator variance into one canonical matching key.

    "Mute Swan", "mute-swan", "mute _ swan", "Mute_Swan" all normalize to
    "mute_swan". This is the shared key used by every canonicalizer below.
    """
    if not s:
        return ""
    s = s.strip().lower()
    s = _SEP_RE.sub("_", s)
    return s.strip("_")


def canonicalize_host_species(raw: str, species_common_names: dict) -> str:
    """Collapse host-species token variants to one canonical label.

    Args:
        raw: the raw host-species token extracted from an isolate name
             (e.g. "Mallard_Duck", "Anas platyrhynchos", "mute - swan").
        species_common_names: gisaid_parser._SPECIES_COMMON_NAMES — passed
             in rather than imported to avoid a circular import (gisaid_parser
             imports this module).

    Resolution order:
      0. Compound "common name(scientific name)" label — e.g.
         "mallard(anas_platyrhynchos)" or "green_winged_teal(Anas crecca)".
         The parenthetical scientific name is authoritative (a controlled
         binomial beats a submitter's free-text common-name prefix, which
         may use a different regional convention); it is extracted and
         canonicalized recursively, ignoring the text before the "(".
      1. Mixed-language term lookup (Cyrillic -> English keyword/species).
      2. Direct hit against a normalized-key index of species_common_names
         (handles ANY spacing/case/hyphen variant of a Latin binomial or
         its existing canonical value, e.g. "Anas platyrhynchos" and
         "Anas_platyrhynchos" both resolve to "mallard").
      3. Common-name synonym alias table (short/regional forms that don't
         share a normalized key with any dictionary entry, e.g. "turnstone"
         -> "ruddy_turnstone" — a shorter name, not a longer one with a
         redundant word to strip).
      4. Strip a redundant qualifier word and retry the lookup (handles
         "Mallard_Duck" -> "mallard" without needing an alias-table entry
         for every compound variant).
      5. Fallback: return the normalized key itself, so even an
         unrecognized species collapses consistently across spacing/case
         variants instead of fragmenting into separate value_counts() rows.
    """
    if not raw:
        return "Unknown"

    # 0. Compound "commonname(scientificname)" label — recurse on the
    #    parenthetical part only, since it's the authoritative one.
    compound = _COMPOUND_LABEL_RE.match(raw.strip())
    if compound and compound.group(2).strip():
        return canonicalize_host_species(compound.group(2), species_common_names)

    key = _norm_key(raw)
    if not key:
        return "Unknown"

    # 1. Mixed-language (Cyrillic) terms
    if key in _MIXED_LANGUAGE_HOST_TERMS:
        return _MIXED_LANGUAGE_HOST_TERMS[key]

    # 2. Direct normalized-key hit against species_common_names
    #    (both its keys — Latin binomials — and its values — already
    #    canonical labels like "mute_swan" — are indexed, so a raw token
    #    that already IS the canonical form also normalizes cleanly).
    norm_index = {
        _norm_key(k): v for k, v in species_common_names.items()
    }
    norm_index.update({_norm_key(v): v for v in species_common_names.values()})
    if key in norm_index:
        return norm_index[key]

    # 3. Common-name synonym alias table
    if key in _COMMON_NAME_ALIASES:
        return _COMMON_NAME_ALIASES[key]

    # 4. Strip redundant qualifier words and retry
    words = key.split("_")
    stripped = [w for w in words if w not in _REDUNDANT_QUALIFIERS]
    if stripped and stripped != words:
        stripped_key = "_".join(stripped)
        if stripped_key in norm_index:
            return norm_index[stripped_key]
        if stripped_key in _COMMON_NAME_ALIASES:
            return _COMMON_NAME_ALIASES[stripped_key]
        return stripped_key

    # 5. Fallback — normalized key, at minimum collapses spacing/case variants
    return key


_ACCESSION_RE = re.compile(r"\s*EPI[\s_\-]*ISL[\s_\-]*(\d+)\s*", re.IGNORECASE)


def canonicalize_accession(raw: str) -> str:
    """Normalize accession-number format variants to one canonical form.

    "EPI_ISL_123456", "EPI ISL 123456", " EPI-ISL-123456 ", "epi isl 123456"
    all normalize to "EPI_ISL_123456". Never turns a real value into
    "Unknown" — a non-EPI_ISL accession (e.g. a GenBank accession) passes
    through with only whitespace stripped.
    """
    if not raw:
        return raw
    raw = raw.strip()
    m = _ACCESSION_RE.search(raw)
    if m:
        return _ACCESSION_RE.sub(f"EPI_ISL_{m.group(1)}", raw).strip()
    return raw


# ---------------------------------------------------------------------------
# Content-based field-type sniffers
# Used both by the parser's format-detection branch (gisaid_parser._parse_header)
# and the Header Converter diagnostic UI (pages/03_🔬_Sequence_Refinery.py).
# ---------------------------------------------------------------------------

_DATE_SNIFF_RE = re.compile(
    r"^\d{4}-\d{2}-\d{2}$|^\d{4}-\d{2}$|^\d{4}$|^\d{2}-[A-Za-z]{3}-\d{4}$|"
    r"^[A-Za-z]{3}-\d{4}$|^[A-Za-z]{3}-\d{2}-\d{4}$|^\d{8}$"
)
_CLADE_SNIFF_RE = re.compile(r"^\d[0-9A-Za-z]*(\.[0-9A-Za-z]+)+$")
_SUBTYPE_SNIFF_RE = re.compile(r"H\d+N\d+", re.IGNORECASE)


def looks_like_date(s: str) -> bool:
    """True if s matches any GISAID date format (see gisaid_parser.parse_flexible_date)."""
    if not s or s.strip() in ("", "Unknown", "unknown", "N/A", "NA", "None", "none"):
        return False
    return bool(_DATE_SNIFF_RE.match(s.strip()))


def looks_like_clade(s: str) -> bool:
    """True if s looks like a Nextstrain-style clade/lineage label (e.g. '3C.2a1b', '2.3.4.4b')."""
    if not s or s.strip() in ("Unknown", "", "None", "none"):
        return False
    return bool(_CLADE_SNIFF_RE.match(s.strip()))


def looks_like_accession(s: str) -> bool:
    """True if s looks like an EPI_ISL or GenBank-style accession token."""
    if not s:
        return False
    s = s.strip()
    if _ACCESSION_RE.search(s):
        return True
    # GenBank-style: 1-2 letters + 5-8 digits, optional version suffix
    return bool(re.match(r"^[A-Z]{1,2}\d{5,8}(\.\d+)?$", s, re.IGNORECASE))


def looks_like_segment(s: str, known_segments: frozenset) -> bool:
    """True if s (uppercased) is a single known influenza segment token."""
    if not s:
        return False
    return s.strip().upper() in known_segments


def looks_like_subtype(s: str) -> bool:
    """True if s contains an HxNx pattern or is a bare flu type marker ('A'/'B')."""
    if not s:
        return False
    s = s.strip()
    if _SUBTYPE_SNIFF_RE.search(s):
        return True
    return s.upper() in ("A", "B")


def looks_like_multi_segment(s: str, known_segments: frozenset):
    """Detect a reassortant-tag segment field (e.g. 'HA/NA', 'PB2+PB1').

    Splits s on '/', '+', ',', '_' and returns the list of tokens if >= 2
    of them are known segment names, else None. Used so a multi-segment
    tag is preserved rather than discarded as an unrecognized single value.
    """
    if not s:
        return None
    tokens = [t.strip().upper() for t in re.split(r"[/+,_]", s) if t.strip()]
    matches = [t for t in tokens if t in known_segments]
    if len(matches) >= 2:
        return tokens
    return None


def find_embedded_subtype(isolate: str):
    """Find an HxNx pattern embedded in an isolate/strain name itself.

    Some reassortant or non-standard submissions embed the subtype directly
    in the strain name (e.g. 'A/duck/China/H5N1/1/2020') in addition to a
    separate header subtype field. Returns the matched subtype string
    (e.g. 'H5N1') or None. Callers should cross-check against the header's
    own subtype field rather than assuming either is authoritative.
    """
    if not isolate:
        return None
    m = _SUBTYPE_SNIFF_RE.search(isolate)
    return m.group(0).upper() if m else None
