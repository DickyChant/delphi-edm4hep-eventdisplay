"""Geometry and collection-selection contracts for the two energy-flow views."""

import copy
import json

import numpy as np
import pytest

import delphi_eventdisplay as display
from delphi_eventdisplay.figure import build_flow2d
from delphi_eventdisplay.figure3d import build_flow3d
from delphi_eventdisplay.read import Event

BUILDERS = [build_flow2d, build_flow3d]


def by_role(fig, role):
    return [trace for trace in fig.data if (trace.meta or {}).get("role") == role]


def text_of(trace):
    text = trace.text if isinstance(trace.text, str) else " ".join(trace.text or [])
    return text + (trace.hovertemplate or "")


def points3d(trace):
    return np.array([trace.x, trace.y, trace.z], dtype=float).T


def assert_finite_coordinates(fig):
    for trace in fig.data:
        for axis in ("x", "y", "z"):
            values = getattr(trace, axis, None)
            if values is not None:
                assert np.isfinite(np.asarray(values, dtype=float)).all(), (trace.name, axis)
    # Serialization should not hide nonfinite coordinate values as nulls.
    assert json.loads(fig.to_json())["layout"]["meta"]["view"] in ("flow2d", "flow3d")


def test_public_builders():
    assert display.build_flow2d is build_flow2d
    assert display.build_flow3d is build_flow3d
    assert {"build", "build3d", "build_flow2d", "build_flow3d"} <= set(display.__all__)


@pytest.mark.parametrize("builder", BUILDERS)
def test_metadata_and_collection_roles(event, builder):
    fig = builder(event, title="Synthetic event", note="No ROOT sample", width=720, height=640)
    expected_meta = {
        "run": 42, "event": 17, "entry": 1, "source": "axis-event.edm4hep.root",
        "n_charged": 6, "n_neutral": 2, "b_field": 1.2, "btag": 3.4,
        "title": "Synthetic event", "note": "No ROOT sample", "view": builder.__name__.removeprefix("build_"),
    }
    assert {key: fig.layout.meta[key] for key in expected_meta} == expected_meta
    assert (fig.layout.width, fig.layout.height) == (720, 640)
    assert fig.layout.showlegend is True
    for trace in fig.data:
        assert trace.meta is not None
        role = trace.meta["role"]
        assert trace.meta["collection"] == event.roles.get(role, "")
    for role in ("tracks", "em_clusters", "jets"):
        assert by_role(fig, role)


def test_flow2d_marker_area_and_minimum_size(event):
    # A common reference includes the 16 GeV jet, so areas can be compared
    # across tracks and clusters. Jets deliberately have a larger scale.
    event.p_abs[5] = 1e-6
    fig = build_flow2d(event)
    tracks = sorted(by_role(fig, "tracks"), key=lambda t: t.meta["object_index"])
    em = sorted(by_role(fig, "em_clusters"), key=lambda t: t.meta["object_index"])
    jets = by_role(fig, "jets")
    sizes = [trace.marker.size[-1] for trace in tracks]
    np.testing.assert_allclose(sizes, np.maximum(4, 22 * np.sqrt(event.p_abs / 16)))
    np.testing.assert_allclose([t.marker.size[-1] for t in em], [11.0, 5.5])
    np.testing.assert_allclose([t.marker.size[-1] for t in jets], [40.0])
    assert sizes[0] ** 2 / sizes[1] ** 2 == pytest.approx(4.0)
    assert sizes[-1] == 4.0
    for trace in tracks + em + jets:
        assert trace.marker.sizemode in (None, "diameter")


