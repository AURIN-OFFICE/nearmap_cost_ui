"""Tests for the coverage-overlay helpers (feature 2).

The folium rendering itself (show_coverage) is thin UI glue; the testable logic is the
status->colour map, the per-tile tooltip text, and the bounding box used to frame the
overlay map.
"""

from __future__ import annotations

import map_helper


def _poly(minlon, minlat, maxlon, maxlat):
    return {
        "type": "Polygon",
        "coordinates": [[
            [minlon, minlat], [maxlon, minlat], [maxlon, maxlat],
            [minlon, maxlat], [minlon, minlat],
        ]],
    }


def test_status_colors_cover_three_distinct_outcomes():
    colors = map_helper.STATUS_COLORS
    assert set(colors) == {"covered", "no_coverage", "errored"}
    assert len(set(colors.values())) == 3  # visually distinguishable


def test_tooltip_covered_shows_credits():
    tip = map_helper.coverage_tile_tooltip({"status": "covered", "coverage": {"costOfTransaction": 1450}})
    assert "covered" in tip.lower()
    assert "1,450" in tip  # thousands-separated credits


def test_tooltip_no_coverage_and_errored_are_described():
    assert "no coverage" in map_helper.coverage_tile_tooltip(
        {"status": "no_coverage", "coverage": None}
    ).lower()
    assert "error" in map_helper.coverage_tile_tooltip(
        {"status": "errored", "coverage": None}
    ).lower()


def test_coverage_bounds_spans_all_tiles():
    tiles = [
        {"geometry": _poly(138.60, -34.92, 138.61, -34.91)},
        {"geometry": _poly(138.62, -34.95, 138.63, -34.94)},
    ]
    # (min_lat, min_lon, max_lat, max_lon) for folium fit_bounds
    assert map_helper.coverage_bounds(tiles) == (-34.95, 138.60, -34.91, 138.63)


def test_coverage_bounds_none_when_empty():
    assert map_helper.coverage_bounds([]) is None
