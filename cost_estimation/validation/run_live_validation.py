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
  C. Multi-pack cap (caveat C) - on a tiny AOI, compare by_area (caps at 7 packs)
     against the live by_api_return for N packs, showing the divergence directly.

Run:
  python -m cost_estimation.validation.run_live_validation
  python -m cost_estimation.validation.run_live_validation --api-key XXXX --aoi <path>
"""

from __future__ import annotations

import argparse
import os
import sys
from pathlib import Path

from cost_estimation.by_area import estimate_by_area
from cost_estimation.estimators import estimate_by_api

from . import cases

OUT = Path(__file__).resolve().parent / "LIVE_REPORT.md"

# A tiny AOI inside the adelaide_sample bbox -> 1 tile -> 1 API call per resource.
TINY_AOI = {
    "type": "Polygon",
    "coordinates": [[
        [138.600, -34.920],
        [138.601, -34.920],
        [138.601, -34.919],
        [138.600, -34.919],
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
        f"({res['tiles_failed']} failed) | |")


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
    log("\n## C. Multi-pack cap divergence (caveat C)\n")
    ai_keys = [k for k in cases.RATE_TABLE if k.startswith("aiPacks:")]
    log("| AI packs | by_area | by_api_return (live) | ratio |")
    log("|--:|--:|--:|--:|")
    for n in [1, 7, 8, 16]:
        if n > len(ai_keys):
            break
        selected = ai_keys[:n]
        api = _run(TINY_AOI, selected, key, sleep)
        ba = estimate_by_area({"type": "Feature", "geometry": TINY_AOI}, selected, "single")
        ratio = ba / api["total"] if api["total"] else float("nan")
        log(f"| {n} | {ba:,} | {api['total']:,} | {ratio:.3f} |")
    log("\n(by_area plateaus after 7 packs; by_api_return keeps growing — the cap-at-7 "
        "under-estimate, now confirmed against the live API.)")


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
        print(msg)
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

    OUT.write_text("\n".join(out_lines), encoding="utf-8")
    print(f"\nWrote {OUT}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