def test_flow3d_unit_sphere_quills_and_equal_ranges(event):
    fig = build_flow3d(event)
    sphere, = [t for t in fig.data if t.type == "surface"]
    radii = np.sqrt(np.asarray(sphere.x) ** 2 + np.asarray(sphere.y) ** 2 + np.asarray(sphere.z) ** 2)
    np.testing.assert_allclose(radii, 1.0, atol=1e-12)
    for i, trace in enumerate(by_role(fig, "tracks")):
        points = points3d(trace)
        u = event.momentum[i] / event.p_abs[i]
        np.testing.assert_allclose(points[0], u, atol=1e-12)
        np.testing.assert_allclose(points[1], u * (1 + 0.9 * np.sqrt(event.p_abs[i] / 16)), atol=1e-12)
    for k, trace in enumerate(by_role(fig, "em_clusters")):
        points = points3d(trace)
        u = np.array([event.sh_x[k], event.sh_y[k], event.sh_z[k]]) / 10
        np.testing.assert_allclose(points[0], u, atol=1e-12)
        assert np.linalg.norm(points[1] - points[0]) == pytest.approx(0.9 * np.sqrt(event.sh_e[k] / 16))
    jet, = by_role(fig, "jets")
    points = points3d(jet)
    np.testing.assert_allclose(points[0], [1 / np.sqrt(2), 1 / np.sqrt(2), 0])
    assert np.linalg.norm(points[1] - points[0]) == pytest.approx(1.3 * 0.9)
    thrust, = [t for t in fig.data if t.legendgroup == "thrust"]
    np.testing.assert_allclose(points3d(thrust), [-1.35 * event.thrust, 1.35 * event.thrust])
    assert thrust.line.dash == "dash"
    scene = fig.layout.scene
    assert scene.aspectmode == "cube"
    assert scene.xaxis.range is not None
    assert tuple(scene.xaxis.range) == tuple(scene.yaxis.range) == tuple(scene.zaxis.range)
    lo, hi = scene.xaxis.range
    assert lo == -hi and hi >= 2.17
    assert_finite_coordinates(fig)


def test_flow3d_clean_scene_and_camera_consistent_axis_labels(event):
    fig = build_flow3d(event)
    scene = fig.layout.scene
    assert scene.bgcolor == "white"
    for axis in (scene.xaxis, scene.yaxis, scene.zaxis):
        assert axis.visible is False
        assert axis.showbackground is axis.showgrid is axis.zeroline is False
        assert axis.showline is axis.showticklabels is False
        assert axis.ticks == "" and axis.title.text == ""
    # Scene-space annotations are projected by the same camera as the sphere.
    assert [label.text for label in scene.annotations] == ["+x", "+y", "+z"]
    np.testing.assert_allclose([[a.x, a.y, a.z] for a in scene.annotations], 1.08 * np.eye(3))
    assert all(label.showarrow is False for label in scene.annotations)
    key, = fig.layout.annotations
    assert key.xref == key.yref == "paper" and key.y > 1
    assert "axis key:" in key.text and "z = beam" in key.text


@pytest.mark.parametrize("builder", BUILDERS)
def test_groups_hide_and_disabled_jets(event, builder):
    fig = builder(event, groups={0: ("highlighted pair", "#ff0000"), 1: ("highlighted pair", "#ff0000")},
                  hide={2: "hidden for this view"}, jets=False)
    assert not by_role(fig, "jets")
    tracks = by_role(fig, "tracks")
    assert not any("<b>track 2</b>" in text_of(t) for t in tracks)
    assert all(any(f"<b>track {i}</b>" in text_of(t) for t in tracks) for i in [0, 1, 3, 4, 5])
    highlighted = [t for t in tracks if t.legendgroup == "g:highlighted pair"]
    assert highlighted
    assert sum(bool(t.showlegend) for t in highlighted) == 1
    assert all(t.marker.color == "#ff0000" for t in highlighted)
    assert all(t.meta["collection"] == "TestTracks" for t in highlighted)


