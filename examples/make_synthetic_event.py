#!/usr/bin/env python3
"""Publish a deterministic, hand-built showcase without a ROOT file or EOS access.

This is illustrative synthetic data, not a generated physics sample or a detector
simulation. Six charged particles and four neutral, massless EM showers form two
balanced hemispheres. Opposite particles have opposite momentum; the charged
particles have pion-like masses only when computing the illustrative jet energy.
The helices use a uniform 1.2 T field and start at the origin. There are no vertex
detector hits, displaced vertices, RICH measurements, or b-tag values.

Run from a checkout after ``pip install -e .``::

    python examples/make_synthetic_event.py
    delphi-pages

Only compact figure JSON and a collection-schema sidecar are written. No
Plotly JavaScript, standalone HTML, ROOT inputs, or real-event files are needed.
"""

from __future__ import annotations

import argparse
import base64
import json
import math
from pathlib import Path

import numpy as np

from delphi_eventdisplay.figure import build, build_flow2d
from delphi_eventdisplay.figure3d import build3d, build_flow3d
from delphi_eventdisplay.read import Event
from delphi_eventdisplay.schema import Collection, Schema, to_dict

STEM = "synthetic_flow_demo"
TITLE = "Synthetic two-jet energy-flow demo"
SOURCE = "synthetic in-memory example (no ROOT input)"
NOTE = (
    "SYNTHETIC: hand-built, balanced two-jet illustration; not DELPHI detector data "
    "or a physics simulation. Six charged tracks, four neutral EM showers; "
    "no VD hits, displaced vertices, or RICH measurements. "
    "Jet weights include the particles and showers; do not sum the displayed weights."
)


def make_event() -> Event:
    """Construct the same explicitly synthetic Event on every invocation."""
    charged_half = np.array([[12.0, 5.0, 4.0], [5.0, 4.0, 1.0], [3.0, -1.0, 3.0]])
    neutral_half = np.array([[4.0, 1.0, -1.0], [2.0, 2.0, 2.0]])
    charged = np.concatenate((charged_half, -charged_half))
    neutral = np.concatenate((neutral_half, -neutral_half))
    momentum = np.concatenate((charged, neutral))
    charge = np.array([1, -1, 1, -1, 1, -1, 0, 0, 0, 0])
    b_field, radius = 1.2, 2100.0
    # Neutral showers intersect a cylindrical toy calorimeter along their momentum.
    shower_xyz = neutral * (radius / np.hypot(neutral[:, 0], neutral[:, 1]))[:, None]
    jet_p = charged_half.sum(axis=0) + neutral_half.sum(axis=0)
    jet_e = float(np.sqrt(np.sum(charged_half**2, axis=1) + 0.13957**2).sum()
                  + np.linalg.norm(neutral_half, axis=1).sum())
    roles = {
        "particles": "SyntheticParticles", "tracks": "SyntheticTracks",
        "primary_vertex": "SyntheticPrimaryVertex", "em_clusters": "SyntheticEMShowers",
        "jets": "SyntheticJets",
    }
    schema = Schema(path=SOURCE, entries=1)
    for name, kind, count, links in (
        (roles["particles"], "ReconstructedParticle", len(momentum),
         [("tracks", roles["tracks"]), ("clusters", roles["em_clusters"])]),
        (roles["tracks"], "Track", len(charged), []),
        (roles["primary_vertex"], "Vertex", 1, [("particles", roles["particles"])]),
        (roles["em_clusters"], "Cluster", len(neutral), []),
        (roles["jets"], "ReconstructedParticle", 2, [("particles", roles["particles"])]),
    ):
        schema.collections[name] = Collection(
            name=name, type=f"edm4hep::{kind}Collection", kind=kind, count=count,
            provenance="synthetic hand-built example", domain="synthetic demo", links=links,
        )
    e = Event(
        path=SOURCE, entry=0, schema=schema, roles=roles,
        gi={"sDST_EVT_nCharged": len(charged), "sDST_EVT_nNeutral": len(neutral)},
        gf={"sDST_EVT_BField": np.array([b_field])},
        momentum=momentum, p_abs=np.linalg.norm(momentum, axis=1), charge=charge,
        pv=np.zeros(3), r_em=radius, r_stop=radius,
        sh_x=shower_xyz[:, 0], sh_y=shower_xyz[:, 1], sh_z=shower_xyz[:, 2],
        sh_e=np.linalg.norm(neutral, axis=1),
        jets=[(*jet_p, jet_e), (*-jet_p, jet_e)],
        thrust=jet_p / np.linalg.norm(jet_p),
    )
    for i, (px, py, pz) in enumerate(charged):
        pt = np.hypot(px, py)
        # dphi/ds [1/mm], for q v x B with the field along +z.
        omega = -charge[i] * 0.299792458 * b_field / (1000 * pt)
        e.par[i] = [0.0, 0.0, 0.0, float(np.arctan2(py, px)), float(omega), float(pz / pt)]
    for field in ("vd_x", "vd_y", "vd_z", "vd_raw_z", "vd_r", "vd_phi", "vd_type"):
        setattr(e, field, np.array([]))
    return e


