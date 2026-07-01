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


# --- tile_at_point: map a clicked (lat, lon) back to a tile index (click-to-inspect) ---

# Two adjacent unit squares: A = lon[0,1], B = lon[1,2], both lat[0,1].
_TILE_A = {"geometry": _poly(0, 0, 1, 1)}
_TILE_B = {"geometry": _poly(1, 0, 2, 1)}


def test_tile_at_point_inside_first_tile_returns_its_index():
    # signature is (tiles, lat, lon); point lon=0.5, lat=0.5 is inside A
    assert map_helper.tile_at_point([_TILE_A, _TILE_B], 0.5, 0.5) == 0


def test_tile_at_point_inside_second_tile_returns_its_index():
    assert map_helper.tile_at_point([_TILE_A, _TILE_B], 0.5, 1.5) == 1


def test_tile_at_point_outside_all_tiles_returns_none():
    assert map_helper.tile_at_point([_TILE_A, _TILE_B], 5.0, 5.0) is None


def test_tile_at_point_empty_list_returns_none():
    assert map_helper.tile_at_point([], 0.5, 0.5) is None


def test_tile_at_point_overlapping_tiles_return_first_match():
    big = {"geometry": _poly(0, 0, 3, 3)}
    inner = {"geometry": _poly(1, 1, 2, 2)}
    # point in both -> first in list order wins (deterministic)
    assert map_helper.tile_at_point([big, inner], 1.5, 1.5) == 0


def test_tile_at_point_skips_invalid_geometry():
    bad = {"geometry": None}
    assert map_helper.tile_at_point([bad, _TILE_A], 0.5, 0.5) == 1
