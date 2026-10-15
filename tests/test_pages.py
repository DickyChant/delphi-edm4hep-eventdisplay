"""The manifest must advertise flow sidecars without counting them as events."""

import json

import pytest

from delphi_eventdisplay.pages import build_index, main


def write_figure(path, *, view=None, title="Synthetic event"):
    meta = {"run": 42, "event": 17, "entry": 1, "source": "input.root", "title": title}
    if view is not None:
        meta["view"] = view
    path.write_text(json.dumps({"data": [], "layout": {"meta": meta}}))


def test_manifest_lists_all_sidecars_once(tmp_path):
    events = tmp_path / "events"
    events.mkdir()
    write_figure(events / "sample.json")
    for suffix in ("3d", "flow2d", "flow3d"):
        write_figure(events / f"sample.{suffix}.json", view=suffix)
    (events / "sample.schema.json").write_text('{"collections": {}}')
    (events / "index.json").write_text('{"events": []}')
    index = build_index(tmp_path)
    assert len(index["events"]) == 1
    item = index["events"][0]
    assert item["key"] == "sample" and item["file"] == "events/sample.json"
    assert item["title"] == "run 42, event 17 — Synthetic event"
    for key, suffix in (("schema", "schema"), ("figure3d", "3d"), ("figureflow2d", "flow2d"), ("figureflow3d", "flow3d")):
        assert item[key] == f"events/sample.{suffix}.json"
        assert (tmp_path / item[key]).is_file()
    assert main(["--docs", str(tmp_path)]) == 0
    assert json.loads((events / "index.json").read_text()) == index


def test_missing_sidecars_remain_optional_and_orphans_are_not_events(tmp_path):
    events = tmp_path / "events"
    events.mkdir()
    write_figure(events / "sample.json")
    for suffix in ("3d", "flow2d", "flow3d"):
        write_figure(events / f"orphan.{suffix}.json", view=suffix)
    (events / "orphan.schema.json").write_text('{}')
    item, = build_index(tmp_path)["events"]
    assert item["key"] == "sample"
    assert all(item[key] is None for key in ("schema", "figure3d", "figureflow2d", "figureflow3d"))


@pytest.mark.parametrize("view", ["3d", "flow2d", "flow3d"])
def test_standalone_views_are_base_events(tmp_path, view):
    events = tmp_path / "events"
    events.mkdir()
    write_figure(events / "sample.json", view=view)
    item, = build_index(tmp_path)["events"]
    assert item["file"] == "events/sample.json"
    assert item["key"] == "sample"


def test_invalid_json_does_not_block_valid_events(tmp_path, capsys):
    events = tmp_path / "events"
    events.mkdir()
    (events / "broken.json").write_text('{')
    write_figure(events / "valid.json")
    item, = build_index(tmp_path)["events"]
    assert item["key"] == "valid"
    assert "skipping broken.json" in capsys.readouterr().err
