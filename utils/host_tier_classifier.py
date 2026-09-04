# -*- coding: utf-8 -*-
"""
utils/host_tier_classifier.py

Biosecurity-tier classification: Wild Birds -> Intermediate -> Poultry.

This is a best-effort heuristic over genus/keyword data, NOT a certainty —
species-name alone cannot always distinguish (e.g.) a wild mallard from a
farmed one. Ambiguous/unrecognized avian hosts return "Unclassified" rather
than guessing wrong. Presented in the UI as an overridable filter dimension
alongside `host`/`host_species`, never a silent relabel of them.

Pure logic layer — zero UI/Streamlit dependencies.
"""

TIER_GLOSSARY: dict = {
    "Wild Birds": (
        "The natural, unmanaged reservoir — free-roaming, self-sustaining "
        "populations with zero reliance on humans. Dominated by migratory "
        "waterfowl, shorebirds, and pelagic seabirds. Maintains the ancestral "
        "pool of low-pathogenic strains through migration and aquatic shedding, "
        "entirely outside human control."
    ),
    "Intermediate": (
        "The critical biosecurity-breach zone — birds that blur the line "
        "between the wild ecosystem and human agriculture. Peridomestic "
        "scavengers (crows, pigeons, gulls) feeding on farm waste, backyard "
        "hobby flocks, captive zoo populations, and game birds bred for "
        "release. Low biosecurity + high contact rates let wild viruses spill "
        "in, mutate, adapt to terrestrial hosts, and amplify before reaching "
        "commercial lines."
    ),
    "Poultry": (
        "The industrial amplification host — domesticated chickens, turkeys, "
        "and domestic ducks in intensive, controlled commercial systems under "
        "strict biosecurity protocols. If a virus from the Intermediate tier "
        "breaches this perimeter, extreme density and genetic homogeneity turn "
        "the environment into a high-velocity evolutionary pressure cooker, "
        "often driving low-pathogenic strains toward highly pathogenic "
        "phenotypes."
    ),
    "Unclassified": (
        "Avian host detected but genus/keyword data was insufficient to "
        "confidently assign a biosecurity tier, or the host is non-avian "
        "(Human/Mammalian/Environment/Unknown)."
    ),
}

# Re-bucketed from gisaid_parser._AVIAN_GENERA / _AVIAN_KW into 3 tiers.
# Poultry: overwhelmingly-farmed genera in surveillance datasets.
_POULTRY_GENERA = frozenset({
    "gallus", "meleagris", "numida",
})
_POULTRY_KW = frozenset({
    "chicken", "hen", "broiler", "layer", "turkey", "poultry", "domestic",
    "farm", "farmed", "commercial", "guinea_fowl", "guineafowl",
})

# Domestic-breed qualifiers that override an otherwise-wild genus/keyword
# match to Poultry — e.g. "domestic_mallard", "Pekin" (the standard
# commercial breed name for domesticated Anas platyrhynchos), "bantam"
# (small domestic chicken breed). Checked before genus/keyword lookup in
# classify_host_tier() so the domesticated status wins regardless of which
# wild species the breed descends from. Deliberately excludes "backyard"
# and "captive" — those already correctly route to Intermediate (low-
# biosecurity, not industrial commercial) via _INTERMEDIATE_KW; including
# them here would wrongly override that.
_DOMESTIC_BREED_KW = frozenset({
    "domestic", "domesticated", "farmed", "commercial", "pekin", "bantam", "reared",
})

# Intermediate: peridomestic scavengers + backyard/zoo/game-release context.
_INTERMEDIATE_GENERA = frozenset({
    "corvus", "pica", "pyrrhocorax",                      # crows, magpies, choughs
    "columba", "streptopelia",                             # pigeons, doves
    "larus", "chroicocephalus", "leucophaeus",             # gulls
    "sturnus",                                              # starlings (peridomestic)
})
_INTERMEDIATE_KW = frozenset({
    "crow", "magpie", "raven", "rook", "jackdaw",
    "pigeon", "dove",
    "gull", "starling",
    "backyard", "hobby", "zoo", "captive", "game", "released", "release",
    "pheasant", "partridge", "quail",  # game birds bred for release
})

