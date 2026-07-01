"""Tests for human-readable resource labels + catalogue display order (UI presentation).

The data model uses terse keys (``aiPacks:pavement_cond``); the selection UI shows the
Nearmap AI Packs catalogue names, in catalogue order. These are pure lookups, tested
offline and guarded against drift from ``get_all_resources``.
"""

from __future__ import annotations

from nearmap_helper import NearMapHelper
import resource_labels as rl

ALL_KEYS = list(NearMapHelper.get_all_resources()["all_tuples"].keys())

# Exact order from the Nearmap website AI Packs catalogue.
CATALOGUE_ORDER = [
    "aiPacks:building", "aiPacks:building_char", "aiPacks:building_structures",
    "aiPacks:construction", "aiPacks:roof_char", "aiPacks:roof_materials",
    "aiPacks:roof_shape", "aiPacks:roof_objects", "aiPacks:commercial_roof_objects",
    "aiPacks:roof_cond", "aiPacks:advanced_roof_cond", "aiPacks:roof_overhang",
    "aiPacks:trampoline", "aiPacks:solar", "aiPacks:pool", "aiPacks:surfaces",
    "aiPacks:vegetation", "aiPacks:poles", "aiPacks:surface_permeability",
    "aiPacks:pavement_marking", "aiPacks:pavement_cond", "aiPacks:yard_objects",
    "aiPacks:debris", "aiPacks:utilities", "aiPacks:experimental",
]


def test_known_pack_uses_catalogue_name():
    assert rl.label_for("aiPacks:pavement_cond") == "Pavement Condition"
    assert rl.label_for("aiPacks:building") == "Building Footprints"
    assert rl.label_for("aiPacks:advanced_roof_cond") == "Advanced Roof Condition"


def test_unknown_key_falls_back_to_prettified_short_name():
    assert rl.label_for("aiPacks:some_new_pack") == "Some New Pack"


def test_raster_key_is_labelled():
    assert rl.label_for("raster:Vert") == "Vertical Imagery"


def test_every_resource_key_has_an_explicit_label():
    missing = [k for k in ALL_KEYS if k not in rl.LABELS]
    assert missing == []


def test_aipacks_display_order_matches_catalogue():
    assert rl.DISPLAY_ORDER["aiPacks"] == CATALOGUE_ORDER


def test_display_order_covers_exactly_the_aipacks():
    ai = {k for k in ALL_KEYS if k.startswith("aiPacks:")}
    assert set(rl.DISPLAY_ORDER["aiPacks"]) == ai


def test_ordered_keys_sorts_to_catalogue_order():
    scrambled = ["aiPacks:experimental", "aiPacks:building", "aiPacks:roof_shape"]
    assert rl.ordered_keys("aiPacks", scrambled) == [
        "aiPacks:building", "aiPacks:roof_shape", "aiPacks:experimental",
    ]


def test_ordered_keys_appends_unknown_after_known():
    keys = ["aiPacks:zzz_new", "aiPacks:building"]
    assert rl.ordered_keys("aiPacks", keys) == ["aiPacks:building", "aiPacks:zzz_new"]
