"""The published demo is reproducible, portable and unmistakably synthetic."""

import json
import runpy
from pathlib import Path

import numpy as np


def test_synthetic_showcase(tmp_path):
    example = runpy.run_path(str(Path(__file__).parents[1] / "examples" / "make_synthetic_event.py"))
    event = example["make_event"]()
    np.testing.assert_allclose(event.momentum.sum(axis=0), np.zeros(3), atol=1e-12)
    assert event.run is None and event.event is None
    assert len(event.par) == 6 and len(event.sh_e) == 4
    assert example["main"](["--out-dir", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("*.json"))) == 5
    for suffix, view in (("", "panels"), (".3d", "3d"), (".flow2d", "flow2d"), (".flow3d", "flow3d")):
        raw = (tmp_path / f"synthetic_flow_demo{suffix}.json").read_text()
        fig = json.loads(raw, parse_constant=lambda value: (_ for _ in ()).throw(ValueError(value)))
        meta = fig["layout"]["meta"]
        assert meta["synthetic"] is True and meta["view"] == view
        assert "Synthetic" in meta["title"] and "not DELPHI" in meta["note"]
        assert "synthetic" in meta["source"] and meta["run"] is None
        assert '"bdata"' not in raw
        assert all("collection" in trace.get("meta", {}) for trace in fig["data"])
