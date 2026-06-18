"""Cost estimation package.

Provides two estimators for a Nearmap AOI + resource selection:

- ``by_area``       : the original manual area-based formula (by_area.py).
- ``by_api_return`` : tiling + summed preview ``costOfTransaction`` (coverage_fetcher.py).

See ``estimators.estimate_cost`` for the combined entry point used by the UI, and
``validation/`` for the offline (cached-plan replay) and live (preview=true) checks.
"""

from .by_area import estimate_area, estimate_by_area
from .coverage_fetcher import CoverageFetcher, DataFetcher, sum_plan_cost
from .estimators import count_tiles, estimate_by_api, estimate_cost

__all__ = [
    "estimate_area",
    "estimate_by_area",
    "CoverageFetcher",
    "DataFetcher",
    "sum_plan_cost",
    "count_tiles",
    "estimate_by_api",
    "estimate_cost",
]
