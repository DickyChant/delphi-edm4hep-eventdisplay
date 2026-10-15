"""Orthographic sphere geometry and truthful encodings for the 2D flow view."""

import json

import numpy as np
import pytest

from delphi_eventdisplay.figure import build_flow2d
from delphi_eventdisplay.read import Event

RIGHT = np.array([-1.0, 1.0, 0.0]) / np.sqrt(2.0)
UP = np.array([-1.0 / np.sqrt(8.0), -1.0 / np.sqrt(8.0), np.sqrt(3.0) / 2.0])
EYE = np.array([np.sqrt(3.0 / 8.0), np.sqrt(3.0 / 8.0), 0.5])


def objects(fig, role):
    return {trace.meta["object_index"]: trace for trace in fig.data if trace.meta["role"] == role}


def endpoint(trace):
    return np.array([trace.x[-1], trace.y[-1]])


def test_known_basis_vectors_project_with_fixed_orthographic_viewpoint(event):
    fig = build_flow2d(event)
    tracks = objects(fig, "tracks")
    expected = [
        [-1 / np.sqrt(2), -1 / np.sqrt(8)],
        [1 / np.sqrt(2), -1 / np.sqrt(8)],
        [0, np.sqrt(3) / 2],
        [1 / np.sqrt(2), 1 / np.sqrt(8)],
        [-1 / np.sqrt(2), 1 / np.sqrt(8)],
        [0, -np.sqrt(3) / 2],
    ]
    for i, xy in enumerate(expected):
        np.testing.assert_allclose(endpoint(tracks[i]), xy, atol=1e-14)
        assert (tracks[i].x[0], tracks[i].y[0]) == (0.0, 0.0)
    np.testing.assert_allclose(endpoint(objects(fig, "jets")[0]), [0, -0.5], atol=1e-14)
    assert "az 45°" in fig.layout.annotations[0].text
    assert "el 30°" in fig.layout.annotations[0].text


def test_positive_depth_faces_viewer_and_rear_is_dashed_faded(event):
    fig = build_flow2d(event)
    tracks = objects(fig, "tracks")
    for i in range(6):
        trace = tracks[i]
        front = i < 3
        assert trace.meta["hemisphere"] == ("front" if front else "rear")
        assert (trace.meta["depth"] > 0) == front
        assert trace.line.dash == ("solid" if front else "dash")
        assert all(trace.meta["hemisphere"] in text for text in trace.text)
        assert endpoint(trace) @ endpoint(trace) + trace.meta["depth"] ** 2 == pytest.approx(1.0)
    assert tracks[0].opacity > tracks[3].opacity > 0
    # Occluded objects are drawn before visible ones, independently of index.
    hemispheres = [t.meta["hemisphere"] for t in fig.data if t.meta["role"]]
    assert hemispheres == sorted(hemispheres, key=lambda s: s == "front")


def test_camera_normal_has_zero_projected_length_but_visible_endpoint(event):
    event.momentum[0] = 7 * EYE
    event.momentum[1] = -7 * EYE
    event.p_abs[:2] = 7.0
    tracks = objects(build_flow2d(event), "tracks")
    for i, depth in ((0, 1), (1, -1)):
        np.testing.assert_allclose(endpoint(tracks[i]), [0, 0], atol=1e-14)
        assert tracks[i].meta["depth"] == pytest.approx(depth)
        assert tracks[i].marker.size[-1] > 0


def test_silhouette_is_unit_circle_and_equator_has_correct_front_back(event):
    fig = build_flow2d(event)
    silhouette, = [t for t in fig.data if t.meta.get("component") == "silhouette"]
    np.testing.assert_allclose(np.asarray(silhouette.x) ** 2 + np.asarray(silhouette.y) ** 2, 1.0, atol=1e-14)
    for trace in (t for t in fig.data if t.meta.get("component") == "equator"):
        x, y = np.array(trace.x), np.array(trace.y)
        np.testing.assert_allclose(x * x + (y / 0.5) ** 2, 1.0, atol=1e-14)
        if trace.meta["hemisphere"] == "front":
            assert np.max(y) < 1e-14
            assert trace.line.dash == "solid"
        else:
            assert np.min(y) > -1e-14
            assert trace.line.dash == "dash"
    for trace in fig.data:
        if trace.meta["role"]:
            assert np.linalg.norm(endpoint(trace)) <= 1.0 + 1e-14
    assert fig.layout.yaxis.scaleanchor == "x"
    assert fig.layout.yaxis.scaleratio == 1
    assert fig.layout.xaxis.range == fig.layout.yaxis.range
    for axis in (fig.layout.xaxis, fig.layout.yaxis):
        assert axis.visible is axis.showticklabels is axis.showgrid is axis.zeroline is False
        assert axis.title.text == "" and axis.ticks == ""
        assert axis.constrain == "domain"
    assert fig.layout.paper_bgcolor == fig.layout.plot_bgcolor == "white"