def test_hidden_objects_and_disabled_jets_do_not_set_scale(event):
    event.p_abs[0] = 1000.0
    fig = build_flow2d(event, hide={0: True}, jets=False)
    em = sorted(by_role(fig, "em_clusters"), key=lambda t: t.meta["object_index"])
    # Remaining maximum is the 4 GeV EM cluster.
    np.testing.assert_allclose([t.marker.size[-1] for t in em], [22.0, 11.0])
    fig3d = build_flow3d(event, hide={0: True}, jets=False)
    em3d = by_role(fig3d, "em_clusters")[0]
    points = points3d(em3d)
    assert np.linalg.norm(points[1] - points[0]) == pytest.approx(0.9)


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("direction", [[0.0, 0.0, 0.0], [np.nan, 1.0, 0.0], [0.0, np.inf, 0.0]])
def test_invalid_directions_are_omitted_and_do_not_set_scale(event, builder, direction):
    event.momentum[0] = direction
    event.p_abs[0] = 1e9
    event.sh_x[0], event.sh_y[0], event.sh_z[0] = direction
    event.sh_e[0] = 1e9
    event.jets = [(*direction, 1e9)]
    event.thrust = np.asarray(direction)
    fig = builder(event)
    assert not by_role(fig, "jets")
    assert not any(t.legendgroup == "thrust" for t in fig.data)
    assert not any("<b>track 0</b>" in text_of(t) for t in by_role(fig, "tracks"))
    assert not any("<b>EM cluster 0</b>" in text_of(t) for t in by_role(fig, "em_clusters"))
    assert by_role(fig, "tracks") and by_role(fig, "em_clusters")
    if builder is build_flow2d:
        em, = by_role(fig, "em_clusters")
        assert em.marker.size[-1] == pytest.approx(22 / np.sqrt(3))
    else:
        em, = by_role(fig, "em_clusters")
        points = points3d(em)
        assert np.linalg.norm(points[1] - points[0]) == pytest.approx(0.9 / np.sqrt(3))
    assert_finite_coordinates(fig)


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("magnitude", [-1.0, np.nan, np.inf])
def test_invalid_magnitudes_are_omitted(event, builder, magnitude):
    event.p_abs[0] = magnitude
    event.sh_e[0] = magnitude
    event.jets = [(1.0, 0.0, 0.0, magnitude)]
    fig = builder(event)
    assert not by_role(fig, "jets")
    assert not any("<b>track 0</b>" in text_of(t) for t in by_role(fig, "tracks"))
    assert not any("<b>EM cluster 0</b>" in text_of(t) for t in by_role(fig, "em_clusters"))
    assert_finite_coordinates(fig)


@pytest.mark.parametrize("builder", BUILDERS)
@pytest.mark.parametrize("use_none", [False, True])
def test_empty_optional_data_is_safe(event, builder, use_none):
    for field in ("sh_x", "sh_y", "sh_z", "sh_e"):
        setattr(event, field, None if use_none else np.array([]))
    event.jets = []
    event.thrust = None if use_none else np.zeros(3)
    fig = builder(event)
    assert by_role(fig, "tracks")
    assert not by_role(fig, "jets")
    assert not by_role(fig, "em_clusters")
    assert not any(t.legendgroup == "thrust" for t in fig.data)
    assert_finite_coordinates(fig)


@pytest.mark.parametrize("builder", BUILDERS)
def test_minimal_empty_event_is_safe(builder):
    fig = builder(Event(path="empty.root", entry=0))
    assert not any(by_role(fig, role) for role in ("tracks", "em_clusters", "jets"))
    assert_finite_coordinates(fig)


@pytest.mark.parametrize("builder", BUILDERS)
def test_zero_magnitudes_have_finite_visible_markers(event, builder):
    event.p_abs[:] = 0
    event.sh_e[:] = 0
    event.jets = [(1.0, 0.0, 0.0, 0.0)]
    fig = builder(event)
    for role in ("tracks", "em_clusters", "jets"):
        assert by_role(fig, role)
        for trace in by_role(fig, role):
            if builder is build_flow2d:
                assert trace.marker.size[-1] == 4.0
            else:
                points = points3d(trace)
                np.testing.assert_allclose(points[0], points[1])
                assert trace.marker.size[-1] > 0
    assert_finite_coordinates(fig)


@pytest.mark.parametrize("builder", BUILDERS)
def test_building_does_not_mutate_event_or_options(event, builder):
    before = copy.deepcopy(event)
    groups, hide = {0: ("chosen", "#123456")}, {1: "hidden"}
    builder(event, groups=groups, hide=hide)
    for field in ("momentum", "p_abs", "sh_x", "sh_y", "sh_z", "sh_e", "thrust"):
        np.testing.assert_array_equal(getattr(event, field), getattr(before, field))
    assert event.par == before.par and event.jets == before.jets and event.roles == before.roles
    assert groups == {0: ("chosen", "#123456")} and hide == {1: "hidden"}


@pytest.mark.parametrize("builder", BUILDERS)
def test_json_coordinates_are_browser_compatible_arrays(event, builder):
    # The published site can read these on Plotly.js 2.x too: plotly.py 6's
    # binary numpy-array encoding requires JS 3.x and must not leak into flow JSON.
    exported = json.loads(builder(event).to_json())
    for trace in exported["data"]:
        for axis in ("x", "y", "z"):
            if axis in trace:
                assert isinstance(trace[axis], list), (trace["name"], axis)
