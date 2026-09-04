# -*- coding: utf-8 -*-
"""
utils/gisaid_parser.py

GISAID-optimized FASTA parser. Zero biopython dependency — string-split
parsing is faster for this known pipe-delimited format.

Header format handled:
  Standard GISAID (6 fields):
    >isolate|subtype|segment|collection_date|accession|clade
    >A/Новосибирск/RII-7.429/2024|A_/_H3N2|HA|2024-01-17|EPI_ISL_123456|3C.2a1b

  v1.0 Normalized (9 fields):
    >name|type|subtype|segment|location|host|date|clade|accession

  No-segment variant (content-detected, no fixed field count):
    >isolate|subtype|date|accession-or-placeholder|clade
    e.g. a header with no dedicated segment field at all. Detected by
    content sniffing (utils/name_normalizer.py) rather than position —
    only the segment field degrades to "Unknown"; date/accession/clade are
    placed correctly regardless of position. See _parse_header() for detail.

  Multi-segment reassortant tags (e.g. segment field = "HA/NA") are kept
  verbatim (not discarded) with `is_reassortant_segment=True`.

  A subtype embedded in the isolate/strain name itself that conflicts with
  the header's own subtype field is captured in `subtype_isolate_embedded`
  rather than silently overwriting either value.

UTF-8 MANDATORY: caller must decode bytes as UTF-8 before passing file_content.
  Correct:   uploaded_file.read().decode('utf-8')
  Incorrect: uploaded_file.read()   ← corrupts Cyrillic location names on Windows

Performance target: 10K sequences in < 5 seconds.
"""

# Increment whenever host-inference, location-extraction, field-order
# detection, or normalization logic changes — forces @st.cache_data to
# reparse all files (including already-uploaded ones in a running session).
_PARSER_VERSION = "v1.0"

import gzip
import hashlib
import io
import re
import time
import zipfile

import pandas as pd
import streamlit as st

from utils.name_normalizer import (
    _MIXED_LANGUAGE_HOST_TERMS,
    _norm_key,
    canonicalize_accession,
    canonicalize_host_species,
    find_embedded_subtype,
    looks_like_accession,
    looks_like_clade,
    looks_like_date,
    looks_like_multi_segment,
    looks_like_segment,
)
from utils.host_tier_classifier import classify_host_tier


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

@st.cache_data(show_spinner=False)
def parse_gisaid_fasta(file_content: str, file_name: str,
                       _version: str = _PARSER_VERSION) -> tuple:
    """Parse a UTF-8 decoded GISAID FASTA string into a list of metadata dicts.

    Decorated with @st.cache_data — parses ONCE per unique (file_content, file_name).
    Subsequent calls with identical arguments return the cached result instantly.

    Args:
        file_content: UTF-8 decoded FASTA string.
                      Caller must decode: raw_bytes.decode('utf-8')
        file_name:    Original filename (included in cache key).

    Returns:
        Tuple: (list_of_metadata_dicts, parse_time_seconds)

        Each dict contains:
            isolate, subtype, subtype_clean, segment,
            collection_date (pd.Timestamp|None), accession, clade,
            clade_l1..clade_l6 (str|None),
            host, location,
            sequence (str, uppercased), sequence_length (int), sequence_hash (str)
    """
    sequences = []
    parsing_start = time.perf_counter()

    current_header = None
    current_seq_parts = []

    for line in file_content.splitlines():
        line = line.strip()
        if not line:
            continue
        if line.startswith(">"):
            # Flush previous record
            if current_header is not None:
                # Strip alignment gap characters (-) so .aln-fasta files
                # (Clustal Omega MSA output) compute correct lengths and hashes.
                seq = "".join(current_seq_parts).upper().replace(" ", "").replace("-", "")
                metadata = _parse_header(current_header)
                metadata["original_header"] = current_header
                metadata["sequence"] = seq
                metadata["sequence_length"] = len(seq)
                metadata["sequence_hash"] = compute_sequence_hash(seq)
                sequences.append(metadata)
            current_header = line[1:]
            current_seq_parts = []
        else:
            current_seq_parts.append(line)

    # Flush last record
    if current_header is not None:
        seq = "".join(current_seq_parts).upper().replace(" ", "").replace("-", "")
        metadata = _parse_header(current_header)
        metadata["original_header"] = current_header
        metadata["sequence"] = seq
        metadata["sequence_length"] = len(seq)
        metadata["sequence_hash"] = compute_sequence_hash(seq)
        sequences.append(metadata)

    # Batch-vectorize date parsing — replaces 10K individual pd.to_datetime() calls
    # with a single Series operation for a ~4x throughput improvement.
    if sequences:
        raw_dates = [s.pop("_raw_date", "") for s in sequences]
        parsed_dates = _batch_parse_dates(raw_dates)
        for s, d in zip(sequences, parsed_dates):
            s["collection_date"] = d

    parsing_time = time.perf_counter() - parsing_start
    return sequences, parsing_time


def decompress_if_needed(raw_bytes: bytes, file_name: str) -> str:
    """Decompress .gz or .zip files and return a UTF-8 decoded string.

    For .zip archives, concatenates ALL FASTA-like files found in the archive.
    This handles multi-segment or multi-file ZIPs (e.g. one file per segment,
    one file per year, or any sub-alignment bundles) — all sequences are merged
    into a single FASTA string in sorted filename order.

    Falls back to plain UTF-8 decode for uncompressed files.
    """
    import os as _os
    name_lower = file_name.lower()
    try:
        if name_lower.endswith(".gz"):
            return gzip.decompress(raw_bytes).decode("utf-8", errors="replace")
        if name_lower.endswith(".zip"):
            with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
                fasta_exts = (".fasta", ".fa", ".fas", ".fna", ".txt", ".aln-fasta")
                # Filter: keep only FASTA-like members; skip macOS metadata and dotfiles
                fasta_members = sorted([
                    m for m in zf.namelist()
                    if m.lower().endswith(fasta_exts)
                    and not m.startswith("__MACOSX")
                    and not _os.path.basename(m).startswith(".")
                ])
                if fasta_members:
                    parts: list[str] = []
                    for member in fasta_members:
                        with zf.open(member) as f:
                            parts.append(f.read().decode("utf-8", errors="replace"))
                    # Join with a blank line so FASTA records from separate files
                    # don't accidentally merge into each other.
                    return "\n".join(parts)
                # Fallback: return first file in archive regardless of extension
                if zf.namelist():
                    with zf.open(zf.namelist()[0]) as f:
                        return f.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    return raw_bytes.decode("utf-8", errors="replace")