def test_marker_area_encodes_magnitude_and_ray_length_only_direction(event):
    event.p_abs[5] = 1e-6
    fig = build_flow2d(event)
    tracks = objects(fig, "tracks")
    for i, trace in tracks.items():
        assert trace.marker.size[-1] == pytest.approx(max(4, 22 * np.sqrt(event.p_abs[i] / 16)))
        assert trace.marker.size[0] == 0
        assert trace.marker.sizemode == "diameter"
    assert tracks[0].marker.size[-1] ** 2 / tracks[1].marker.size[-1] ** 2 == pytest.approx(4)
    assert [t.marker.size[-1] for t in objects(fig, "em_clusters").values()] == pytest.approx([5.5, 11.0])
    assert objects(fig, "jets")[0].marker.size[-1] == pytest.approx(40)
    old = endpoint(tracks[0])
    event.p_abs[0] *= 1000
    np.testing.assert_allclose(endpoint(objects(build_flow2d(event), "tracks")[0]), old)


def test_thrust_is_an_antipodal_direction_pair(event):
    fig = build_flow2d(event)
    traces = [t for t in fig.data if t.meta.get("component") == "thrust"]
    assert len(traces) == 2
    for trace in traces:
        direction = trace.meta["sign"] * event.thrust
        np.testing.assert_allclose(endpoint(trace), [direction @ RIGHT, direction @ UP])
        assert trace.meta["depth"] == pytest.approx(direction @ EYE)
        assert trace.marker.symbol == "star"
        assert trace.x[0] == trace.y[0] == 0
    np.testing.assert_allclose(endpoint(traces[0]), -endpoint(traces[1]))
    assert sum(bool(t.showlegend) for t in traces) == 1


def test_collection_tags_highlights_hiding_and_legend_are_preserved(event):
    fig = build_flow2d(event, groups={0: ("chosen pair", "#123456"), 3: ("chosen pair", "#123456")},
                       hide={2: True}, jets=False)
    tracks = objects(fig, "tracks")
    assert set(tracks) == {0, 1, 3, 4, 5}
    assert not objects(fig, "jets")
    for trace in fig.data:
        assert trace.meta["collection"] == event.roles.get(trace.meta["role"], "")
    for i in (0, 3):
        assert tracks[i].marker.color == tracks[i].line.color == "#123456"
        assert tracks[i].legendgroup == "g:chosen pair"
        assert tracks[i].meta["collection"] == "TestTracks"
    assert sum(bool(tracks[i].showlegend) for i in (0, 3)) == 1


@pytest.mark.parametrize("direction", [[0, 0, 0], [np.nan, 1, 0], [0, np.inf, 0]])
def test_invalid_directions_do_not_appear_or_change_marker_scale(event, direction):
    event.momentum[0] = direction
    event.p_abs[0] = 1e9
    event.sh_x[0], event.sh_y[0], event.sh_z[0] = direction
    event.sh_e[0] = 1e9
    event.jets = [(*direction, 1e9)]
    event.thrust = np.asarray(direction)
    fig = build_flow2d(event)
    assert 0 not in objects(fig, "tracks")
    assert set(objects(fig, "em_clusters")) == {1}
    assert not objects(fig, "jets")
    assert not any(t.meta.get("component") == "thrust" for t in fig.data)
    assert objects(fig, "em_clusters")[1].marker.size[-1] == pytest.approx(22 / np.sqrt(3))
    for trace in fig.data:
        assert np.isfinite(trace.x).all() and np.isfinite(trace.y).all()


@pytest.mark.parametrize("magnitude", [-1.0, np.nan, np.inf])
def test_invalid_magnitudes_are_omitted_without_nonfinite_json(event, magnitude):
    event.p_abs[0] = event.sh_e[0] = magnitude
    event.jets = [(1, 0, 0, magnitude)]
    fig = build_flow2d(event)
    assert 0 not in objects(fig, "tracks")
    assert 0 not in objects(fig, "em_clusters")
    assert not objects(fig, "jets")
    for trace in fig.data:
        assert np.isfinite(trace.x).all() and np.isfinite(trace.y).all()
    json.loads(fig.to_json())


def test_zero_magnitudes_and_empty_event_still_draw_finite_sphere(event):
    event.p_abs[:] = event.sh_e[:] = 0
    event.jets = [(1.0, 0, 0, 0)]
    fig = build_flow2d(event)
    for trace in fig.data:
        if trace.meta["role"]:
            assert trace.marker.size[-1] == 4
    empty = build_flow2d(Event(path="empty.root", entry=0))
    assert all(not trace.meta["role"] for trace in empty.data)
    assert any(t.meta.get("component") == "silhouette" for t in empty.data)
    for trace in empty.data:
        assert np.isfinite(trace.x).all() and np.isfinite(trace.y).all()


def test_all_projection_coordinates_and_sizes_serialize_as_plain_arrays(event):
    exported = json.loads(build_flow2d(event).to_json())
    for trace in exported["data"]:
        assert isinstance(trace["x"], list) and isinstance(trace["y"], list)
        assert np.isfinite(trace["x"]).all() and np.isfinite(trace["y"]).all()
        if "marker" in trace:
            assert isinstance(trace["marker"]["size"], list)
