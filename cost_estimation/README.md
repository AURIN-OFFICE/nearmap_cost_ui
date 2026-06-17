# cost_estimation

Self-contained cost-estimation module for the Nearmap Cost Estimator UI. It produces
**two** credit estimates for the same AOI + resource selection so they can be compared
side by side in the UI:

| Estimate | What it is | Source of truth |
|---|---|---|
| **`by_area`** | The original author's manual area-based formula (extracted unchanged from `main.py`). | local arithmetic over a rate table |
| **`by_api_return`** | The `../nearmap` method: tile the AOI to ≤300k sqm, call the Coverage API with `preview=true` per tile, and **sum** `costOfTransaction`. | the live Nearmap API |

`by_api_return` is the more correct figure (it's what Nearmap actually bills). `by_area`
is kept for comparison and is **deliberately not "fixed"** — its known quirks (7-AI-pack
cap, plain `round()`, no 5-credit floor) are preserved so the divergence is visible.

## Why `by_api_return` is more correct (validated in `../nearmap`)

- **Tiling.** AOIs over ~300k sqm get `400 INVALID_AREA` from a single call; the original
  UI fell back to manual math for those. This module tiles first, so it gets real API
  numbers even for large areas.
- **Per-pack billing.** Each AI pack is a separate charge (no bundle discount). `by_area`'s
  cap at 7 packs assumes a bundle that `../nearmap` empirically **refuted** — so `by_area`
  under-estimates once >7 packs are selected (see `validation/REPORT.md` §3).
- **5-credit floor + multiple-of-5 quantization per tile** — captured automatically because
  the figure comes straight from the API.

## Layout

```
cost_estimation/
  coverage_fetcher.py   # GDAL-free port of ../nearmap/utils/aipack_transaction.py
                        #   (CoverageFetcher: tiling + tx/poly preview; DataFetcher kept for fidelity)
  by_area.py            # the original manual estimator, preserved as-is
  estimators.py         # estimate_cost() / estimate_by_api() / count_tiles() — UI entry points
  data/
    aois/               # test AOIs copied from ../nearmap (adelaide_sample, perth)
    credit_plans/       # cached preview plans copied from ../nearmap (offline ground truth)
  validation/
    test_offline.py     # pytest: replay cached plans, reproduce tiling, quantization, divergence
    generate_report.py  # writes REPORT.md (by_area vs by_api comparison)
    run_live_validation.py  # optional live preview=true checks (needs a key, $0)
    REPORT.md           # committed sample of the offline comparison
```

## Port note (no GDAL)

`coverage_fetcher.py` reproduces the `../nearmap` tiling algorithm exactly — UTM area
calc, the `n_rows × n_cols` grid, `simplify(0.0001)`, the `GET /coverage/v2/tx/poly`
endpoint — but using **shapely + pyproj** (already installed) instead of
`geopandas`/`fiona`. So **no new runtime dependencies**. The offline test
`test_tile_count_reproduced` proves the GDAL-free tiler produces the same tiles as the
original (adelaide_sample → 42, perth → 508).

## How the UI uses it

`main.py` calls `count_tiles()` first (local, no API) to gate very large jobs, then
`estimate_cost(...)` which returns `{by_area, by_api_return, tiles, tiles_with_coverage,
tiles_failed, ...}`. Both estimates use the API key entered in the UI.

## Validation

### Offline (no key, reproducible, $0)

```bash
uv sync                                                       # runtime + pytest
uv run pytest cost_estimation/validation/test_offline.py -v
uv run python -m cost_estimation.validation.generate_report   # regenerates REPORT.md
```

(With plain pip: `pip install -r requirements-dev.txt`, then drop the `uv run` prefix.)

Offline checks run against the cached `data/credit_plans/*.json` (May-2026 snapshot):
sum-matches-total, tiling reproduction, 5-credit quantization, failed-tile undercount,
and the `by_area` vs `by_api_return` divergence table.

### Live (needs a Nearmap key, preview=true → $0)

```bash
export NEARMAP_API_TOKEN=your_key      # or pass --api-key; a local .env also works
uv run python -m cost_estimation.validation.run_live_validation
```

Live checks: drift vs the cached total, the mixed raster+AI combined-call sum (caveat D),
and the live multi-pack cap-at-7 divergence (caveat C). All calls use `preview=true`, so
**no credits are charged**.

## Caveats baked into the design

- **A — failed tiles undercount.** A tile that errors (e.g. ocean → `404`) contributes 0.
  The result reports `tiles_failed`; the UI shows `≥ X` (and the warning banner) when any
  tile failed, so a silently-low number can't be mistaken for authoritative.
- **E — latency.** One preview call per tile (perth ≈ 508 calls ≈ a few minutes). The UI
  gates jobs over `TILE_WARN_THRESHOLD` (50 tiles) behind a confirmation and refuses over
  `TILE_HARD_CAP` (2000). The `0.5s` inter-call sleep is tunable (`sleep=` arg).
- **G — area engines differ.** `by_area` uses Albers; tiling uses UTM. So reported
  divergence mixes the billing-model difference with a small area-method delta.
- Offline data is single-pack, so the >7-pack divergence is shown via the synthetic
  section of `REPORT.md` and the live script — not the raw cached plans.