# Wild Birds: migratory waterfowl, shorebirds, pelagic seabirds — everything
# else already in _AVIAN_GENERA / _AVIAN_KW (gisaid_parser.py) not claimed above.
_WILD_GENERA = frozenset({
    "anas", "aythya", "bucephala", "clangula", "mergus", "mergellus",
    "oxyura", "netta", "marmaronetta", "spatula",
    "anser", "branta", "chen", "cygnus", "coscoroba",
    "calidris", "tringa", "charadrius", "pluvialis", "limosa", "numenius",
    "gallinago", "scolopax", "recurvirostra", "haematopus", "vanellus",
    "phalaropus", "philomachus", "actitis", "arenaria",
    "sterna", "thalasseus", "anous", "catharacta", "stercorarius",
    "fratercula", "alca", "uria", "cepphus", "alle",
    "puffinus", "calonectris", "fulmarus", "oceanodroma", "diomedea",
    "thalassarche", "macronectes",
    "pelecanus", "phalacrocorax", "morus", "sula", "fregata",
    "ardea", "egretta", "bubulcus", "nycticorax", "ciconia", "mycteria",
    "threskiornis", "plegadis", "platalea",
    "fulica", "gallinula", "rallus", "crex", "porzana", "grus",
    "balearica", "anthropoides",
    "spheniscus", "pygoscelis", "aptenodytes", "eudyptes",
})
_WILD_KW = frozenset({
    "duck", "mallard", "pintail", "teal", "wigeon", "shoveler", "gadwall",
    "pochard", "scaup", "eider", "goldeneye", "bufflehead", "canvasback",
    "redhead", "smew", "merganser",
    "goose", "brant", "barnacle", "greylag", "swan", "whooper",
    "pelican", "cormorant", "gannet", "booby", "frigatebird",
    "egret", "heron", "bittern", "ibis", "spoonbill", "stork", "crane",
    "tern", "skua", "puffin", "guillemot", "razorbill", "auk",
    "petrel", "shearwater", "albatross", "fulmar", "penguin",
    "plover", "sandpiper", "dunlin", "knot", "turnstone", "curlew", "godwit",
    "whimbrel", "snipe", "woodcock", "avocet", "oystercatcher", "lapwing",
    "redshank", "greenshank", "phalarope", "stint", "ruff", "dowitcher",
    "coot", "moorhen", "rail", "crake", "gallinule",
    "waterfowl", "shorebird", "wader", "seabird", "migratory", "wild",
})


def classify_host_tier(host: str, host_species: str) -> str:
    """Classify an avian record into a biosecurity tier.

    Args:
        host: the coarse host class ("Avian"/"Mammalian"/"Human"/"Environment"/"Unknown").
        host_species: the specific species token (post-canonicalization),
            e.g. "mallard", "chicken", "Anas_platyrhynchos".

    Returns one of "Wild Birds", "Intermediate", "Poultry", "Unclassified".
    Non-avian hosts and unrecognized avian species both return "Unclassified"
    — this is a best-effort heuristic, not a certainty, and is never used to
    silently overwrite `host`/`host_species`.
    """
    if host != "Avian":
        return "Unclassified"
    if not host_species or host_species == "Unknown":
        return "Unclassified"

    token = host_species.lower().replace("-", "_")
    words = token.split("_")
    genus = words[0]

    # Domestic-breed qualifier overrides genus/keyword classification —
    # checked FIRST. A species whose base genus/keyword would otherwise
    # match Wild Birds (e.g. "mallard") is explicitly Poultry when tagged
    # as a domesticated breed: "domestic_mallard" and "Pekin" (the common
    # commercial breed name for domesticated Anas platyrhynchos) are farmed
    # birds, not the wild reservoir, even though they're the same species.
    # Confirmed against real surveillance data where both co-occurred
    # alongside wild "mallard" records.
    if any(w in _DOMESTIC_BREED_KW for w in words):
        return "Poultry"

    if genus in _POULTRY_GENERA or any(w in _POULTRY_KW for w in words):
        return "Poultry"
    if genus in _INTERMEDIATE_GENERA or any(w in _INTERMEDIATE_KW for w in words):
        return "Intermediate"
    if genus in _WILD_GENERA or any(w in _WILD_KW for w in words):
        return "Wild Birds"

    return "Unclassified"
