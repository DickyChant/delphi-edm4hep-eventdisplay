"""Run the real CLI/builders/export path against an in-memory Event."""

import json

import pytest

from delphi_eventdisplay import cli


@pytest.mark.parametrize(("view", "expected"), [
    (None, {"": None}),
    ("panels", {"": None}),
    ("3d", {"": "3d"}),
    ("flow2d", {"": "flow2d"}),
    ("flow3d", {"": "flow3d"}),
    ("both", {"": None, ".3d": "3d"}),
    ("all", {"": None, ".3d": "3d", ".flow2d": "flow2d", ".flow3d": "flow3d"}),
])
def test_cli_emitted_filenames_and_metadata(event, monkeypatch, tmp_path, view, expected):
    source = tmp_path / "input.edm4hep.root"
    source.touch()  # Only CLI existence validation uses this; the reader is replaced below.
    event.path = str(source)
    event.schema.path = str(source)
    reads = []

    def read_event(path, entry, **kwargs):
        reads.append((path, entry, kwargs))
        return event

    monkeypatch.setattr(cli, "n_entries", lambda _path: 3)
    monkeypatch.setattr(cli, "read_event", read_event)
    out = tmp_path / "out" / "sample.html"
    args = [str(source), "--entry", "1", "--out", str(out), "--cdn", "--quiet", "--width", "720", "--height", "640",
            "--title", "Synthetic CLI event", "--note", "No ROOT data", "--domains", str(tmp_path / "missing.json")]
    if view is not None:
        args += ["--view", view]
    assert cli.main(args) == 0
    assert reads == [(str(source), 1, {"collections": {}, "domains": {}})]
    expected_files = {"sample.schema.json"}
    for suffix, mode in expected.items():
        expected_files.update({f"sample{suffix}.html", f"sample{suffix}.json"})
        exported = json.loads(out.with_suffix(f"{suffix}.json").read_text())
        meta = exported["layout"]["meta"]
        assert meta.get("view") == mode
        assert {key: meta[key] for key in ("run", "event", "entry", "source", "title", "note")} == {
            "run": 42, "event": 17, "entry": 1, "source": "input.edm4hep.root",
            "title": "Synthetic CLI event", "note": "No ROOT data",
        }
        html = out.with_suffix(f"{suffix}.html").read_text()
        assert "Plotly.newPlot" in html and "Synthetic CLI event" in html
        assert "cdn.plot.ly" in html
        if mode in ("flow2d", "flow3d"):
            assert any(t.get("meta", {}).get("role") == "jets" for t in exported["data"])
            assert (exported["layout"]["width"], exported["layout"]["height"]) == (720, 640)
    assert {p.name for p in out.parent.iterdir()} == expected_files
    schema = json.loads(out.with_suffix(".schema.json").read_text())
    assert schema["roles"] == event.roles
    assert schema["collections"]["TestTracks"]["count"] == 6


@pytest.mark.parametrize("view", ["flow2d", "flow3d", "all"])
def test_cli_flow_group_and_hide_options(event, monkeypatch, tmp_path, view):
    source = tmp_path / "input.root"
    source.touch()
    monkeypatch.setattr(cli, "n_entries", lambda _path: 3)
    monkeypatch.setattr(cli, "read_event", lambda *_args, **_kwargs: event)
    out = tmp_path / "sample.html"
    assert cli.main([str(source), "--entry", "1", "--out", str(out), "--view", view, "--cdn", "--quiet",
                     "--require-vd", "--group", "chosen:#123456:0,1"]) == 0
    for suffix in ([".flow2d", ".flow3d"] if view == "all" else [""]):
        figure = json.loads(out.with_suffix(f"{suffix}.json").read_text())
        tracks = [t for t in figure["data"] if t.get("meta", {}).get("role") == "tracks"]
        assert tracks
        assert all(t["legendgroup"] == "g:chosen" for t in tracks)
        assert all(t["marker"]["color"] == "#123456" for t in tracks)
        hovers = [t.get("text", t.get("hovertemplate", "")) for t in tracks]
        text = " ".join(value if isinstance(value, str) else " ".join(value) for value in hovers)
        assert "<b>track 0</b>" in text and "<b>track 1</b>" in text
        assert all(f"<b>track {i}</b>" not in text for i in (2, 3, 4, 5))
