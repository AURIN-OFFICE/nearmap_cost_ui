"""Tests for the editable layer-availability config (feature 3).

The availability list is deployment config (the tool is account-irrelevant): a JSON
file of ``{resource_key: bool}``. Unknown/new resources default to *available*, so
adding a resource to the rate table later never silently hides it from users.
"""

from __future__ import annotations

import json

import layer_config


def test_load_defaults_all_available_when_no_file(tmp_path):
    path = tmp_path / "layer_availability.json"  # does not exist
    avail = layer_config.load_availability(str(path))
    assert set(avail) == set(layer_config.all_resource_keys())
    assert all(avail.values())  # everything selectable by default


def test_load_merges_new_resources_as_available(tmp_path):
    path = tmp_path / "layer_availability.json"
    # File marks one pack unavailable and omits every other resource.
    path.write_text(json.dumps({"aiPacks:building": False}))
    avail = layer_config.load_availability(str(path))
    assert avail["aiPacks:building"] is False  # respected
    assert avail["raster:Vert"] is True        # omitted -> defaults available
    assert set(avail) == set(layer_config.all_resource_keys())


def test_save_then_load_roundtrip(tmp_path):
    path = tmp_path / "layer_availability.json"
    desired = {k: True for k in layer_config.all_resource_keys()}
    desired["aiPacks:solar"] = False
    layer_config.save_availability(desired, str(path))
    reloaded = layer_config.load_availability(str(path))
    assert reloaded["aiPacks:solar"] is False
    assert reloaded["aiPacks:building"] is True


def test_save_ignores_unknown_keys_and_writes_full_set(tmp_path):
    path = tmp_path / "layer_availability.json"
    layer_config.save_availability(
        {"not:a_real_resource": True, "aiPacks:pool": False}, str(path)
    )
    on_disk = json.loads(path.read_text())
    assert "not:a_real_resource" not in on_disk          # bogus key dropped
    assert on_disk["aiPacks:pool"] is False              # known key persisted
    assert set(on_disk) == set(layer_config.all_resource_keys())  # full known set written


def test_available_resources_excludes_disabled(tmp_path):
    path = tmp_path / "layer_availability.json"
    desired = {k: True for k in layer_config.all_resource_keys()}
    desired["aiPacks:debris"] = False
    layer_config.save_availability(desired, str(path))
    avail = layer_config.available_resources(str(path))
    assert "aiPacks:debris" not in avail
    assert "aiPacks:building" in avail


def test_corrupt_file_falls_back_to_all_available(tmp_path):
    path = tmp_path / "layer_availability.json"
    path.write_text("{ this is not valid json")
    avail = layer_config.load_availability(str(path))
    assert all(avail.values())  # fail-open: never block the user on a bad config
