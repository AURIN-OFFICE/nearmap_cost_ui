"""Quote export (feature 4): turn an ``estimate_cost`` result into CSV / JSON.

The quote is meant for procurement and must stay auditable if Nearmap pricing drifts
later, so it embeds a **pricing snapshot** (the rate-table rows for the selected
resources) plus a timestamp. CSV and JSON only — no PDF (no extra dependency).
"""

from __future__ import annotations

import csv
import io
import json
from datetime import datetime, timezone
from typing import Dict, List, Optional

from nearmap_helper import NearMapHelper

# Fields rendered as simple key,value rows in the CSV (and present in the JSON).
_SCALAR_FIELDS: List[str] = [
    "generated_at",
    "polygons",
    "layer_count",
    "area_sqm",
    "tiles",
    "tiles_with_coverage",
    "tiles_no_coverage",
    "tiles_errored",
    "by_api_return_credits",
    "by_area_credits",
]


def build_quote(
    result: Dict,
    *,
    timestamp: Optional[str] = None,
    rate_table: Optional[Dict] = None,
) -> Dict:
    """Assemble an auditable quote dict from an ``estimate_cost`` result.

    ``timestamp`` (ISO-8601) defaults to ``result['estimated_at']`` if present, else
    now (UTC). ``pricing_snapshot`` captures the rate-table rows for the selected
    resources so the quote can be reconciled later even if pricing changes.
    """
    resources = list(result.get("resources", []))
    if rate_table is None:
        rate_table = NearMapHelper.get_all_resources()["all_tuples"]
    generated_at = timestamp or result.get("estimated_at") or datetime.now(timezone.utc).isoformat()

    return {
        "generated_at": generated_at,
        "polygons": result.get("n_polygons", 1),
        "resources": resources,
        "layer_count": len(resources),
        "area_sqm": round(float(result.get("area_sqm", 0) or 0), 2),
        "tiles": result.get("tiles", 0),
        "tiles_with_coverage": result.get("tiles_with_coverage", 0),
        "tiles_no_coverage": result.get("tiles_no_coverage", 0),
        "tiles_errored": result.get("tiles_errored", 0),
        "by_api_return_credits": result.get("by_api_return", 0),
        "by_area_credits": result.get("by_area", 0),
        "pricing_snapshot": {r: rate_table[r] for r in resources if r in rate_table},
    }


def quote_to_json(quote: Dict) -> str:
    """Pretty-printed JSON of the quote."""
    return json.dumps(quote, indent=2)


def quote_to_csv(quote: Dict) -> str:
    """Procurement-friendly CSV: scalar key/value rows, then a per-resource pricing block."""
    buf = io.StringIO()
    writer = csv.writer(buf)
    writer.writerow(["field", "value"])
    for field in _SCALAR_FIELDS:
        writer.writerow([field, quote.get(field, "")])
    writer.writerow(["resources", "; ".join(quote.get("resources", []))])

    writer.writerow([])  # blank separator row
    writer.writerow(["resource", "credits_single_survey", "credits_all_survey", "content_type"])
    for resource, rates in quote.get("pricing_snapshot", {}).items():
        writer.writerow([
            resource,
            rates.get("Credits (single survey)"),
            rates.get("Credits (all survey data)"),
            rates.get("matched_content_type"),
        ])
    return buf.getvalue()
