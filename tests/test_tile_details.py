"""Tests for the per-tile detail summary (click-to-inspect feature).

``summarize_tile`` turns one plan tile record (as stored in
``st.session_state['last_coverage_tiles']``) into a display-ready dict for the panel
below the coverage map. It is pure (no Streamlit) so it is tested offline, with fixtures
mirroring the real ``/coverage/v2/tx/poly`` shape (``coverage.surveys[].contentTypes`` is
a list of resource strings; ``coverage.costOfTransaction`` is an int).
"""

from __future__ import annotations

from tile_details import summarize_tile

_GEOM = {"type": "Polygon", "coordinates": [[[0, 0], [0, 1], [1, 1], [1, 0], [0, 0]]]}

COVERED_TILE = {
    "tile_id": 0,
    "source_polygons": [0],
    "status": "covered",
    "coverage": {
        "surveys": [
            {
                "id": "b04a42be",
                "captureDate": "2026-03-03",
                "contentTypes": ["aiPacks:building", "raster:Vert"],
            }
        ],
        "costOfTransaction": 1270,
    },
    "geometry": _GEOM,
    "area_sqm": 298410.0,
}

NO_COVERAGE_TILE = {
    "tile_id": 1,
    "source_polygons": [0],
    "status": "no_coverage",
    "coverage": None,
    "geometry": _GEOM,
    "area_sqm": 1000.0,
}

ERRORED_TILE = {
    "tile_id": 2,
    "source_polygons": [1],
    "status": "errored",
    "coverage": None,
    "error": "HTTP 500 boom",
    "geometry": _GEOM,
    "area_sqm": 1000.0,
}


def test_covered_tile_summary_has_credits_area_and_number():
    s = summarize_tile(COVERED_TILE, 0)
    assert s["number"] == 1  # 1-based for humans
    assert s["status"] == "covered"
    assert s["credits"] == 1270
    assert s["area_sqm"] == 298410.0
    assert s["source_polygons"] == [0]
    assert s["error"] is None


def test_number_is_one_based_index():
    assert summarize_tile(COVERED_TILE, 6)["number"] == 7


def test_covered_tile_lists_surveys_with_date_and_content_types():
    s = summarize_tile(COVERED_TILE, 0)
    assert s["surveys"] == [
        {
            "id": "b04a42be",
            "date": "2026-03-03",
            "content_types": ["aiPacks:building", "raster:Vert"],
        }
    ]


def test_no_coverage_tile_has_zero_credits_and_no_surveys():
    s = summarize_tile(NO_COVERAGE_TILE, 3)
    assert s["number"] == 4
    assert s["status"] == "no_coverage"
    assert s["credits"] == 0
    assert s["surveys"] == []
    assert s["error"] is None


def test_errored_tile_surfaces_error_string():
    s = summarize_tile(ERRORED_TILE, 0)
    assert s["status"] == "errored"
    assert s["credits"] == 0
    assert s["surveys"] == []
    assert s["error"] == "HTTP 500 boom"


def test_status_derived_when_missing_and_coverage_present():
    tile = {k: v for k, v in COVERED_TILE.items() if k != "status"}
    assert summarize_tile(tile, 0)["status"] == "covered"


def test_status_derived_when_missing_and_coverage_absent():
    tile = {"source_polygons": [0], "coverage": None, "geometry": _GEOM, "area_sqm": 5.0}
    assert summarize_tile(tile, 0)["status"] == "no_coverage"


def test_survey_without_content_types_does_not_crash():
    tile = {
        "status": "covered",
        "source_polygons": [0],
        "coverage": {"surveys": [{"id": "x", "captureDate": "2026-01-01"}], "costOfTransaction": 5},
        "geometry": _GEOM,
        "area_sqm": 1.0,
    }
    s = summarize_tile(tile, 0)
    assert s["surveys"] == [{"id": "x", "date": "2026-01-01", "content_types": []}]


def test_multiple_surveys_all_summarized():
    tile = {
        "status": "covered",
        "source_polygons": [0],
        "coverage": {
            "surveys": [
                {"id": "a", "captureDate": "2026-03-03", "contentTypes": ["aiPacks:building"]},
                {"id": "b", "captureDate": "2025-06-01", "contentTypes": ["raster:Vert"]},
            ],
            "costOfTransaction": 15,
        },
        "geometry": _GEOM,
        "area_sqm": 1.0,
    }
    s = summarize_tile(tile, 0)
    assert [r["id"] for r in s["surveys"]] == ["a", "b"]
    assert [r["date"] for r in s["surveys"]] == ["2026-03-03", "2025-06-01"]
