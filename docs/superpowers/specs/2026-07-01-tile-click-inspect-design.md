# Click-to-inspect coverage tiles — design

**Date:** 2026-07-01
**Status:** Approved (brainstorm) — ready for implementation plan

## Summary

After an estimation is submitted, the coverage map shows one colour-coded tile per API
call. Today those tiles are hover-only. This feature lets the user **click a tile (or pick
it from a fallback selector) and see exactly what the Nearmap coverage API returned for
it** — status, credits, area, per-survey details, and the full raw JSON — in a panel below
the map.

## Goals

- Click a tile → see its API return in a readable panel below the map.
- Show a friendly **summary** (status, credits, area, surveys) **plus** a collapsible
  **raw API response** (JSON).
- No new API calls: everything is read from the data already cached in `session_state`
  from the estimation run.
- Keep the logic in small, offline-testable pure functions.

## Non-goals

- No re-querying the API on click (preview data is already cached per tile).
- No editing/redrawing of tiles.
- No changes to the estimation, pricing, or tiling logic.

## Current state (what we build on)

- `run_estimation` (`main.py`) persists `st.session_state['last_coverage_tiles']` — a flat
  list of tile records. Each record already contains everything needed:
  - `status`: `"covered" | "no_coverage" | "errored"`
  - `coverage`: the full `/coverage/v2/tx/poly` JSON (`costOfTransaction`, `surveys[]`) for
    covered tiles; `None` for no_coverage/errored.
  - `geometry` (GeoJSON), `area_sqm`, `source_polygons`, and `error` (for errored tiles).
- `map_helper.py::BoxDrawer.show_coverage()` draws each tile as a colour-coded
  `folium.GeoJson` with a hover tooltip, then calls
  `st_folium(..., returned_objects=[], key="coverage_map")` — so **clicks are currently
  discarded**. This is the one call that changes.
- The flattened `last_coverage_tiles` merges per-polygon plans whose `tile_id`s each restart
  at 0, so per-AOI `tile_id` is **not** unique. Identity is therefore the **flattened list
  index**.

## Design

### Component 1 — `tile_details.py` (new): `summarize_tile(tile, index) -> dict`

Pure function, no Streamlit. Turns one tile record into a display-ready dict:

```
{
  "number": index + 1,            # 1-based, for humans ("Tile #3")
  "status": "covered" | "no_coverage" | "errored",
  "credits": int,                 # coverage.costOfTransaction, else 0
  "area_sqm": float,
  "source_polygons": [int, ...],
  "surveys": [                    # empty unless covered
    {"date": str, "content_types": [str, ...], "id": str}
  ],
  "error": str | None,           # errored tiles only
}
```

Defensive `.get()` everywhere: missing `coverage`, missing `surveys`, a survey lacking
`contentTypes` (fall back to `resources`), etc. never raise. This is the logic core and is
fully unit-tested.

### Component 2 — `map_helper.py`: `tile_at_point(tiles, lat, lon) -> int | None`

Pure function. Builds shapely geometries from tile `geometry` and returns the flattened
index of the **first** tile whose polygon contains `(lon, lat)`, or `None` if the click hit
no tile.

### Component 3 — `map_helper.py`: `show_coverage(...)` changes

- Include the tile number in the tooltip: `"Tile #3 · covered · 1,270 credits"` so the map
  and the panel correlate.
- Capture interaction and return it:
  `return st_folium(m, ..., returned_objects=["last_object_clicked", "last_clicked"], key=key)`
  (currently returns `None` and discards interactions).
- Remains read-only (no Draw controls).

### Component 4 — `main.py`: wiring (right column, immediately after the map)

1. `result = BoxDrawer(height=500).show_coverage(coverage_tiles, key="coverage_map")`
2. Derive the clicked point from `result`: prefer `last_object_clicked`, else `last_clicked`
   (safety net). Each carries `{lat, lng}`.
3. If a point exists → `idx = tile_at_point(coverage_tiles, lat, lng)`; if `idx is not None`
   → `st.session_state['selected_tile_index'] = idx`. A click on empty map (idx `None`)
   leaves the current selection unchanged.
4. **Fallback selector**: `st.selectbox("Inspect tile #", options=range(len(tiles)),
   format_func=…)` showing `#N — status`. It is **seeded** via `index=selected_tile_index`
   under its **own** widget key (e.g. `"tile_select_box"`), and its return value is written
   back to `selected_tile_index`. It does **not** share the click-set session key — that
   would trigger Streamlit's "cannot modify a widget's state after instantiation" error, the
   same gotcha the code already documents for checkboxes (`main.py:329-333`). Guarantees the
   feature works even if a map click is finicky.
5. If a valid selection exists → render the detail panel (Component 5). Otherwise show a
   hint: *"Click a tile (or pick one below) to see the API details."*

### Component 5 — detail panel (Streamlit rendering in `main.py`)

Given `summary = summarize_tile(tile, idx)` and the raw `tile`:

- **Header:** `Tile #N · {status} · {credits} credits` and a caption with area (m²) and
  source polygon(s).
- **covered:** a surveys table (`st.dataframe`) — capture date + content types per survey.
- **no_coverage:** info message *"No survey coverage — billed $0 (ocean / outside date
  range)."*
- **errored:** the `error` string in `st.warning`.
- **Always:** expander **"Raw API response"** → `st.json(tile['coverage'])` when present,
  else `st.json({"status": ..., "error": ...})`.

### Data flow & state

```
estimation → last_coverage_tiles (session)
   → show_coverage() renders map, returns click
   → tile_at_point() → selected_tile_index (session)
   → summarize_tile() → detail panel
```

- st_folium's rerun on click drives the loop; the map re-renders from cached tiles — **no
  API calls**.
- `selected_tile_index` is **cleared when a new estimation runs** (in `run_estimation`) and
  when the AOI/coverage is cleared (alongside the existing `pop('last_coverage_tiles')`), so
  a stale index never points at the wrong tile.
- If a stored index is out of range for the current tile list, treat it as no selection.

## Edge cases

- Click on empty background / ocean gap → `tile_at_point` returns `None` → selection
  unchanged.
- New estimation with fewer tiles → selection cleared, no stale pointer.
- `coverage is None` (no_coverage / errored) → panel renders status/error; raw view shows
  `{status, error}`.
- Duplicate per-AOI `tile_id`s → sidestepped by using the flattened index as identity.
- Survey objects with varying fields → `summarize_tile` degrades gracefully.

## Testing

**Offline pytest** (no API/key, matches existing `tests/` style):
- `summarize_tile`: covered tile with 1+ surveys → correct credits/date/content types;
  no_coverage → status + 0 credits, empty surveys; errored → error surfaced; tile with
  missing/edge fields → no crash.
- `tile_at_point`: point inside a tile → its index; point outside all tiles → `None`;
  adjacent tiles → deterministic first match.
- Fixtures mirror the real coverage-JSON shape (`surveys[].contentTypes`,
  `costOfTransaction`).

**Manual live check** ("let's test it"): run the Streamlit app, estimate a small AOI, click
tiles and confirm the panel matches the map; verify a no_coverage tile and the fallback
selector.

## Files touched

- `tile_details.py` — new (pure `summarize_tile`).
- `map_helper.py` — add `tile_at_point`; update `show_coverage` (tooltip number, capture &
  return click).
- `main.py` — click→tile wiring, fallback selector, detail panel; clear selection on new
  estimation / AOI clear.
- `tests/test_tile_details.py` (or extend an existing offline test module) — unit tests.
