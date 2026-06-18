"""Editable layer-availability config (feature 3).

The tool is account-irrelevant, so "which packs are orderable" is *deployment* config,
not something probed per API key. It lives in a JSON file (``layer_availability.json``
in the repo root, which ships inside the Docker image) mapping each resource key to a
boolean. The "Manage layers" dialog in the UI reads/writes it, and the resource
checkboxes disable any layer set to ``False``.

Design choices:
- Unknown / newly-added resources default to **available**, so extending the rate table
  never silently hides a layer.
- A missing or corrupt file fails *open* (everything available) — a bad config must
  never block a user from estimating.

Persistence note: runtime edits update the JSON inside the running container (or a
mounted volume). To make a change permanent across image rebuilds / a Streamlit Cloud
redeploy, commit the updated ``layer_availability.json`` (or mount a volume).
"""

from __future__ import annotations

import json
import os
from typing import Dict, List

from nearmap_helper import NearMapHelper

# The config file ships with the repo (and therefore the Docker image).
DEFAULT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "layer_availability.json")


def all_resource_keys() -> List[str]:
    """Every known resource key, e.g. ``raster:Vert``, ``aiPacks:building``."""
    return list(NearMapHelper.get_all_resources()["all_tuples"].keys())


def load_availability(path: str = DEFAULT_PATH) -> Dict[str, bool]:
    """Return ``{resource_key: bool}`` for every known resource.

    Resources absent from the file (or the whole file missing/corrupt) default to
    ``True`` (available), so the result always covers the full known resource set.
    """
    stored: Dict[str, object] = {}
    if os.path.exists(path):
        try:
            with open(path) as f:
                loaded = json.load(f)
            if isinstance(loaded, dict):
                stored = loaded
        except (json.JSONDecodeError, OSError, ValueError):
            stored = {}  # fail open
    return {key: bool(stored.get(key, True)) for key in all_resource_keys()}


def save_availability(availability: Dict[str, bool], path: str = DEFAULT_PATH) -> Dict[str, bool]:
    """Persist availability for the full known resource set (sorted, pretty-printed).

    Unknown keys in ``availability`` are dropped; known keys not supplied default to
    ``True``. Returns the cleaned mapping that was written.
    """
    known = set(all_resource_keys())
    clean = {key: bool(availability.get(key, True)) for key in known}
    with open(path, "w") as f:
        json.dump(dict(sorted(clean.items())), f, indent=2)
    return clean


def available_resources(path: str = DEFAULT_PATH) -> List[str]:
    """Known resource keys currently marked available."""
    return [key for key, ok in load_availability(path).items() if ok]