def decompress_zip_to_files(raw_bytes: bytes) -> dict:
    """Extract a ZIP archive to a {member_basename: fasta_content_str} dict.

    Only FASTA-like members are included (.fasta .fa .fas .fna .txt).
    Returns an empty dict on failure or if no FASTA members are found.
    Used by the Workspace upload loop so that each FASTA inside a ZIP
    is treated as its own separate raw_files entry (batch mode).
    """
    import os as _os
    result = {}
    try:
        with zipfile.ZipFile(io.BytesIO(raw_bytes)) as zf:
            fasta_exts = (".fasta", ".fa", ".fas", ".fna", ".txt", ".aln-fasta")
            members = sorted([
                m for m in zf.namelist()
                if m.lower().endswith(fasta_exts)
                and not m.startswith("__MACOSX")
                and not _os.path.basename(m).startswith(".")
            ])
            for member in members:
                with zf.open(member) as f:
                    result[member] = f.read().decode("utf-8", errors="replace")
    except Exception:
        pass
    return result


def parse_flexible_date(date_str: str):
    """Handle all GISAID date format variants.

    Supported: %Y-%m-%d, %Y-%m, %Y, %d-%b-%Y, %b-%Y, %b-%d-%Y, %Y%m%d
    Returns pd.Timestamp or None on failure.
    """
    if not date_str:
        return None
    date_str = date_str.strip()
    if date_str in ("", "Unknown", "unknown", "N/A", "NA", "None", "none"):
        return None
    date_str = _strip_gisaid_xx_placeholders(date_str)
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y", "%d-%b-%Y", "%b-%Y", "%b-%d-%Y", "%Y%m%d"):
        try:
            return pd.to_datetime(date_str, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(date_str)
    except Exception:
        return None


def _normalize_hyphen_delimited_isolate(isolate_name: str) -> str:
    """Convert a hyphen-delimited GISAID isolate name to the standard
    slash-delimited form, so every downstream host/species/location
    extraction function only ever has to handle one convention.

    Some submitters export isolate names using "-" as the field delimiter
    instead of "/" — e.g. "A-duck-Ibaraki-1-2016-E1_S1" instead of
    "A/duck/Ibaraki/1/2016-E1_S1". Left unconverted, this breaks every
    slash-based rule in this module: _is_flu_AB (startswith "A/") is False,
    so host/location/species all fall through to "Unknown", or worse, the
    RSV-style fallback scanner returns the whole mangled name as a fake
    "species" (observed in real data as host_species = "a_ibaraki_1_2016_e1_s1").

    Detection is deliberately narrow to avoid corrupting genuinely
    hyphenated content (place names like "Ust-Kamchatsk", species names
    like "white-fronted_goose", or compound strain IDs): only triggers when
    the name has ZERO slashes AND starts with "A-" or "B-" — an
    unambiguous signal, since a real slash-delimited name never starts
    that way. Only the first three hyphens (Type|Host|Location boundaries,
    which are always simple single-word tokens) become slashes; everything
    from the ID field onward is left as one hyphenated tail, so a
    compound/hyphenated strain-ID or year suffix is never split further.

    "A-duck-Ibaraki-1-2016-E1_S1" -> "A/duck/Ibaraki/1-2016-E1_S1"
    """
    if "/" in isolate_name:
        return isolate_name
    if not (isolate_name.startswith("A-") or isolate_name.startswith("B-")):
        return isolate_name
    parts = isolate_name.split("-")
    if len(parts) < 4:
        return isolate_name
    return "/".join(parts[:3]) + "/" + "-".join(parts[3:])


def infer_host_from_isolate(isolate_name: str) -> str:
    """Infer host class from GISAID isolate naming conventions.

    PRIMARY RULE — GISAID Influenza A/B structural slot count:
      Avian/animal: A / HOST / Location / ID / Year  → ≥5 slash parts
      Human:        A / Location / ID / Year          → 4 slash parts

    GISAID human influenza isolate names NEVER carry a host field — the slot
    count is therefore the most reliable discriminator. Keyword scanning is
    used first to identify the specific host class (Avian vs Mammalian), and
    the slot count is the tiebreaker when no keyword matches.

    Detection order for influenza A/B:
      1. Keyword scan at positions 1 & 2 (covers Latin binomials, compound
         underscore names, and common English names)
      2. Slot count ≥5 with no keyword match → Avian (structural guarantee:
         an unrecognised host token at slot 1 is still a non-human animal)
      3. Slot count 4 → Human
      4. Slot count ≤3 → Human (degenerate/short format)

    For non-influenza pathogens (hRSV, MERS-CoV, SARS-CoV): caught by prefix
    check before any slot logic.  Legacy whole-string keyword scan is kept as
    a final safety net for non-A/B or unusual database entries.
    """
    if not isolate_name:
        return "Unknown"
    isolate_name = _normalize_hyphen_delimited_isolate(isolate_name)
    name_lower = isolate_name.lower()
    if "/environment/" in name_lower:
        return "Environment"
    # Known non-influenza human respiratory pathogens — always Human
    if name_lower.startswith(("hrsv/", "rsv/", "mers-cov/", "sars-cov/")):
        return "Human"

    _slash_parts = isolate_name.split("/")
    _n = len(_slash_parts)
    _is_flu_AB = isolate_name.startswith("A/") or isolate_name.startswith("B/")

    if _is_flu_AB:
        # ── Step 1: keyword scan at slots 1 and 2 ─────────────────────────────
        # Slot 1 is always the host for avian/animal sequences.
        # Slot 2 is checked as a secondary guard for unusual host placements.
        for _pos in (1, 2):
            if _pos < _n:
                _r = _classify_isolate_part(_slash_parts[_pos])
                if _r:
                    return _r

        # ── Step 2: structural tiebreaker ──────────────────────────────────────
        # No keyword match — use slot count to decide.
        # GISAID convention:
        #   ≥5 parts  →  animal source (host is at slot 1, even if unrecognised)
        #    4 parts  →  human source (no host slot at all)
        if _n >= 5:
            # e.g. A/Podiceps_cristatus/Chany/3/2019  (grebe — genus not in DB)
            # Structural guarantee: 5-part A/B influenza names ALWAYS originate
            # from a non-human host.  Return Avian rather than falling through to
            # the ≥2-slash Human fallback that existed previously.
            return "Avian"
        # 4-part or shorter A/B → Human
        return "Human"

    # ── Keyword scan for non-A/B and non-standard formats ─────────────────────
    # Kept as a safety net for unusual pathogen prefixes or old database exports.
    _legacy_avian = [
        "duck", "mallard", "pintail", "teal", "wigeon", "shoveler", "gadwall",
        "pochard", "scaup", "eider", "goldeneye", "bufflehead", "canvasback",
        "redhead", "smew", "merganser", "ruddy duck",
        "goose", "brant", "barnacle", "greylag", "snow goose", "canada goose",
        "bean goose", "white-fronted goose", "swan", "whooper", "mute swan",
        "pelican", "cormorant", "gannet", "booby", "frigatebird",
        "egret", "heron", "bittern", "ibis", "spoonbill", "stork", "crane",
        "gull", "tern", "skua", "puffin", "guillemot", "razorbill", "auk",
        "petrel", "shearwater", "albatross", "fulmar", "penguin",
        "plover", "sandpiper", "dunlin", "knot", "turnstone", "curlew", "godwit",
        "whimbrel", "snipe", "woodcock", "avocet", "oystercatcher", "lapwing",
        "redshank", "greenshank", "phalarope", "stint", "ruff", "dowitcher",
        "yellowlegs", "chicken", "hen", "broiler", "layer", "turkey", "quail",
        "pheasant", "partridge", "grouse", "guinea fowl", "peafowl", "chukar",
        "junglefowl", "ostrich", "emu", "cassowary", "rhea",
        "coot", "moorhen", "rail", "crake", "gallinule",
        "pigeon", "dove",
        "sparrow", "starling", "crow", "magpie", "raven", "rook", "jackdaw",
        "finch", "bunting", "thrush", "blackbird", "robin", "warbler",
        "swift", "martin", "swallow",
        "hawk", "eagle", "falcon", "owl", "kite", "harrier", "buzzard",
        "kestrel", "vulture", "osprey",
        "wild bird", "avian", "bird", "poultry", "waterfowl", "shorebird",
        "wader", "seabird", "passerine", "raptor", "fowl", "gallinaceous",
    ]
    if any(k in name_lower for k in _legacy_avian):
        return "Avian"
    _legacy_mammal = [
        "swine", "pig", "ferret", "mink", "seal", "sea lion", "walrus",
        "cat", "dog", "horse", "tiger", "leopard", "lion", "bear",
        "bat", "fox", "raccoon", "otter", "badger", "mongoose", "civet",
        "whale", "dolphin", "porpoise", "bovine", "cattle", "cow",
        "sheep", "goat", "deer", "elk", "moose", "rabbit", "rodent",
    ]
    if any(k in name_lower for k in _legacy_mammal):
        return "Mammalian"

    return "Unknown"


def extract_location_from_isolate(isolate_name: str) -> str:
    """Extract geographic location from a GISAID isolate name.

    Uses keyword-scan-first disambiguation (mirrors infer_host_from_isolate)
    before falling back to slot indexing — a 4-part isolate name is only
    genuinely "Human" (Type/Location/ID/Year) when slot 1 does NOT look like
    a host token. A 4-part AVIAN name missing its strain-ID field (e.g.
    "A/turkey/England/1969") would otherwise be misread as Human format,
    returning the host name ("turkey") as the location instead of the real
    location ("England") one slot later.

      Recognised host at slot 1 or 2:  Location = the slot right after it
      No host recognised, ≥5 parts:    Avian/animal, unrecognised host at
                                        slot 1 (structural guarantee) → slot 2
      No host recognised, 4 parts:     Human format → slot 1

    Falls back to the skip-based scanner for RSV, MERS, SARS and other
    non-influenza or non-standard-length formats.

    Preserves Cyrillic characters (e.g., Новосибирск).
    """
    if not isolate_name:
        return "Unknown"
    isolate_name = _normalize_hyphen_delimited_isolate(isolate_name)
    parts = [p.strip() for p in isolate_name.split("/") if p.strip()]
    n = len(parts)
    _is_flu_AB = isolate_name.startswith("A/") or isolate_name.startswith("B/")

    if _is_flu_AB:
        # ── Step 1: keyword scan at slots 1 and 2, same as infer_host_from_isolate ──
        for _pos in (1, 2):
            if _pos < n and _classify_isolate_part(parts[_pos]) is not None:
                loc_slot = _pos + 1
                return parts[loc_slot] if loc_slot < n else "Unknown"

        # ── Step 2: structural tiebreaker (no keyword match at slot 1/2) ──
        if n >= 5:
            # Avian/animal format: [A, HOST(unrecognised), Location, ID, Year, …]
            return parts[2]
        if n == 4:
            # Human format: [A, Location, ID, Year]
            return parts[1]

    # Skip-based scanner for RSV, MERS, SARS and other formats ───────────────
    # Skips the type prefix and any recognisable host tokens, then returns the
    # first remaining part as the location.
    _always_skip = frozenset({"a", "b", "hrsv", "rsv", "mers-cov", "sars-cov",
                               "environment"})
    for part in parts:
        p_low = part.lower()
        if p_low in _always_skip:
            continue
        if _classify_isolate_part(part) is not None:
            continue
        return part

    return parts[1] if n > 1 else "Unknown"


# Scientific name → common name lookup (applied to host_species column).
# Maps GISAID verbatim tokens at slot 1 to their conventional English name.
# Case-sensitive — keys match the exact capitalisation used in GISAID headers.
_SPECIES_COMMON_NAMES: dict = {
    # Anatidae — ducks
    "Anas_platyrhynchos":   "mallard",
    "Anas_crecca":          "common_teal",
    "Anas_carolinensis":    "green-winged_teal",
    "Anas_strepera":        "gadwall",
    "Anas_acuta":           "pintail",
    "Anas_clypeata":        "shoveler",
    "Anas_querquedula":     "garganey",
    "Anas_penelope":        "wigeon",  # a.k.a. European wigeon — see _COMMON_NAME_ALIASES
    "Anas_americana":       "American_wigeon",
    "Anas_discors":         "blue-winged_teal",
    "Anas_formosa":         "Baikal_teal",
    "Anas_poecilorhyncha":  "spot-billed_duck",
    "Anas_falcata":         "falcated_duck",
    "Cairina_moschata":     "muscovy_duck",
    # Tadorna — shelducks (genuinely distinct species, kept separate)
    "Tadorna_ferruginea":   "ruddy_shelduck",
    "Tadorna_tadorna":      "common_shelduck",
    "Tadorna_variegata":    "paradise_shelduck",
    # Scolopacidae — sandpipers, turnstones
    "Arenaria_interpres":   "ruddy_turnstone",
    # Aythya — diving ducks
    "Aythya_ferina":        "pochard",
    "Aythya_fuligula":      "tufted_duck",
    "Aythya_marila":        "scaup",
    "Aythya_nyroca":        "ferruginous_duck",
    # Anser — geese
    "Anser_anser":          "greylag_goose",
    "Anser_fabalis":        "bean_goose",
    "Anser_albifrons":      "white-fronted_goose",
    "Anser_brachyrhynchus": "pink-footed_goose",
    "Anser_caerulescens":   "snow_goose",
    "Anser_cygnoides":      "swan_goose",
    "Branta_canadensis":    "Canada_goose",
    "Branta_bernicla":      "brent_goose",
    "Branta_leucopsis":     "barnacle_goose",
    # Mergus — mergansers
    "Mergus_merganser":     "merganser",
    "Mergus_serrator":      "red-breasted_merganser",
    # Sternidae — terns
    "Sterna_paradisaea":    "arctic_tern",
    # Cygnus — swans
    "Cygnus_olor":          "mute_swan",
    "Cygnus_cygnus":        "whooper_swan",
    "Cygnus_columbianus":   "Bewick_swan",
    # Podicipedidae — grebes
    "Podiceps_cristatus":   "great_crested_grebe",
    "Podiceps_grisegena":   "red-necked_grebe",
    "Podiceps_auritus":     "Slavonian_grebe",
    # Corvidae
    "Corvus_frugilegus":    "rook",
    "Corvus_corax":         "raven",
    "Corvus_corone":        "carrion_crow",
    # Galliformes
    "Gallus_gallus":        "chicken",
    "Meleagris_gallopavo":  "turkey",
    "Coturnix_coturnix":    "quail",
    "Coturnix_japonica":    "Japanese_quail",
    "Phasianus_colchicus":  "pheasant",
    "Numida_meleagris":     "guinea_fowl",
    # Columbidae
    "Columba_livia":        "pigeon",
    # Ardeidae
    "Ardea_cinerea":        "grey_heron",
    "Nycticorax_nycticorax": "night_heron",
    # Mammals
    "Sus_scrofa":           "pig",
    "Equus_caballus":       "horse",
    "Felis_catus":          "cat",
    "Canis_lupus":          "dog",
    "Mustela_vison":        "mink",
    "Neovison_vison":       "mink",
    "Halichoerus_grypus":   "grey_seal",
    "Phoca_vitulina":       "harbour_seal",
    "Phoca_largha":         "spotted_seal",
    "Odobenus_rosmarus":    "walrus",
}


def _extract_host_species(isolate_name: str) -> str:
    """Return the specific host-species token from a GISAID isolate name.

    Uses keyword-scan-first disambiguation (mirrors infer_host_from_isolate)
    before falling back to slot indexing — a 4-part isolate name is only
    genuinely human (no host slot) when slot 1 does NOT look like a host
    token. A 4-part AVIAN name missing its strain-ID field (e.g.
    "A/turkey/England/1969") is correctly recognised via the "turkey"
    keyword match rather than being written off as human.

    For standard influenza A/B with ≥5 slash parts and no keyword match,
    the host token at slot 1 is still returned verbatim (structural
    guarantee) — e.g. 'Podiceps_cristatus' even though that genus is not
    yet in _AVIAN_GENERA.

    For 4-part human influenza (A / Location / ID / Year) with no keyword
    match at slot 1 returns 'Unknown' because there is no host slot.

    For RSV and other formats falls back to the skip-based scanner that
    walks parts and returns the first part recognised by _classify_isolate_part().
    """
    if not isolate_name:
        return "Unknown"
    isolate_name = _normalize_hyphen_delimited_isolate(isolate_name)
    _skip = frozenset({"a", "b", "hrsv", "rsv", "mers-cov", "sars-cov", "environment"})
    parts = [p.strip() for p in isolate_name.split("/") if p.strip()]
    n = len(parts)
    _is_flu_AB = isolate_name.startswith("A/") or isolate_name.startswith("B/")

    if _is_flu_AB:
        # ── Step 1: keyword scan at slots 1 and 2, same as infer_host_from_isolate ──
        for _pos in (1, 2):
            if _pos < n:
                token = parts[_pos]
                if token.lower() in _skip:
                    continue
                if _classify_isolate_part(token) is not None:
                    return canonicalize_host_species(token, _SPECIES_COMMON_NAMES)

        # ── Step 2: structural tiebreaker (no keyword match at slot 1/2) ──
        if n >= 5:
            # Unrecognised host token at slot 1 — still return it verbatim.
            token = parts[1]
            return "Unknown" if token.lower() in _skip else canonicalize_host_species(token, _SPECIES_COMMON_NAMES)
        # 4-part or shorter with no keyword match = genuine human (no host slot)
        return "Unknown"

    # Fallback: skip-based scanner for RSV and other formats ──────────────────
    for part in parts:
        if not part or part.lower() in _skip:
            continue
        if _classify_isolate_part(part) is not None:
            return canonicalize_host_species(part, _SPECIES_COMMON_NAMES)
    return "Unknown"


def compute_sequence_hash(sequence: str) -> str:
    """12-character MD5 hash of uppercased sequence for identity tracking."""
    return hashlib.md5(sequence.upper().encode()).hexdigest()[:12]


def convert_df_to_fasta(df: pd.DataFrame, header_format: str = "gisaid6") -> str:
    """Convert a filtered DataFrame back to FASTA format string.

    Fully vectorized header construction — no iterrows.

    Args:
        header_format:
            "gisaid6" (default, unchanged) — isolate|subtype|segment|date|accession|clade.
            "full9" — the legacy v1.0 field order, isolate|type|segment|date|
                      accession|clade|host|location, so host/location survive
                      into the exported header text instead of staying only
                      in the DataFrame/CSV export.
    """
    if df.empty:
        return ""

    def _col(name: str, fallback: str = "Unknown") -> pd.Series:
        if name in df.columns:
            return df[name].fillna(fallback).astype(str)
        return pd.Series([fallback] * len(df), index=df.index)

    # Format collection_date to YYYY-MM-DD
    if "collection_date" in df.columns:
        date_col = pd.to_datetime(df["collection_date"], errors="coerce")
        date_str = date_col.dt.strftime("%Y-%m-%d").fillna("Unknown")
    else:
        date_str = pd.Series(["Unknown"] * len(df), index=df.index)

    if header_format == "full9":
        headers = (
            ">"
            + _col("isolate") + "|"
            + _col("subtype") + "|"
            + _col("segment") + "|"
            + date_str + "|"
            + _col("accession") + "|"
            + _col("clade") + "|"
            + _col("host") + "|"
            + _col("location")
        )
    else:
        headers = (
            ">"
            + _col("isolate") + "|"
            + _col("subtype") + "|"
            + _col("segment") + "|"
            + date_str + "|"
            + _col("accession") + "|"
            + _col("clade")
        )
    sequences = _col("sequence", "")

    # Vectorized interleave: ">{header}\n{seq}" per record, joined by \n
    return (headers + "\n" + sequences).str.cat(sep="\n")


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------

_HXNX_RE = re.compile(r"(H\d+N\d+)")
# Fallback for HA-only or NA-only submissions where the other side of the
# subtype was never typed (e.g. raw "A_/_H3" with no N number at all) — the
# full H#N# pattern above never matches these, so subtype_clean silently
# fell through to the raw, uncleaned string ("A_/_H3" instead of "H3").
_HX_OR_NX_RE = re.compile(r"(H\d+|N\d+)")

# ---------------------------------------------------------------------------
# Latin genus → host-type lookup tables
# These cover the genera that appear in GISAID isolate names as
# scientific binomials (e.g. A/Anas_platyrhynchos/Chany_Lake/10/03).
# Only the genus (first word of Genus_species) is needed.
# ---------------------------------------------------------------------------
_AVIAN_GENERA: frozenset = frozenset({
    # Anatidae — ducks, geese, swans
    "anas", "aythya", "bucephala", "clangula", "mergus", "mergellus",
    "oxyura", "netta", "marmaronetta", "spatula", "anas",
    "anser", "branta", "chen", "cygnus", "coscoroba",
    # Pelecanidae / Sulidae / Fregatidae
    "pelecanus", "phalacrocorax", "morus", "sula", "fregata",
    # Ardeidae / Ciconiidae / Threskiornithidae
    "ardea", "egretta", "bubulcus", "nycticorax", "ciconia", "mycteria",
    "threskiornis", "plegadis", "platalea",
    # Charadriiformes — waders, gulls, terns, auks
    "calidris", "tringa", "charadrius", "pluvialis", "limosa", "numenius",
    "gallinago", "scolopax", "recurvirostra", "haematopus", "vanellus",
    "phalaropus", "philomachus", "actitis", "arenaria",
    "larus", "chroicocephalus", "leucophaeus", "sterna", "thalasseus",
    "anous", "catharacta", "stercorarius", "fratercula", "alca",
    "uria", "cepphus", "alle",
    # Procellariidae — petrels, shearwaters, albatrosses
    "puffinus", "calonectris", "fulmarus", "oceanodroma", "diomedea",
    "thalassarche", "macronectes",
    # Galliformes — poultry & game
    "gallus", "meleagris", "coturnix", "phasianus", "numida",
    "perdix", "alectoris", "colinus", "callipepla", "lophura",
    "chrysolophus", "polyplectron", "afropavo", "pavo",
    # Gruiformes — rails, coots, cranes
    "fulica", "gallinula", "rallus", "crex", "porzana", "grus",
    "balearica", "anthropoides",
    # Columbiformes
    "columba", "streptopelia", "zenaida", "geopelia",
    # Passeriformes
    "passer", "sturnus", "corvus", "pica", "pyrrhocorax", "turdus",
    "erithacus", "fringilla", "emberiza", "hirundo", "delichon",
    "ficedula", "sylvia", "phylloscopus", "acrocephalus",
    # Accipitriformes / Falconiformes — raptors
    "accipiter", "buteo", "aquila", "hieraaetus", "haliaeetus",
    "pandion", "milvus", "circus", "elanus", "falco",
    # Strigiformes — owls
    "strix", "bubo", "asio", "tyto", "athene",
    # Sphenisciformes — penguins
    "spheniscus", "pygoscelis", "aptenodytes", "eudyptes",
    # Struthioniformes / Casuariiformes — ratites
    "struthio", "dromaius", "rhea", "casuarius",
})

_MAMMAL_GENERA: frozenset = frozenset({
    # Suidae
    "sus",
    # Mustelidae — ferret, mink, otter, badger
    "mustela", "neovison", "neogale", "lutra", "meles",
    # Phocidae / Otariidae — seals, sea lions
    "halichoerus", "phoca", "mirounga", "zalophus", "arctocephalus",
    # Felidae — cats, tigers, leopards
    "felis", "panthera", "neofelis", "prionailurus",
    # Canidae
    "canis", "vulpes", "nyctereutes",
    # Equidae
    "equus",
    # Chiroptera — bats (orders and genera)
    "rhinolophus", "pteropus", "tadarida", "myotis", "pipistrellus",
    "miniopterus", "hipposideros", "cynopterus",
    # Cetacea — whales, dolphins
    "balaena", "tursiops", "delphinus", "phocoena", "orcinus",
    "megaptera", "balaenoptera",
    # Bovidae / Cervidae / Camelidae
    "bos", "bubalus", "ovis", "capra", "cervus", "alces", "odocoileus",
    "rangifer", "camelus", "lama",
    # Viverridae / Herpestidae
    "viverra", "civettictis", "herpestes",
    # Procyonidae
    "procyon",
    # Lagomorpha
    "oryctolagus", "lepus",
})

# Flat sets of common-name keyword tokens used for fast word-level matching
# inside compound host parts like "common_teal", "mallard_duck", "domestic_chicken".
# These mirror the lists in infer_host_from_isolate() but as a frozenset for
# O(1) lookup when splitting underscore-separated isolate parts.
_AVIAN_KW: frozenset = frozenset({
    "duck", "mallard", "pintail", "teal", "wigeon", "shoveler", "gadwall",
    "pochard", "scaup", "eider", "goldeneye", "bufflehead", "canvasback",
    "redhead", "smew", "merganser",
    "goose", "brant", "barnacle", "greylag", "swan", "whooper",
    "pelican", "cormorant", "gannet", "booby", "frigatebird",
    "egret", "heron", "bittern", "ibis", "spoonbill", "stork", "crane",
    "gull", "tern", "skua", "puffin", "guillemot", "razorbill", "auk",
    "petrel", "shearwater", "albatross", "fulmar", "penguin",
    "plover", "sandpiper", "dunlin", "knot", "turnstone", "curlew", "godwit",
    "whimbrel", "snipe", "woodcock", "avocet", "oystercatcher", "lapwing",
    "redshank", "greenshank", "phalarope", "stint", "ruff", "dowitcher",
    "chicken", "hen", "broiler", "layer", "turkey", "quail", "pheasant",
    "partridge", "grouse", "peafowl", "chukar", "junglefowl",
    "ostrich", "emu", "cassowary", "rhea",
    "coot", "moorhen", "rail", "crake", "gallinule",
    "pigeon", "dove",
    "sparrow", "starling", "crow", "magpie", "raven", "rook", "jackdaw",
    "finch", "warbler", "swift", "martin", "swallow",
    "hawk", "eagle", "falcon", "owl", "kite", "harrier", "buzzard",
    "kestrel", "vulture", "osprey",
    "bird", "avian", "poultry", "waterfowl", "shorebird",
    "wader", "seabird", "passerine", "raptor", "fowl",
    "domestic", "wild",   # context words: "domestic_chicken", "wild_bird"
})

_MAMMAL_KW: frozenset = frozenset({
    "swine", "pig", "boar", "pork",
    "ferret", "mink", "otter", "badger",
    "seal", "sealion",
    "cat", "feline", "tiger", "leopard", "lion",
    "dog", "canine", "fox", "raccoon",
    "horse", "equine",
    "bat",
    "whale", "dolphin", "porpoise",
    "bovine", "cattle", "cow", "bull", "calf",
    "sheep", "ovine", "goat", "deer", "elk", "moose", "rabbit",
    "mongoose", "civet",
})


def _classify_isolate_part(part: str) -> str | None:
    """Classify a single slash-delimited isolate part as 'Avian', 'Mammalian',
    or None (not a recognisable host token).

    Handles three naming conventions found in GISAID isolate names:
      1. Exact common name:        "duck", "chicken", "ferret"
      2. Compound underscore name: "common_teal", "mallard_duck", "domestic_chicken"
      3. Latin binomial:           "Anas_platyrhynchos", "Gallus_gallus", "Sus_scrofa"
    """
    p = _norm_key(part)
    if not p:
        return None

    # Mixed-language (Cyrillic) host terms — checked first, since the app
    # already explicitly supports Cyrillic location names and the same
    # real-world data carries Cyrillic host terms.
    if p in _MIXED_LANGUAGE_HOST_TERMS:
        mapped = _MIXED_LANGUAGE_HOST_TERMS[p]
        if mapped in _AVIAN_KW or mapped == "wild_bird":
            return "Avian"
        if mapped in _MAMMAL_KW:
            return "Mammalian"

    words = p.split("_")
    genus = words[0]

    # Latin genus lookup (fast O(1) frozenset check)
    if genus in _AVIAN_GENERA:
        return "Avian"
    if genus in _MAMMAL_GENERA:
        return "Mammalian"

    # Word-level common-name lookup (handles "common_teal" → "teal" is avian)
    for w in words:
        if w in _AVIAN_KW:
            return "Avian"
        if w in _MAMMAL_KW:
            return "Mammalian"

    return None

# Known influenza gene segment names — used to auto-detect field order in
# 6-field GISAID headers.  GISAID avian batch downloads emit the header as:
#   >isolate | SEGMENT | SUBTYPE | date | accession | clade
# while human/normalized downloads emit:
#   >isolate | SUBTYPE | SEGMENT | date | accession | clade
# We detect the avian variant by checking whether parts[1] is a segment name.
_KNOWN_SEGMENTS = frozenset({
    "HA", "NA", "PB1", "PB2", "PA", "NP", "MP", "NS",
    "HE", "P3",          # less-common influenza segments
    "M1", "M2",          # MP gene products sometimes labelled individually
    "NEP", "NS1", "NS2", # NS gene products
})

# Standard GISAID date format tried first as a fast path
_FAST_DATE_FMT = "%Y-%m-%d"

# Fallback formats tried only for dates that didn't match the fast path
_SLOW_DATE_FMTS = ("%Y-%m", "%Y", "%d-%b-%Y", "%b-%Y", "%b-%d-%Y", "%Y%m%d")

_DATE_NULL_SET = frozenset(("", "Unknown", "unknown", "N/A", "NA", "None", "none"))

# GISAID's own submission/export convention represents an unknown date
# component with a literal "XX" rather than omitting it: "2013-01-XX" (day
# unknown), "2011-XX-XX" (month+day unknown). Left as-is, these fail every
# format above and the WHOLE date is lost as "Unknown" even when the year
# (or year+month) is genuinely known. Truncating to the known prefix first
# reduces "2013-01-XX" -> "2013-01" and "2011-XX-XX" -> "2011", which the
# existing "%Y-%m" / "%Y" formats already parse correctly — so precision
# that IS available is kept instead of being discarded along with the part
# that isn't. A year that is itself partly unknown ("20XX-XX-XX") has no
# concrete year to fall back to and is intentionally left unparsed.
_GISAID_XX_DAY_RE = re.compile(r"^(\d{4}-\d{2})-XX$", re.IGNORECASE)
_GISAID_XX_MONTH_DAY_RE = re.compile(r"^(\d{4})-XX-XX$", re.IGNORECASE)


def _strip_gisaid_xx_placeholders(raw: str) -> str:
    """Truncate a GISAID XX-placeholder date to its known prefix, if any."""
    m = _GISAID_XX_DAY_RE.match(raw)
    if m:
        return m.group(1)
    m = _GISAID_XX_MONTH_DAY_RE.match(raw)
    if m:
        return m.group(1)
    return raw


def _batch_parse_dates(date_strings: list) -> list:
    """Vectorized date parser — converts a list of raw date strings to
    pd.Timestamp | None values in a single pass.

    Strategy:
      1. Fast path: vectorized pd.to_datetime() on the full Series using the
         dominant GISAID format "%Y-%m-%d". Covers ~95% of real data.
      2. Slow path: per-string fallback for dates that didn't parse in step 1
         (partial dates like "2024-01", "2024", or locale formats).

    This replaces N individual pd.to_datetime() calls with one vectorized
    call, reducing overhead by ~4x for 10K records.
    """
    if not date_strings:
        return []

    s = pd.Series(date_strings, dtype=str)

    # Step 0: truncate GISAID "XX" placeholders to their known prefix
    # (vectorized) so partial precision survives instead of being lost.
    s = s.str.replace(_GISAID_XX_DAY_RE, r"\1", regex=True)
    s = s.str.replace(_GISAID_XX_MONTH_DAY_RE, r"\1", regex=True)

    # Step 1: fast vectorized parse on the dominant format
    fast = pd.to_datetime(s, format=_FAST_DATE_FMT, errors="coerce")

    # Step 2: for entries that failed, try slow fallback formats
    null_mask = fast.isna()
    if null_mask.any():
        for raw, idx in zip(s[null_mask], s[null_mask].index):
            raw = raw.strip() if isinstance(raw, str) else ""
            if raw in _DATE_NULL_SET:
                continue  # leave as NaT → None below
            for fmt in _SLOW_DATE_FMTS:
                try:
                    fast.iloc[idx] = pd.to_datetime(raw, format=fmt)
                    break
                except (ValueError, TypeError):
                    continue
            else:
                # Last resort: pandas inference
                try:
                    fast.iloc[idx] = pd.to_datetime(raw)
                except Exception:
                    pass

    # Convert NaT → None for consistency with downstream code
    return [None if pd.isna(v) else v for v in fast]


def _parse_header(header: str) -> dict:
    """Parse one FASTA header line (without leading '>') into a metadata dict.

    Handles four GISAID/respiratory-virus header variants:

    1. v1.0 Normalized (9 fields):
         name | type | subtype | segment | location | host | date | clade | accession

    2. Standard GISAID human/B (6 fields, subtype before segment):
         isolate | subtype | segment | date | accession | clade
         e.g. >A/Novosibirsk/.../2024|A_/_H3N2|HA|2024-01-17|EPI_ISL_...|3C.2a1b

    3. GISAID avian batch download (6 fields, SEGMENT before subtype):
         isolate | segment | subtype | date | accession | clade
         e.g. >A/goose/Zambia/05/2008|PB2|A_/_H3N8|07.2008|EPI_ISL_88225|
         Detected automatically: parts[1] is a known segment name (HA, NA, …)

    4. hRSV / 3-field (3 fields):
         isolate | accession | date
         e.g. >hRSV/B/Argentina/.../2016|EPI_ISL_1074181|2016-04-18

    All fields default to 'Unknown' / None gracefully — never raises.
    """
    parts = [p.strip() for p in header.split("|")]
    n = len(parts)

    if n >= 9:
        # v1.0 Normalized: name | type | subtype | segment | location | host | date | clade | accession
        _v1_host = parts[5] if n > 5 else "Unknown"
        _v1_accession = parts[8] if n > 8 else "Unknown"
        metadata = {
            "isolate":      parts[0],
            "subtype":      parts[2] if n > 2 else "Unknown",
            "segment":      parts[3] if n > 3 else "Unknown",
            "location":     parts[4] if n > 4 else "Unknown",
            "host":         _v1_host,
            "host_species": _extract_host_species(parts[0]) if _v1_host == "Unknown"
                            else canonicalize_host_species(_v1_host, _SPECIES_COMMON_NAMES),
            "_raw_date":    parts[6] if n > 6 else "",
            "clade":        parts[7] if n > 7 else "Unknown",
            "accession":    canonicalize_accession(_v1_accession) if _v1_accession != "Unknown" else "Unknown",
        }
    elif n <= 3:
        # hRSV / short format: isolate | accession | date
        # (also handles degenerate 1- or 2-field headers gracefully)
        raw_isolate = parts[0] if n > 0 else "Unknown"
        _short_accession = parts[1] if n > 1 else "Unknown"
        metadata = {
            "isolate":      raw_isolate,
            "subtype":      "Unknown",
            "segment":      "Unknown",
            "accession":    canonicalize_accession(_short_accession) if _short_accession != "Unknown" else "Unknown",
            "_raw_date":    parts[2] if n > 2 else "",
            "clade":        "Unknown",
            "host":         infer_host_from_isolate(raw_isolate),
            "host_species": _extract_host_species(raw_isolate),
            "location":     extract_location_from_isolate(raw_isolate),
        }
    else:
        # 4–8 field headers: content-aware field-type detection.
        #
        # Two structurally different sub-formats share this field-count range:
        #   A) Has a segment field:
        #        Avian batch:  isolate | SEGMENT | subtype | date | accession | clade
        #        Human/B std:  isolate | subtype | SEGMENT | date | accession | clade
        #   B) No segment field at all (confirmed real-world variant):
        #        isolate | subtype | date | accession-or-placeholder | clade
        #
        # Distinguishing (A) from (B) by position alone silently corrupts (B) —
        # a fixed-position read would misassign segment=date-value and
        # accession=clade-value. Instead: detect segment by CONTENT
        # (known segment token, or a multi-segment reassortant tag like
        # "HA/NA"), then classify every remaining field by content too
        # (looks_like_date / looks_like_clade / looks_like_accession) rather
        # than trusting position. This guarantees a missing segment degrades
        # ONLY the segment field — nothing else in the record is affected —
        # and a literal "Unknown"/blank placeholder in the source data is
        # never mistaken for a real accession value.
        raw_isolate = parts[0] if n > 0 else "Unknown"
        p1 = parts[1] if n > 1 else ""
        p2 = parts[2] if n > 2 else ""

        p1_is_segment = looks_like_segment(p1, _KNOWN_SEGMENTS)
        p2_is_segment = looks_like_segment(p2, _KNOWN_SEGMENTS)
        p1_multi_seg = None if p1_is_segment else looks_like_multi_segment(p1, _KNOWN_SEGMENTS)
        p2_multi_seg = None if p2_is_segment else looks_like_multi_segment(p2, _KNOWN_SEGMENTS)

        is_reassortant = False
        if p1_is_segment or p1_multi_seg:
            # Avian batch order: isolate | SEGMENT | subtype | date | accession | clade
            segment = p1
            subtype = p2
            is_reassortant = bool(p1_multi_seg)
            rest = parts[3:]
        elif p2_is_segment or p2_multi_seg:
            # Human/B order: isolate | subtype | SEGMENT | date | accession | clade
            subtype = p1
            segment = p2
            is_reassortant = bool(p2_multi_seg)
            rest = parts[3:]
        else:
            # No segment field present — variant (B). Only this field
            # degrades; date/accession/clade are recovered by content below.
            subtype = p1
            segment = "Unknown"
            rest = parts[2:]

        # Classify remaining fields by content, not position.
        _PLACEHOLDER_VALUES = ("", "Unknown", "unknown", "N/A", "NA", "None", "none")
        date_val, accession_val, clade_val = "", "Unknown", "Unknown"
        unclassified = []
        for f in rest:
            if not date_val and looks_like_date(f):
                date_val = f
            elif clade_val == "Unknown" and looks_like_clade(f):
                clade_val = f
            elif accession_val == "Unknown" and looks_like_accession(f):
                accession_val = f
            else:
                unclassified.append(f)
        # Fill any still-default slot from leftover fields, preserving
        # original field order — matters only when content sniffing is
        # inconclusive; never lets a placeholder value become the accession.
        for f in unclassified:
            if not date_val:
                date_val = f
            elif accession_val == "Unknown" and f not in _PLACEHOLDER_VALUES:
                accession_val = f
            elif clade_val == "Unknown" and f not in _PLACEHOLDER_VALUES:
                clade_val = f

        metadata = {
            "isolate":      raw_isolate,
            "subtype":      subtype,
            "segment":      segment,
            "is_reassortant_segment": is_reassortant,
            "_raw_date":    date_val,
            "accession":    canonicalize_accession(accession_val) if accession_val != "Unknown" else "Unknown",
            "clade":        clade_val if clade_val else "Unknown",
            "host":         infer_host_from_isolate(raw_isolate),
            "host_species": _extract_host_species(raw_isolate),
            "location":     extract_location_from_isolate(raw_isolate),
        }

    # subtype_clean: "A_/_H3N2" → "H3N2", "H5N1" stays as-is.
    # HA-only/NA-only submissions never have a full H#N# pair (e.g. raw
    # "A_/_H3" with the N side untyped) — fall back to matching H# or N#
    # alone rather than leaving the raw "A_/_H3" string uncleaned.
    m = _HXNX_RE.search(metadata["subtype"])
    if m:
        metadata["subtype_clean"] = m.group(1)
    else:
        m2 = _HX_OR_NX_RE.search(metadata["subtype"])
        metadata["subtype_clean"] = m2.group(1) if m2 else metadata["subtype"]

    # Double-subtype check: a subtype embedded in the isolate/strain name
    # itself (e.g. "A/duck/China/H5N1/1/2020") that conflicts with the
    # header's own subtype field. Never silently overwrites either value —
    # surfaced via this column so the Header Converter can flag it.
    _embedded = find_embedded_subtype(metadata["isolate"])
    metadata["subtype_isolate_embedded"] = (
        _embedded if _embedded and _embedded != metadata["subtype_clean"].upper() else None
    )

    # Reassortant-segment flag defaults to False for branches that always
    # have an explicit single segment field (v1.0 Normalized, hRSV/short).
    metadata.setdefault("is_reassortant_segment", False)

    # Biosecurity tier — derived from host/host_species, never overwrites them.
    metadata["host_tier"] = classify_host_tier(metadata["host"], metadata["host_species"])

    # Hierarchical clade levels: "3C.2a1b.2a.2a" → l1="3C", l2="3C.2a1b", ...
    clade_val = metadata.get("clade") or "Unknown"
    if clade_val not in ("Unknown", "", "None", "none"):
        levels = clade_val.split(".")
        for i in range(6):
            metadata[f"clade_l{i + 1}"] = ".".join(levels[: i + 1]) if i < len(levels) else None
    else:
        for i in range(6):
            metadata[f"clade_l{i + 1}"] = None

    return metadata
