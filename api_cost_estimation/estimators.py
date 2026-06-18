"""Top-level cost-estimation entry points used by the UI and the validation harness.

Produces two estimates for the same AOI + resource selection:

- ``by_area``       : the original manual area-based formula (see by_area.py).
- ``by_api_return`` : tiling + summed ``preview=true`` ``costOfTransaction`` from the
                      Nearmap Coverage API (the ../nearmap method, see coverage_fetcher.py).

Both rely on the same Nearmap API key entered in the UI. ``by_api_return`` makes one
preview call per tile. Skipped tiles are split by reason: ``tiles_no_coverage`` (HTTP
404 SURVEYS_NOT_FOUND — ocean / outside the date window, genuinely $0) vs
``tiles_errored`` (timeout / 5xx / 429 / 400 — could hide real cost). The UI only
treats the total as a lower bound (``≥``) when ``tiles_errored`` > 0.
"""

from __future__ import annotations

from typing import Callable, Dict, List, Optional

from .by_area import estimate_area, estimate_by_area
from .coverage_fetcher import (  # noqa: F401  (re-export)
    DEFAULT_MAX_WORKERS,
    CoverageFetcher,
    sum_plan_cost,
)

DEFAULT_MAX_AREA_SQM = 300000
DEFAULT_SLEEP = 0.5


def count_tiles(geometry: Dict, max_area_sqm: float = DEFAULT_MAX_AREA_SQM) -> int:
    """How many tiles (= preview API calls) this AOI will require. Pure-local."""
    fetcher = CoverageFetcher(max_area_sqm=max_area_sqm)
    unique_tiles, _, _ = fetcher.generate_tiles(geometry)
    return len(unique_tiles)


def estimate_by_api(
    geometry: Dict,
    resources: List[str],
    api_key: str,
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    dates: str = "single",
    max_area_sqm: float = DEFAULT_MAX_AREA_SQM,
    sleep: float = DEFAULT_SLEEP,
    max_workers: int = DEFAULT_MAX_WORKERS,
    progress_cb: Optional[Callable[[int, int, int, int], None]] = None,
) -> Dict:
    """Tile the AOI and sum preview ``costOfTransaction`` across tiles.

    Returns a dict with: total, tiles, tiles_with_coverage, tiles_no_coverage,
    tiles_errored, plan.
    """
    fetcher = CoverageFetcher(api_key=api_key, max_area_sqm=max_area_sqm)
    unique_tiles, tile_to_sources, _ = fetcher.generate_tiles(geometry)
    resources_str = ",".join(selected.strip() for selected in resources)
    plan = fetcher.plan_coverage_for_tiles(
        unique_tiles,
        tile_to_sources,
        resources_str,
        preview=True,
        since=since,
        until=until,
        dates=dates,
        sleep=sleep,
        max_workers=max_workers,
        progress_cb=progress_cb,
    )
    summary = plan["summary"]
    return {
        "total": summary["total_estimated_cost_credits"],
        "tiles": summary["unique_tiles"],
        "tiles_with_coverage": summary["tiles_with_coverage"],
        "tiles_no_coverage": summary["tiles_no_coverage"],
        "tiles_errored": summary["tiles_errored"],
        "first_error": summary.get("first_error"),
        "plan": plan,
    }


def estimate_cost(
    geojson_feature: Dict,
    selected_resources: List[str],
    api_key: str,
    *,
    since: Optional[str] = None,
    until: Optional[str] = None,
    dates_single: str = "single",
    max_area_sqm: float = DEFAULT_MAX_AREA_SQM,
    sleep: float = DEFAULT_SLEEP,
    max_workers: int = DEFAULT_MAX_WORKERS,
    progress_cb: Optional[Callable[[int, int, int, int], None]] = None,
) -> Dict:
    """Compute both estimates for one AOI.

    Args:
        geojson_feature: GeoJSON Feature (the UI's ``st.session_state.geodata``).
        selected_resources: resource keys, e.g. ["raster:Vert", "aiPacks:building"].
        api_key: Nearmap API key (from the UI).
        dates_single: "single" or "all".

    Returns dict:
        by_area, by_api_return, resources, tiles, tiles_with_coverage,
        tiles_no_coverage, tiles_errored, area_sqm, plan.
    """
    geometry = geojson_feature.get("geometry", geojson_feature)

    area_sqm = estimate_area(geojson_feature)
    by_area = estimate_by_area(geojson_feature, selected_resources, dates_single, area_sqm=area_sqm)

    api = estimate_by_api(
        geometry,
        selected_resources,
        api_key,
        since=since,
        until=until,
        dates=dates_single,
        max_area_sqm=max_area_sqm,
        sleep=sleep,
        max_workers=max_workers,
        progress_cb=progress_cb,
    )

    return {
        "by_area": by_area,
        "by_api_return": api["total"],
        "resources": list(selected_resources),
        "tiles": api["tiles"],
        "tiles_with_coverage": api["tiles_with_coverage"],
        "tiles_no_coverage": api["tiles_no_coverage"],
        "tiles_errored": api["tiles_errored"],
        "first_error": api.get("first_error"),
        "area_sqm": area_sqm,
        "plan": api["plan"],
    }


# Scalar result fields that aggregate by summation across AOIs.
_SUMMED_RESULT_KEYS = [
    "by_area",
    "by_api_return",
    "tiles",
    "tiles_with_coverage",
    "tiles_no_coverage",
    "tiles_errored",
    "area_sqm",
]


def aggregate_results(per_aoi: List[Dict], selected_resources: List[str]) -> Dict:
    """Combine per-AOI ``estimate_cost`` results into one grand-total result (feature 7).

    The summed scalar keys match a single result's keys, so the outcome panel and quote
    export work on the aggregate unchanged. ``first_error`` is the first non-null across
    polygons; ``n_polygons`` records how many features (polygons) were estimated.
    """
    agg: Dict = {key: sum(r.get(key, 0) for r in per_aoi) for key in _SUMMED_RESULT_KEYS}
    agg["resources"] = list(selected_resources)
    agg["n_polygons"] = len(per_aoi)
    agg["first_error"] = next((r.get("first_error") for r in per_aoi if r.get("first_error")), None)
    return agg
