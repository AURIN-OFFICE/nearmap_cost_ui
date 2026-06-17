"""Offline validation of the cost estimators (no API key, no network, $0).

Ground truth = the cached coverage plans copied from the ../nearmap repo, which were
produced by the original (GDAL-based) code with preview=true.

What this proves:
1. sum check         - our aggregation reproduces each plan's stored total.
2. tiling reproduction - the GDAL-free tiler produces the same tiles as the original.
3. quantization      - cached per-tile costs obey the 5-credit / multiple-of-5 rule.
4. failed-tile model - plans with errored tiles undercount (caveat A) as expected.
5. by_area sanity    - the legacy estimator stays same-order-of-magnitude for 1 pack.

What this CANNOT prove offline (covered by the live script instead):
- multi-pack / mixed-resource combined-call billing (cached plans are single-pack).
- current API pricing (cached values are a May-2026 snapshot).
"""

from __future__ import annotations

import pytest

from api_cost_estimation.coverage_fetcher import sum_plan_cost
from api_cost_estimation.by_area import estimate_by_area

from . import cases

PLAN_PATHS = cases.plan_paths()
PLAN_IDS = [cases.plan_name(p) for p in PLAN_PATHS]


def test_has_cached_plans():
    assert PLAN_PATHS, "no cached credit_plans found to validate against"


@pytest.mark.parametrize("path", PLAN_PATHS, ids=PLAN_IDS)
def test_sum_matches_stored_total(path):
    """Our aggregation (sum of per-tile costOfTransaction) == the stored total."""
    plan = cases.load_plan(path)
    stored = plan["summary"]["total_estimated_cost_credits"]
    assert sum_plan_cost(plan) == stored


@pytest.mark.parametrize("path", PLAN_PATHS, ids=PLAN_IDS)
def test_per_tile_costs_quantized(path):
    """Every stored per-tile cost is a non-negative multiple of 5 (T5)."""
    plan = cases.load_plan(path)
    for tile in plan.get("tiles", []):
        cost = tile.get("coverage", {}).get("costOfTransaction", 0)
        assert cost >= 0
        assert cost % 5 == 0, f"{cases.plan_name(path)}: tile cost {cost} not a multiple of 5"


@pytest.mark.parametrize("path", PLAN_PATHS, ids=PLAN_IDS)
def test_tile_count_reproduced(path):
    """The GDAL-free tiler reproduces the original's unique tile count."""
    plan = cases.load_plan(path)
    name = cases.plan_name(path)
    aoi = cases.aoi_path_for(name)
    if aoi is None:
        pytest.skip(f"no local AOI for {name}")
    expected = plan["summary"]["unique_tiles"]
    unique_tiles, _ = cases.tile_aoi(aoi, plan["metadata"].get("max_area_sqm", 300000))
    assert len(unique_tiles) == expected


@pytest.mark.parametrize("path", PLAN_PATHS, ids=PLAN_IDS)
def test_tiled_area_matches_for_fully_covered(path):
    """For fully-covered AOIs, re-tiled total area ~= sum of stored tile areas (<1%)."""
    plan = cases.load_plan(path)
    name = cases.plan_name(path)
    aoi = cases.aoi_path_for(name)
    if aoi is None:
        pytest.skip(f"no local AOI for {name}")
    summary = plan["summary"]
    if summary["tiles_with_coverage"] != summary["unique_tiles"] or summary["unique_tiles"] == 0:
        pytest.skip(f"{name}: not fully covered (cannot compare full area)")
    cached_area = sum(t.get("area_sqm", 0.0) for t in plan["tiles"])
    _, my_area = cases.tile_aoi(aoi, plan["metadata"].get("max_area_sqm", 300000))
    rel = abs(my_area - cached_area) / cached_area
    assert rel < 0.01, f"{name}: area diff {rel:.4%} (mine={my_area:.0f}, cached={cached_area:.0f})"


def test_failed_tiles_undercount_demonstrated():
    """The all-failed pavement_condition plan reads 0 credits (caveat A in real data)."""
    target = next((p for p in PLAN_PATHS if "pavement_condition" in p.name), None)
    if target is None:
        pytest.skip("pavement_condition plan not present")
    plan = cases.load_plan(target)
    # Original cached plans use tiles_with_coverage; an all-failed plan has 0 coverage + 0 cost.
    assert plan["summary"]["tiles_with_coverage"] == 0
    assert plan["summary"]["total_estimated_cost_credits"] == 0
    assert plan["summary"]["unique_tiles"] > 0  # tiles WERE generated, just all errored


