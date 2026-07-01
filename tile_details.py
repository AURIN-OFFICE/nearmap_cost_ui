"""Per-tile detail summary for the click-to-inspect feature.

``summarize_tile`` turns one plan tile record (as stored in
``st.session_state['last_coverage_tiles']``) into a display-ready dict for the panel
below the coverage map. Pure (no Streamlit / no network) so it is unit-tested offline.

A tile record carries ``status`` (covered / no_coverage / errored), the full
``coverage`` API return (``None`` for no_coverage / errored), ``area_sqm``,
``source_polygons`` and — for errored tiles — an ``error`` string. Every field is read
defensively so an unexpected/partial shape never raises in the UI.
"""

from __future__ import annotations

from typing import Any, Dict, List


def _summarize_survey(survey: Dict[str, Any]) -> Dict[str, Any]:
    """One survey -> {id, date, content_types}. Falls back across field names."""
    content_types = survey.get("contentTypes") or survey.get("resources") or []
    return {
        "id": survey.get("id"),
        "date": survey.get("captureDate"),
        "content_types": list(content_types),
    }


def summarize_tile(tile: Dict[str, Any], index: int) -> Dict[str, Any]:
    """Turn a tile record into a display-ready summary.

    Args:
        tile: a plan tile record.
        index: its position in the flattened ``last_coverage_tiles`` list (the tile's
            identity — per-AOI ``tile_id`` is not unique across polygons).

    Returns:
        ``{number, status, credits, area_sqm, source_polygons, surveys, error}`` where
        ``number`` is 1-based for display and ``surveys`` is ``[{id, date, content_types}]``.
    """
    coverage = tile.get("coverage") or {}

    status = tile.get("status")
    if not status:
        status = "covered" if tile.get("coverage") else "no_coverage"

    surveys = [_summarize_survey(s) for s in (coverage.get("surveys") or [])]

    return {
        "number": index + 1,
        "status": status,
        "credits": coverage.get("costOfTransaction") or 0,
        "area_sqm": tile.get("area_sqm", 0.0),
        "source_polygons": tile.get("source_polygons", []),
        "surveys": surveys,
        "error": tile.get("error"),
    }