def plain_json(value):
    """Keep coordinates compatible with the site's Plotly.js 2.x.

    Newer plotly.py serializes NumPy arrays as binary typed arrays by default.
    Walk ``Figure.to_dict()`` instead, and use JSON null for curve gaps/NaNs.
    """
    if isinstance(value, np.ndarray):
        return plain_json(value.tolist())
    if isinstance(value, np.generic):
        return plain_json(value.item())
    if isinstance(value, dict):
        if "bdata" in value and "dtype" in value and set(value) <= {"bdata", "dtype", "shape"}:
            array = np.frombuffer(base64.b64decode(value["bdata"]), dtype=value["dtype"])
            if value.get("shape"):
                array = array.reshape(tuple(int(n) for n in value["shape"].split(",")))
            return plain_json(array.tolist())
        return {key: plain_json(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [plain_json(item) for item in value]
    if isinstance(value, float) and not math.isfinite(value):
        return None
    return value


def write_json(path: Path, payload):
    path.write_text(json.dumps(plain_json(payload), separators=(",", ":"), allow_nan=False) + "\n", encoding="utf-8")
    print(f"wrote {path} ({path.stat().st_size / 1000:.1f} kB)")


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    parser.add_argument("--out-dir", type=Path, default=Path(__file__).resolve().parents[1] / "docs" / "events",
                        help="directory for the five synthetic JSON files (default: docs/events in this checkout)")
    args = parser.parse_args(argv)
    args.out_dir.mkdir(parents=True, exist_ok=True)
    e = make_event()
    groups = {i: ("synthetic hemisphere +", "#3769b1") if i < 3
              else ("synthetic hemisphere -", "#c85332") for i in e.par}
    for suffix, view, builder in (
        ("", "panels", build), (".3d", "3d", build3d),
        (".flow2d", "flow2d", build_flow2d), (".flow3d", "flow3d", build_flow3d),
    ):
        figure = builder(e, groups=groups, jets=True, title=TITLE, note=NOTE)
        # Avoid environment-dependent optional plotlyhep styling in the demo.
        figure.update_layout(template="plotly_white")
        for trace in figure.data:
            if trace.meta is None:
                trace.meta = {"role": "", "collection": ""}
        figure.layout.meta = dict(figure.layout.meta or {}, view=view, synthetic=True,
                                  generator="examples/make_synthetic_event.py")
        write_json(args.out_dir / f"{STEM}{suffix}.json", figure.to_dict())
    write_json(args.out_dir / f"{STEM}.schema.json", to_dict(e.schema, e.roles))
    print("Run delphi-pages to refresh the showcase manifest.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