@pytest.mark.parametrize("path", PLAN_PATHS, ids=PLAN_IDS)
def test_by_area_same_order_for_single_pack(path):
    """Legacy by_area stays within 0.5x-2x of by_api for a single pack (sanity floor).

    (Single-pack is the only case offline data covers; the >7-pack divergence is
    shown in the report's synthetic section and the live script.)
    """
    plan = cases.load_plan(path)
    name = cases.plan_name(path)
    aoi = cases.aoi_path_for(name)
    resource = cases.plan_resource(plan)
    api_total = plan["summary"]["total_estimated_cost_credits"]
    if aoi is None or not cases.resource_in_rate_table(resource) or api_total == 0:
        pytest.skip(f"{name}: not comparable (missing aoi/rate/coverage)")
    dates = plan["metadata"].get("date_filter_mode", "single")
    area_sqm = cases.aoi_albers_area(aoi)
    by_area = estimate_by_area({}, [resource], dates, area_sqm=area_sqm)
    ratio = by_area / api_total
    assert 0.5 <= ratio <= 2.0, f"{name}: by_area/by_api ratio {ratio:.2f} out of [0.5, 2.0]"


def test_404_counts_as_no_coverage_not_error():
    """A 404 tile is classified as no_coverage (genuine $0); other failures error.

    This is the distinction that decides whether the UI shows an exact figure or a
    ">=" lower bound. Mocks the per-tile call, so it needs no network.
    """
    import requests
    from shapely.geometry import box

    from api_cost_estimation.coverage_fetcher import CoverageFetcher

    fetcher = CoverageFetcher(api_key="x")
    tiles = [box(138.600, -34.920, 138.601, -34.919) for _ in range(3)]
    sources = {0: [0], 1: [0], 2: [0]}

    def fake_call(tile, resources, idx, **kw):
        if idx == 0:  # covered
            return {"costOfTransaction": 10, "surveys": [{}]}
        resp = requests.Response()
        resp.status_code = 404 if idx == 1 else 500  # 404 = no coverage, 500 = real error
        raise requests.exceptions.HTTPError(response=resp)

    fetcher.get_coverage_for_tile = fake_call
    summary = fetcher.plan_coverage_for_tiles(tiles, sources, "aiPacks:building", sleep=0)["summary"]

    assert summary["tiles_with_coverage"] == 1
    assert summary["tiles_no_coverage"] == 1            # the 404 -> correct $0
    assert summary["tiles_errored"] == 1                # the 500 -> would trigger ">="
    assert summary["total_estimated_cost_credits"] == 10


# --- the two sublinear "bundles" (both modeled the same by by_area and the API) ---


def _load_cost_table():
    import json
    from pathlib import Path
    root = Path(__file__).resolve().parent.parent.parent
    return json.loads((root / "cost_table.json").read_text())


def test_cost_table_all_survey_is_1_5x_single():
    """Multi-survey bundle: every cost_table row's all-survey price == 1.5x single."""
    for row in _load_cost_table():
        single = row["Credits (single survey)"]
        all_survey = row["Credits (all survey data)"]
        assert all_survey == pytest.approx(single * 1.5), row["Content type"]


def test_all_packs_bundle_equals_seven_single_packs():
    """AI-pack bundle: 'AI (all packs)' == 7 x 'AI (1 pack)' in both price columns."""
    by_type = {r["Content type"]: r for r in _load_cost_table()}
    one, all_packs = by_type["AI (1 pack)"], by_type["AI (all packs)"]
    assert all_packs["Credits (single survey)"] == 7 * one["Credits (single survey)"]     # 35 == 7*5
    assert all_packs["Credits (all survey data)"] == 7 * one["Credits (all survey data)"]  # 52.5 == 7*7.5


def test_rate_table_all_survey_is_1_5x_single():
    """by_area's rate table encodes the 1.5x multi-survey bundle for every resource."""
    for key, rates in cases.RATE_TABLE.items():
        assert rates["Credits (all survey data)"] == pytest.approx(
            rates["Credits (single survey)"] * 1.5
        ), key


def test_by_area_caps_ai_packs_at_seven():
    """AI-pack bundle in by_area: >7 packs costs the same as 7 (the all-packs cap)."""
    ai = sorted(k for k in cases.RATE_TABLE if k.startswith("aiPacks:"))
    area = 1_000_000  # 1 km^2, fixed
    six = estimate_by_area({}, ai[:6], "single", area_sqm=area)
    seven = estimate_by_area({}, ai[:7], "single", area_sqm=area)
    sixteen = estimate_by_area({}, ai[:16], "single", area_sqm=area)
    assert six < seven        # below the cap, cost scales with pack count
    assert sixteen == seven   # at/above the cap, 8..16 packs == 7 packs
