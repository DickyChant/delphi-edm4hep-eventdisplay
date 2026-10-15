"""Small in-memory events; tests never download or open a ROOT sample."""

import numpy as np
import pytest

from delphi_eventdisplay.read import Event
from delphi_eventdisplay.schema import Collection, Schema


@pytest.fixture
def event():
    momentum = np.array([
        [4.0, 0.0, 0.0], [0.0, 1.0, 0.0], [0.0, 0.0, 2.0],
        [-3.0, 0.0, 0.0], [0.0, -2.0, 0.0], [0.0, 0.0, -1.0],
    ])
    roles = {"particles": "TestParticles", "tracks": "TestTracks", "em_clusters": "TestShowers", "jets": "TestJets"}
    schema = Schema(path="/synthetic/axis-event.edm4hep.root", entries=3)
    for name, kind, count in (("TestParticles", "ReconstructedParticle", 8), ("TestTracks", "Track", 6),
                              ("TestShowers", "Cluster", 2), ("TestJets", "ReconstructedParticle", 1)):
        schema.collections[name] = Collection(name=name, type=f"edm4hep::{kind}Collection", kind=kind, count=count)
    e = Event(
        path=schema.path, entry=1, schema=schema, roles=roles,
        gi={"sDST_EVT_runNumber": 42, "sDST_EVT_eventNumber": 17, "sDST_EVT_nCharged": 6, "sDST_EVT_nNeutral": 2},
        gf={"sDST_EVT_BField": np.array([1.2]), "sDST_AABTAG_CombinedTagEvent": np.array([3.4])},
        momentum=momentum, p_abs=np.linalg.norm(momentum, axis=1), charge=np.array([1, -1, 1, -1, 1, -1]),
        par={i: [0.0, 0.0, 0.0, float(np.arctan2(p[1], p[0])), 0.001, float(p[2])] for i, p in enumerate(momentum)},
        pv=np.zeros(3), sh_x=np.array([0.0, 0.0]), sh_y=np.array([10.0, 0.0]),
        sh_z=np.array([0.0, -10.0]), sh_e=np.array([4.0, 1.0]),
        jets=[(1.0, 1.0, 0.0, 16.0)], thrust=np.array([1.0, 2.0, 2.0]) / 3.0,
    )
    for field in ("vd_x", "vd_y", "vd_z", "vd_raw_z", "vd_r", "vd_phi", "vd_type"):
        setattr(e, field, np.array([]))
    return e
