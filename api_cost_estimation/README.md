# api_cost_estimation

Self-contained cost-estimation module for the Nearmap Cost Estimator UI. It produces
**two** credit estimates for the same AOI + resource selection, shown side by side:

| Estimate | What it is | Source of truth |
|---|---|---|
| **`by_area`** | the original author's manual area-based formula, extracted **unchanged** from `main.py` | local arithmetic over a rate table |
| **`by_api_return`** | tile the AOI to ≤300k sqm, call the Coverage API with `preview=true` per tile, and **sum** `costOfTransaction` | the live Nearmap API |

---

## Why this module exists

The original UI estimated cost with `by_area` only — `rate × area`, with a hard cap of
7 AI packs — and fell back to it whenever a single API call was rejected for being too
large. That formula is a **local guess**: it never asks Nearmap what the request actually
costs. It's a better model than you'd expect — it even reproduces Nearmap's two sublinear
**bundles** (the >7-pack cap and the 1.5× multi-survey price; see validation §3–§4). But it
is **blind to two real-world facts**, and that's where it goes wrong:

### 1. Coastal / partial-coverage AOIs → `by_area` *over*-charges
`by_area` bills the **entire drawn polygon**. But Nearmap charges **nothing** for tiles
with no imagery — ocean, uncovered land, or nothing in your date window. On a real Perth
AOI (~205 km², partly over water):

| resource | `by_area` | `by_api_return` | covered tiles | error |
|---|--:|--:|--:|--:|
| building | 1,025,550 | **823,560** | 428 / 508 | **+25%** |
| surfaces | 1,025,550 | **769,165** | 390 / 508 | **+33%** |

The ~80–118 ocean tiles cost 0 in reality; `by_area` can't see that and bills them anyway.

### 2. Packs your subscription doesn't include → `by_area` invents a cost
`by_area` multiplies `area × rate` for **any** resource you tick — even packs your account
isn't permitted to access (or that aren't a valid Nearmap resource at all). The API rejects
those, e.g. `HTTP 403 {"error":"access to resource namespace trueOrthoAiPacks not permitted"}`
(or `HTTP 400 {"errors":["UNKNOWN_PACK"]}`), so `by_api_return` **flags it** instead of
returning a confident price for data you could never actually order. (Live check: all 25 AI
packs are valid identifiers and priced on the test key; the separate `aiImpactAssessment:postcat`
product returned `403 not permitted`. The former `aiPacks:postcat` entry was dropped — the API
rejects it as `UNKNOWN_PACK`.)

### What `by_area` gets *right*: the pricing bundles
Easy to assume otherwise, so worth stressing: `by_area` correctly models **both** of Nearmap's
sublinear bundles — the **>7-pack cap** (8+ AI packs cost the same as the all-packs bundle,
`35 = 7×5`) and the **1.5× multi-survey** price (`dates=all`). Verified offline and live (§3–§4
of the report), the two agree to ~0.1% on these. **Pack count and survey count are *not* where
`by_area` goes wrong.**

### Why `by_api_return` is the right answer
It is **the number Nearmap actually bills**. It tiles the AOI so no request is ever
rejected for size, queries each tile with `preview=true` (validated to equal the real
charge — T1), and sums. Because the figure comes from the billing engine itself, it
inherently respects everything `by_area` is blind to:

- **coverage gaps** — uncovered/ocean/out-of-date-window tiles are billed 0;
- **request validity & entitlements** — only packs Nearmap recognises *and* your account is
  permitted to access are priced; unavailable / unknown packs are flagged, not silently billed;
- **the 5-credit floor and per-tile rounding to multiples of 5**;
- **any AOI size** — tiling replaces the old "single call → `INVALID_AREA` → fall back to
  guesswork" path.

`by_area` is **kept, unchanged**, only for comparison — its quirks (7-pack cap, plain
`round()`, no floor) are preserved on purpose. Treat it as a rough sanity check; trust
`by_api_return`.

## When do the two actually agree?

**Whenever the AOI is fully covered and you own the packs — for *any* number of packs or
surveys.** They match to ~0.1% (a single pack over Adelaide: 60,820 vs 60,900; the live check
stays flat from 1 → 15 packs). Because `by_area` models both bundles, pack count and survey
count never open a gap on their own.

