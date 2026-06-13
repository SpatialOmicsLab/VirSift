# -*- coding: utf-8 -*-
"""
utils/gisaid_parser.py

GISAID-optimized FASTA parser. Zero biopython dependency — string-split
parsing is faster for this known pipe-delimited format.

Header format handled (both variants):
  Standard GISAID (6 fields):
    >isolate|subtype|segment|collection_date|accession|clade
    >A/Новосибирск/RII-7.429/2024|A_/_H3N2|HA|2024-01-17|EPI_ISL_123456|3C.2a1b

  v1.0 Normalized (9 fields):
    >name|type|subtype|segment|location|host|date|clade|accession

UTF-8 MANDATORY: caller must decode bytes as UTF-8 before passing file_content.
  Correct:   uploaded_file.read().decode('utf-8')
  Incorrect: uploaded_file.read()   ← corrupts Cyrillic location names on Windows

Performance target: 10K sequences in < 5 seconds.
"""

# Increment whenever host-inference, location-extraction, or field-order
# detection logic changes — forces @st.cache_data to reparse all files.
_PARSER_VERSION = "v1.0"

import gzip
import hashlib
import io
import re
import time
import zipfile

import pandas as pd
import streamlit as st


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
    for fmt in ("%Y-%m-%d", "%Y-%m", "%Y", "%d-%b-%Y", "%b-%Y", "%b-%d-%Y", "%Y%m%d"):
        try:
            return pd.to_datetime(date_str, format=fmt)
        except ValueError:
            continue
    try:
        return pd.to_datetime(date_str)
    except Exception:
        return None


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

    Uses direct slot indexing for standard GISAID influenza A/B headers —
    this is faster and immune to unrecognised host-name tokens:

      Avian (≥5 parts):  A / HOST / Location / ID / Year  → slot 2 = Location
      Human (4 parts):   A / Location / ID / Year          → slot 1 = Location

    Falls back to the skip-based scanner for RSV, MERS, SARS and other
    non-influenza or non-standard-length formats.

    Preserves Cyrillic characters (e.g., Новосибирск).
    """
    if not isolate_name:
        return "Unknown"
    parts = [p.strip() for p in isolate_name.split("/") if p.strip()]
    n = len(parts)
    _is_flu_AB = isolate_name.startswith("A/") or isolate_name.startswith("B/")

    # Direct slot rule for standard influenza A/B ─────────────────────────────
    if _is_flu_AB and n >= 5:
        # Avian/animal format: [A, HOST, Location, ID, Year, …]
        return parts[2]

    if _is_flu_AB and n == 4:
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
    "Anas_penelope":        "wigeon",
    "Anas_americana":       "American_wigeon",
    "Anas_discors":         "blue-winged_teal",
    "Anas_formosa":         "Baikal_teal",
    "Anas_poecilorhyncha":  "spot-billed_duck",
    "Anas_falcata":         "falcated_duck",
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
    "Branta_canadensis":    "Canada_goose",
    "Branta_bernicla":      "brent_goose",
    "Branta_leucopsis":     "barnacle_goose",
    # Mergus — mergansers
    "Mergus_merganser":     "merganser",
    "Mergus_serrator":      "red-breasted_merganser",
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

    For standard influenza A/B with ≥5 slash parts the host token is
    always at slot 1 (A / HOST / Location / ID / Year).  It is returned
    directly regardless of whether the name is in our keyword database —
    e.g. 'Podiceps_cristatus' will be returned verbatim even though that
    genus is not yet in _AVIAN_GENERA.

    For 4-part human influenza (A / Location / ID / Year) returns 'Unknown'
    because there is no host slot.

    For RSV and other formats falls back to the skip-based scanner that
    walks parts and returns the first part recognised by _classify_isolate_part().
    """
    if not isolate_name:
        return "Unknown"
    _skip = frozenset({"a", "b", "hrsv", "rsv", "mers-cov", "sars-cov", "environment"})
    parts = [p.strip() for p in isolate_name.split("/") if p.strip()]
    n = len(parts)
    _is_flu_AB = isolate_name.startswith("A/") or isolate_name.startswith("B/")

    # Direct slot rule for standard influenza A/B ─────────────────────────────
    if _is_flu_AB and n >= 5:
        # Slot 1 = host species token (always present in avian/animal records)
        token = parts[1]
        raw = token if token.lower() not in _skip else "Unknown"
        return _SPECIES_COMMON_NAMES.get(raw, raw)

    if _is_flu_AB and n == 4:
        # Human format — no host slot
        return "Unknown"

    # Fallback: skip-based scanner for RSV and other formats ──────────────────
    for part in parts:
        if not part or part.lower() in _skip:
            continue
        if _classify_isolate_part(part) is not None:
            raw = part
            return _SPECIES_COMMON_NAMES.get(raw, raw)
    return "Unknown"


