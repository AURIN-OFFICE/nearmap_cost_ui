"""Human-readable labels + catalogue display order for resource keys (UI presentation).

The API / data model uses terse keys (``aiPacks:pavement_cond``); the selection UI shows
the names from the Nearmap AI Packs catalogue, in catalogue order. This lives apart from
``nearmap_helper`` so the data model stays presentation-agnostic. Any key missing from
``LABELS`` falls back to a title-cased short name, and any key missing from
``DISPLAY_ORDER`` sorts to the end, so a newly added resource never breaks the UI.
"""

from __future__ import annotations

from typing import Dict, Iterable, List

# Per-namespace order. aiPacks matches the Nearmap website AI Packs catalogue exactly.
DISPLAY_ORDER: Dict[str, List[str]] = {
    "raster": [
        "raster:Vert", "raster:TrueOrtho",
        "raster:North", "raster:East", "raster:South", "raster:West",
        "raster:DetailDtm", "raster:DetailDsm",
    ],
    "aiPacks": [
        "aiPacks:building", "aiPacks:building_char", "aiPacks:building_structures",
        "aiPacks:construction", "aiPacks:roof_char", "aiPacks:roof_materials",
        "aiPacks:roof_shape", "aiPacks:roof_objects", "aiPacks:commercial_roof_objects",
        "aiPacks:roof_cond", "aiPacks:advanced_roof_cond", "aiPacks:roof_overhang",
        "aiPacks:trampoline", "aiPacks:solar", "aiPacks:pool", "aiPacks:surfaces",
        "aiPacks:vegetation", "aiPacks:poles", "aiPacks:surface_permeability",
        "aiPacks:pavement_marking", "aiPacks:pavement_cond", "aiPacks:yard_objects",
        "aiPacks:debris", "aiPacks:utilities", "aiPacks:experimental",
    ],
    "trueOrthoAiPacks": [
        "trueOrthoAiPacks:building", "trueOrthoAiPacks:building_char",
    ],
    "aiImpactAssessment": [
        "aiImpactAssessment:postcat",
    ],
}

LABELS: Dict[str, str] = {
    # raster
    "raster:Vert": "Vertical Imagery",
    "raster:TrueOrtho": "True Ortho",
    "raster:North": "Panorama (North)",
    "raster:East": "Panorama (East)",
    "raster:South": "Panorama (South)",
    "raster:West": "Panorama (West)",
    "raster:DetailDtm": "DEM/DTM",
    "raster:DetailDsm": "DSM",
    # AI packs — Nearmap catalogue names
    "aiPacks:building": "Building Footprints",
    "aiPacks:building_char": "Building Characteristics",
    "aiPacks:building_structures": "Building Structures",
    "aiPacks:construction": "Construction",
    "aiPacks:roof_char": "Roof Characteristics",
    "aiPacks:roof_materials": "Roof Materials",
    "aiPacks:roof_shape": "Roof Shape",
    "aiPacks:roof_objects": "Roof Objects",
    "aiPacks:commercial_roof_objects": "Commercial Roof Objects",
    "aiPacks:roof_cond": "Roof Condition",
    "aiPacks:advanced_roof_cond": "Advanced Roof Condition",
    "aiPacks:roof_overhang": "Roof Overhang",
    "aiPacks:trampoline": "Trampoline",
    "aiPacks:solar": "Solar Panels",
    "aiPacks:pool": "Pool",
    "aiPacks:surfaces": "Surfaces",
    "aiPacks:vegetation": "Vegetation",
    "aiPacks:poles": "Poles",
    "aiPacks:surface_permeability": "Surface Permeability",
    "aiPacks:pavement_marking": "Pavement Markings",
    "aiPacks:pavement_cond": "Pavement Condition",
    "aiPacks:yard_objects": "Yard Objects",
    "aiPacks:debris": "Debris",
    "aiPacks:utilities": "Utilities",
    "aiPacks:experimental": "Experimental",
    # other namespaces
    "trueOrthoAiPacks:building": "Building Footprints (True Ortho)",
    "trueOrthoAiPacks:building_char": "Building Characteristics (True Ortho)",
    "aiImpactAssessment:postcat": "Post-Catastrophe (ImpactAssessment)",
}


def label_for(key: str) -> str:
    """Human-readable label for a resource key; prettified short name as a fallback."""
    if key in LABELS:
        return LABELS[key]
    short = key.split(":", 1)[-1]
    return short.replace("_", " ").title()


def ordered_keys(namespace: str, keys: Iterable[str]) -> List[str]:
    """``keys`` reordered to the catalogue order; keys not in the order go last (by name)."""
    order = DISPLAY_ORDER.get(namespace, [])
    rank = {k: i for i, k in enumerate(order)}
    return sorted(keys, key=lambda k: (rank.get(k, len(order)), k))
