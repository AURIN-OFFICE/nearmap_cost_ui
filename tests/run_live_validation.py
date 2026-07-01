"""Live validation of the cost estimators against the real Nearmap API.

ALWAYS uses ``preview=true`` -> **no credits are charged** (validated finding T1:
preview cost == actual cost). Requires a Nearmap API key.

Provide the key (matching the ../nearmap repo convention) via either:
  - environment variable ``NEARMAP_API_TOKEN``  (also reads a local ``.env`` if present), or
  - the ``--api-key`` flag.

Checks performed:
  A. Drift vs cached  - re-run a cached single-pack plan live; compare to the
     May-2026 cached total (detects API price/coverage drift).
  B. Mixed-resource sum (caveat D) - on a tiny 1-tile AOI, confirm a combined
     ``raster:Vert,aiPacks:building`` call costs ~= the sum of the two separate calls
     (extends T4, which only covered AI packs).
  C. AI-pack bundle - on a tiny AOI, confirm both by_area and the live by_api_return
     cap at the all-packs price for >7 packs (35 = 7x5); they should agree, not diverge.
  D. Multi-survey bundle - on a tiny AOI, confirm dates=all costs ~1.5x dates=single
     (sublinear; matches T7 and the 1.5x all-survey rate column).

Run:
  python -m tests.run_live_validation
  python -m tests.run_live_validation --api-key XXXX --aoi <path>
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from api_cost_estimation.by_area import estimate_by_area
from api_cost_estimation.estimators import estimate_by_api

from . import cases

OUT = Path(__file__).resolve().parent / "LIVE_REPORT.md"

# A tiny AOI inside the adelaide_sample bbox -> 1 tile -> 1 API call per resource.
TINY_AOI = {
    "type": "Polygon",
    "coordinates": [[
        [138.600, -34.920],
        [138.605, -34.920],
        [138.605, -34.915],
        [138.600, -34.915],
        [138.600, -34.920],
    ]],
}


def resolve_key(cli_key: str | None) -> str | None:
    if cli_key:
        return cli_key
    key = os.getenv("NEARMAP_API_TOKEN")
    if key:
        return key
    # Optional: parse a local .env without adding a python-dotenv dependency.
    env_path = cases._REPO_ROOT / ".env"
    if env_path.exists():
        for line in env_path.read_text().splitlines():
            line = line.strip()
            if line.startswith("NEARMAP_API_TOKEN") and "=" in line:
                return line.split("=", 1)[1].strip().strip('"').strip("'")
    return None


def _run(geometry, resources, key, sleep):
    return estimate_by_api(geometry, resources, key, dates="single", sleep=sleep)


def check_drift(key, aoi_path, sleep, log):
    log("\n## A. Drift vs cached (single pack)\n")
    plan_path = cases.PLANS_DIR / "adelaide_sample_building_preview.json"
    if not plan_path.exists():
        log("  skipped: no cached adelaide_sample_building plan")
        return
    cached_total = cases.load_plan(plan_path)["summary"]["total_estimated_cost_credits"]
    geometry = cases.json.loads(Path(aoi_path).read_text())
    res = _run(geometry, ["aiPacks:building"], key, sleep)
    live = res["total"]
    drift = (live - cached_total) / cached_total * 100 if cached_total else float("nan")
    log(f"| metric | cached (May-2026) | live | drift |")
    log(f"|---|--:|--:|--:|")
    log(f"| credits | {cached_total:,} | {live:,} | {drift:+.2f}% |")
    log(f"| tiles covered | - | {res['tiles_with_coverage']}/{res['tiles']} "
        f"({res['tiles_no_coverage']} no-coverage, {res['tiles_errored']} errored) | |")


def check_mixed(key, sleep, log):
    log("\n## B. Mixed-resource combined-call sum (caveat D)\n")
    raster = _run(TINY_AOI, ["raster:Vert"], key, sleep)["total"]
    building = _run(TINY_AOI, ["aiPacks:building"], key, sleep)["total"]
    combined = _run(TINY_AOI, ["raster:Vert", "aiPacks:building"], key, sleep)["total"]
    expected = raster + building
    verdict = "PASS" if combined == expected else "CHECK"
    log("| raster:Vert | aiPacks:building | sum | combined call | verdict |")
    log("|--:|--:|--:|--:|:--:|")
    log(f"| {raster:,} | {building:,} | {expected:,} | {combined:,} | {verdict} |")
    log("\n(If combined == sum, mixed raster+AI bills as the sum — the assumption the "
        "UI relies on for `by_api_return`.)")


def check_multipack(key, sleep, log):
    log("\n## C. AI-pack bundle — >7 packs cap at the all-packs price\n")
    ai_keys = sorted(k for k in cases.RATE_TABLE if k.startswith("aiPacks:"))
    # Probe each pack alone; keep the ones this account can actually price (entitlements).
    accessible = []
    for k in ai_keys:
        api = _run(TINY_AOI, [k], key, sleep)
        if api["total"] > 0 and api["tiles_errored"] == 0:
            accessible.append(k)
    unavailable = [k.split(":", 1)[1] for k in ai_keys if k not in accessible]
    log(f"Accessible AI packs for this account: **{len(accessible)}/{len(ai_keys)}** "
        f"(unavailable: {', '.join(unavailable) or 'none'}). That gap is the entitlements "
        f"point — by_area would price all {len(ai_keys)} regardless.\n")
    if len(accessible) < 8:
        log("Fewer than 8 accessible packs, so the 7-pack cap can't be exercised live here "
            "(the offline cost-table + by_area tests cover it instead).\n")
        return
    log("| accessible AI packs | by_area | by_api_return (live) | ratio |")
    log("|--:|--:|--:|--:|")
    for n in sorted({1, 7, 8, len(accessible)}):
        selected = accessible[:n]
        api = _run(TINY_AOI, selected, key, sleep)
        ba = estimate_by_area({"type": "Feature", "geometry": TINY_AOI}, selected, "single")
        ratio = ba / api["total"] if api["total"] else float("nan")
        log(f"| {n} | {ba:,} | {api['total']:,} | {ratio:.3f} |")
    log("\n(by_api_return should flatten from 7 packs on — 8+ accessible packs cost the same "
        "as 7, the all-packs bundle cap. by_area caps at 7 too, so ratios stay ~flat.)")


def check_dates(key, sleep, log):
    log("\n## D. Multi-survey bundle — dates=all ≈ 1.5x single\n")
    single = estimate_by_api(TINY_AOI, ["aiPacks:building"], key, dates="single", sleep=sleep)["total"]
    all_d = estimate_by_api(TINY_AOI, ["aiPacks:building"], key, dates="all", sleep=sleep)["total"]
    ratio = all_d / single if single else float("nan")
    log("| dates=single | dates=all | ratio |")
    log("|--:|--:|--:|")
    log(f"| {single:,} | {all_d:,} | {ratio:.3f} |")
    log("\n(Expect ≈ 1.5 — the multi-survey bundle (sublinear: ~1.5x regardless of survey "
        "count, per T7). by_area uses the all-survey rate column (1.5x), so they agree.)")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--api-key", default=None, help="Nearmap API key (else $NEARMAP_API_TOKEN)")
    parser.add_argument("--aoi", default=str(cases.AOIS_DIR / "adelaide_sample_aoi.geojson"),
                        help="AOI geojson for the drift check")
    parser.add_argument("--sleep", type=float, default=0.3, help="inter-call sleep (s)")
    parser.add_argument("--skip-drift", action="store_true", help="skip the 42-call drift check")
    args = parser.parse_args()

    key = resolve_key(args.api_key)
    if not key:
        print("No API key found. Set NEARMAP_API_TOKEN (or a .env), or pass --api-key.")
        print("All checks use preview=true, so no credits would be charged.")
        return 0

    out_lines = []

    def log(msg=""):
        try:
            print(msg)
        except UnicodeEncodeError:
            # Windows consoles default to cp1252; keep unicode in the file, fall back on stdout.
            print(msg.encode("ascii", "replace").decode("ascii"))
        out_lines.append(msg)

    log("# Cost Estimation — Live Validation Report\n")
    log("All calls use `preview=true` — **no credits charged**.\n")

    try:
        if not args.skip_drift:
            check_drift(key, args.aoi, args.sleep, log)
    except Exception as e:
        log(f"  A. drift check failed: {e}")
    try:
        check_mixed(key, args.sleep, log)
    except Exception as e:
        log(f"  B. mixed check failed: {e}")
    try:
        check_multipack(key, args.sleep, log)
    except Exception as e:
        log(f"  C. multipack check failed: {e}")
    try:
        check_dates(key, args.sleep, log)
    except Exception as e:
        log(f"  D. dates check failed: {e}")

    OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