def compute_sequence_hash(sequence: str) -> str:
    """12-character MD5 hash of uppercased sequence for identity tracking."""
    return hashlib.md5(sequence.upper().encode()).hexdigest()[:12]


def convert_df_to_fasta(df: pd.DataFrame) -> str:
    """Convert a filtered DataFrame back to FASTA format string.

    Fully vectorized header construction — no iterrows.
    Reconstructs pipe-delimited GISAID-style headers.
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
    p = part.lower().strip()
    if not p:
        return None
    words = p.replace("-", "_").split("_")
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
        metadata = {
            "isolate":      parts[0],
            "subtype":      parts[2] if n > 2 else "Unknown",
            "segment":      parts[3] if n > 3 else "Unknown",
            "location":     parts[4] if n > 4 else "Unknown",
            "host":         _v1_host,
            "host_species": _extract_host_species(parts[0]) if _v1_host == "Unknown"
                            else _v1_host,
            "_raw_date":    parts[6] if n > 6 else "",
            "clade":        parts[7] if n > 7 else "Unknown",
            "accession":    parts[8] if n > 8 else "Unknown",
        }
    elif n <= 3:
        # hRSV / short format: isolate | accession | date
        # (also handles degenerate 1- or 2-field headers gracefully)
        raw_isolate = parts[0] if n > 0 else "Unknown"
        metadata = {
            "isolate":      raw_isolate,
            "subtype":      "Unknown",
            "segment":      "Unknown",
            "accession":    parts[1] if n > 1 else "Unknown",
            "_raw_date":    parts[2] if n > 2 else "",
            "clade":        "Unknown",
            "host":         infer_host_from_isolate(raw_isolate),
            "host_species": _extract_host_species(raw_isolate),
            "location":     extract_location_from_isolate(raw_isolate),
        }
    else:
        # 4–8 field headers: detect avian vs human field order by checking
        # whether parts[1] is a known segment name.
        #   Avian batch:  isolate | SEGMENT | subtype | date | accession | clade
        #   Human/B std:  isolate | subtype | SEGMENT | date | accession | clade
        raw_isolate = parts[0] if n > 0 else "Unknown"
        p1 = parts[1] if n > 1 else "Unknown"
        p2 = parts[2] if n > 2 else "Unknown"

        if p1.upper() in _KNOWN_SEGMENTS:
            # Avian format: segment is in position 1, subtype in position 2
            segment = p1
            subtype  = p2
        else:
            # Human/B format: subtype is in position 1, segment in position 2
            subtype  = p1
            segment  = p2

        metadata = {
            "isolate":      raw_isolate,
            "subtype":      subtype,
            "segment":      segment,
            "_raw_date":    parts[3] if n > 3 else "",
            "accession":    parts[4] if n > 4 else "Unknown",
            "clade":        parts[5] if n > 5 else "Unknown",
            "host":         infer_host_from_isolate(raw_isolate),
            "host_species": _extract_host_species(raw_isolate),
            "location":     extract_location_from_isolate(raw_isolate),
        }

    # subtype_clean: "A_/_H3N2" → "H3N2", "H5N1" stays as-is
    m = _HXNX_RE.search(metadata["subtype"])
    metadata["subtype_clean"] = m.group(1) if m else metadata["subtype"]

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
