"""Tests for the quote export (feature 4): CSV + JSON with a pricing snapshot.

A quote must be auditable if pricing drifts later, so it embeds the rate snapshot for
the selected resources and a timestamp. Tests pass an explicit timestamp to stay
deterministic.
"""

from __future__ import annotations

import csv
import io
import json

import quote_export
from nearmap_helper import NearMapHelper

SAMPLE = {
    "resources": ["raster:Vert", "aiPacks:building"],
    "area_sqm": 12345.678,
    "tiles": 10,
    "tiles_with_coverage": 8,
    "tiles_no_coverage": 1,
    "tiles_errored": 1,
    "by_api_return": 1450,
    "by_area": 1600,
}
TS = "2026-06-17T00:00:00+00:00"


def test_build_quote_fields_and_layer_count():
    q = quote_export.build_quote(SAMPLE, timestamp=TS)
    assert q["generated_at"] == TS
    assert q["layer_count"] == 2
    assert q["resources"] == ["raster:Vert", "aiPacks:building"]
    assert q["by_api_return_credits"] == 1450
    assert q["by_area_credits"] == 1600
    assert (q["tiles"], q["tiles_with_coverage"], q["tiles_no_coverage"], q["tiles_errored"]) == (10, 8, 1, 1)


def test_pricing_snapshot_only_selected_and_matches_rate_table():
    q = quote_export.build_quote(SAMPLE, timestamp=TS)
    rate = NearMapHelper.get_all_resources()["all_tuples"]
    assert set(q["pricing_snapshot"]) == {"raster:Vert", "aiPacks:building"}
    for key, snap in q["pricing_snapshot"].items():
        assert snap == rate[key]  # exact snapshot of current pricing


def test_quote_json_roundtrips():
    q = quote_export.build_quote(SAMPLE, timestamp=TS)
    assert json.loads(quote_export.quote_to_json(q)) == q


def test_quote_csv_has_totals_and_per_resource_pricing_rows():
    q = quote_export.build_quote(SAMPLE, timestamp=TS)
    rows = list(csv.reader(io.StringIO(quote_export.quote_to_csv(q))))
    flat = {r[0]: r[1] for r in rows if len(r) == 2}
    assert flat["by_api_return_credits"] == "1450"
    assert flat["by_area_credits"] == "1600"
    assert flat["layer_count"] == "2"
    assert flat["generated_at"] == TS
    # a pricing row per selected resource
    assert any(r and r[0] == "raster:Vert" for r in rows)
    assert any(r and r[0] == "aiPacks:building" for r in rows)


def test_build_quote_uses_estimated_at_when_no_timestamp():
    sample = dict(SAMPLE, estimated_at="2026-01-02T03:04:05+00:00")
    q = quote_export.build_quote(sample)  # no explicit timestamp
    assert q["generated_at"] == "2026-01-02T03:04:05+00:00"


def test_quote_reports_polygon_count():
    single = quote_export.build_quote(SAMPLE, timestamp=TS)
    assert single["polygons"] == 1  # defaults to 1 when not a batch
    batch = quote_export.build_quote(dict(SAMPLE, n_polygons=3), timestamp=TS)
    assert batch["polygons"] == 3
    # and it surfaces in the CSV scalar block
    flat = {r[0]: r[1] for r in csv.reader(io.StringIO(quote_export.quote_to_csv(batch))) if len(r) == 2}
    assert flat["polygons"] == "3"
