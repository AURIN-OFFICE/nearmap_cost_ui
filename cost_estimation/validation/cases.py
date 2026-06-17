"""Shared helpers for offline validation: locate cached plans, AOIs, and re-tile.

Used by both ``test_offline.py`` (assertions) and ``generate_report.py`` (the
human-readable divergence report). No API calls — everything here runs offline
against the cached coverage plans copied from the ../nearmap repo.
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path
from typing import Dict, List, Optional

_VALIDATION_DIR = Path(__file__).resolve().parent
_PKG_DIR = _VALIDATION_DIR.parent              # cost_estimation/
_REPO_ROOT = _PKG_DIR.parent                   # repo root
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from shapely.geometry import mapping  # noqa: E402

from cost_estimation import by_area as _by_area  # noqa: E402
from cost_estimation.coverage_fetcher import CoverageFetcher  # noqa: E402
from nearmap_helper import NearMapHelper  # noqa: E402

DATA_DIR = _PKG_DIR / "data"
PLANS_DIR = DATA_DIR / "credit_plans"
AOIS_DIR = DATA_DIR / "aois"

RATE_TABLE = NearMapHelper.get_all_resources()["all_tuples"]


def plan_paths() -> List[Path]:
    return sorted(PLANS_DIR.glob("*_preview.json"))


def plan_name(path: Path) -> str:
    return path.stem.replace("_preview", "")


def load_plan(path: Path) -> Dict:
    return json.loads(Path(path).read_text())


def aoi_path_for(name: str) -> Optional[Path]:
    """Map a plan name to its AOI file (adelaide_sample_* or perth_*)."""
    if name.startswith("adelaide_sample"):
        p = AOIS_DIR / "adelaide_sample_aoi.geojson"
    elif name.startswith("perth"):
        p = AOIS_DIR / "perth_aoi.geojson"
    else:
        return None
    return p if p.exists() else None


def plan_resource(plan: Dict) -> Optional[str]:
    """The resource string the plan was generated with, e.g. 'aiPacks:building'."""
    meta = plan.get("metadata", {})
    return meta.get("resource_type") or meta.get("resources")


def resource_in_rate_table(resource: Optional[str]) -> bool:
    return bool(resource) and resource in RATE_TABLE


def tile_aoi(aoi_path: Path, max_area_sqm: float = 300000):
    """Re-tile an AOI with the GDAL-free fetcher. Returns (unique_tiles, total_area)."""
    geometry = json.loads(Path(aoi_path).read_text())
    fetcher = CoverageFetcher(max_area_sqm=max_area_sqm)
    unique_tiles, _, _ = fetcher.generate_tiles(geometry)
    total_area = sum(fetcher.calculate_polygon_area_sqm(t) for t in unique_tiles)
    return unique_tiles, total_area


def aoi_albers_area(aoi_path: Path) -> float:
    """Total AOI area (sqm) via by_area's Albers method over all polygons.

    This is the area basis the legacy ``by_area`` estimate would use, summed across
    every polygon in the AOI so it is comparable to the API total (which tiles all
    polygons). The UI itself only ever feeds one feature, but for the divergence
    comparison we use the whole AOI to be apples-to-apples.
    """
    geometry = json.loads(Path(aoi_path).read_text())
    polys = CoverageFetcher().polygons_from_geometry(geometry)
    return sum(_by_area.estimate_area(mapping(p)) for p in polys)
