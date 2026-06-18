"""The ``by_area`` cost estimator: the original manual area-based formula.

This is the existing method written by the original author, extracted from
``main.py`` (the INVALID_AREA fallback block) **without behavioural changes** so
it can be run alongside the API-based estimate for comparison. Its known quirks
are preserved deliberately:

- AI packs capped at 7 (the implicit "AI all packs" bundle assumption — refuted by
  the nearmap repo's validation, but kept here so the divergence is visible).
- plain ``round()`` (not round-up) and no 5-credit floor / multiple-of-5 quantize.
- area via a local Albers equal-area projection (same as ``map_helper.estimate_area``).

Do NOT "fix" this file — the whole point is to compare it against ``by_api_return``.
"""

from __future__ import annotations

import os
import sys
from typing import Dict, List

import shapely.ops
from pyproj import CRS, Transformer
from shapely.geometry import shape

# Reuse the original author's rate table (nearmap_helper only imports `requests`).
_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
from nearmap_helper import NearMapHelper  # noqa: E402


def estimate_area(geojson_feature: Dict) -> float:
    """Area in square meters via a local Albers Equal Area projection.

    Faithful reproduction of ``map_helper.BoxDrawer.estimate_area`` so this module
    has no dependency on streamlit/folium. Accepts a GeoJSON Feature (``{"geometry":
    ...}``) or a bare geometry dict.
    """
    try:
        geom_dict = geojson_feature.get("geometry", geojson_feature)
        geom = shape(geom_dict)
        lon, lat = geom.centroid.x, geom.centroid.y
        local_aea = CRS.from_proj4(
            f"+proj=aea +lat_0={lat} +lon_0={lon} +lat_1={lat-2} +lat_2={lat+2} +datum=WGS84 +units=m"
        )
        transformer = Transformer.from_crs("EPSG:4326", local_aea, always_xy=True)
        projected_geom = shapely.ops.transform(transformer.transform, geom)
        return projected_geom.area
    except Exception as e:  # pragma: no cover - mirrors original swallow-and-zero
        print(f"Error calculating area: {e}")
        return 0.0


def estimate_by_area(
    geojson_feature: Dict,
    selected_resources: List[str],
    dates_single: str,
    area_sqm: float | None = None,
) -> int:
    """Estimate cost from area + the per-resource rate table (original method).

    Args:
        geojson_feature: GeoJSON Feature/geometry for the AOI.
        selected_resources: resource keys, e.g. ["raster:Vert", "aiPacks:building"].
        dates_single: "single" or "all".
        area_sqm: optionally supply a pre-computed area (otherwise computed here).

    Returns:
        Estimated credits (int), computed exactly as the original main.py fallback.
    """
    total_cost = 0
    ai_counter = 0  # AI packs limited to 7 maximum (preserved original behaviour)
    if area_sqm is None:
        area_sqm = estimate_area(geojson_feature)
    all_resources = NearMapHelper.get_all_resources()["all_tuples"]

    for resource in selected_resources:
        resource_object = all_resources[resource]
        namespace = resource.split(":")[0]
        unit_cost = (
            resource_object["Credits (single survey)"]
            if dates_single == "single"
            else resource_object["Credits (all survey data)"]
        )

        if namespace != "aiPacks":
            total_cost += round(unit_cost * area_sqm / 1000)
        elif namespace == "aiPacks" and ai_counter < 7:
            ai_counter += 1
            total_cost += round(unit_cost * area_sqm / 1000)
        else:
            # Skip additional AI packs beyond the 7-pack cap.
            pass

    return total_cost