The two diverge only when `by_area` hits one of its blind spots above: **the AOI includes
ocean / uncovered land** (it over-charges), or **you select packs your account can't access**
(it prices what the API would reject).

## `by_api_return` is better — but not infallible

It needs a live API + key, makes one call per tile (latency), and if a tile **errors**
(timeout, 5xx, rate-limit) it contributes 0 and could undercount. This is surfaced, never
hidden: the UI shows `≥ X` + a warning when any tile errored, and `API error` if nothing
priced. A **`404` (no coverage) is not an error** — it's a genuine $0, so the figure stays
**exact** (see caveat A).

---

## Layout

```
api_cost_estimation/    # the cost-estimation library (UI-free, no test fixtures)
  coverage_fetcher.py   # GDAL-free port of ../nearmap/utils/aipack_transaction.py
                        #   (CoverageFetcher: tiling + tx/poly preview; DataFetcher kept for fidelity)
  by_area.py            # the original manual estimator, preserved as-is
  estimators.py         # estimate_cost() / estimate_by_api() / count_tiles() — UI entry points

tests/                  # all tests + the validation harness + cached fixtures (repo root)
  test_offline.py       # offline assertions (no key, $0)
  cases.py              # shared offline helpers
  generate_report.py    # writes REPORT.md (the validation report)
  run_live_validation.py
  REPORT.md             # generated validation report (committed sample)
  data/
    aois/               # test AOIs copied from ../nearmap (adelaide_sample, perth)
    credit_plans/       # cached preview plans copied from ../nearmap (offline ground truth)
```

## Port note (no GDAL)

`coverage_fetcher.py` reproduces the `../nearmap` tiling algorithm exactly — UTM area
calc, the `n_rows × n_cols` grid, `simplify(0.0001)`, the `GET /coverage/v2/tx/poly`
endpoint — but on **shapely + pyproj** (already installed) instead of `geopandas`/`fiona`,
so **no new runtime dependencies**. The offline test `test_tile_count_reproduced` proves
the GDAL-free tiler produces the same tiles as the original (adelaide_sample → 42,
perth → 508).

## How the UI uses it

`main.py` calls `count_tiles()` first (local, no API) to gate very large jobs, then
`estimate_cost(...)`, which returns `{by_area, by_api_return, tiles, tiles_with_coverage,
tiles_no_coverage, tiles_errored, ...}`. Both estimates use the API key entered in the UI.
Every call is `preview=true`, so **the UI never charges credits**.

## Validation

The evidence + findings (with numbers) live in the generated
**[../tests/REPORT.md](../tests/REPORT.md)**. To run the checks:

```bash
uv run pytest tests/test_offline.py -v              # offline, no key, $0
uv run python -m tests.generate_report              # regenerate REPORT.md
NEARMAP_API_TOKEN=… uv run python -m tests.run_live_validation  # live, preview-only, $0
```

## Caveats baked into the design

- **A — failed tiles vs no-coverage.** A skipped tile contributes 0, but the *reason*
  matters. A `404 SURVEYS_NOT_FOUND` (ocean / outside the date window) is genuinely $0 —
  tracked as `tiles_no_coverage`, and the figure stays **exact**. Any other failure
  (timeout, 5xx, 429, complex-polygon 400) is tracked as `tiles_errored`; only then does
  the UI show `≥ X` (or `API error` if nothing was priced), since those could hide cost.
- **E — latency.** One preview call per tile, fetched **concurrently** (default
  `DEFAULT_MAX_WORKERS` = 8) with exponential backoff on `429` rate-limits, so perth's
  ≈ 508 calls finish well under a minute. The UI gates jobs over `TILE_WARN_THRESHOLD`
  (50 tiles) behind a confirmation and refuses over `TILE_HARD_CAP` (2000). Concurrency
  (`max_workers=`) and the sequential-mode inter-call sleep (`sleep=`) are tunable.
- **G — area engines differ.** `by_area` uses Albers; tiling uses UTM. So reported
  divergence mixes the billing-model difference with a small area-method delta.
- Offline cached plans are single-pack / single-date, so the two bundles (>7-pack cap, 1.5×
  multi-survey) are shown from the rate table + the live script — not the raw cached plans.
