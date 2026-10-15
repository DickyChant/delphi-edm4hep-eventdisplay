"""The event as a 3-D scene, the way a general-purpose event display shows it.

Same rule as the panels: only measured quantities. That rule bites hardest here.
A vertex-detector hit is a *strip*, not a space point -- a type-0 hit measures R and
phi but not z, a type-1 hit measures R and z but not phi -- so in three dimensions a
single hit is a line, not a dot. Hits that belong to a track are placed at the z (or
phi) their own track supplies, which is a real measurement; hits belonging to no track
are drawn as the line they actually constrain, not as invented points.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go

from . import geometry as G
from ._flow import objects, unit_direction
from .figure import GREY, HITC, HPCC, JETC, PVC, SHOWER, SHOWER_SCALE, SVC, VDC, logo_image
from .read import Event

ZLIM = 3000.0
QUILL = 0.9  # largest ordinary quill, relative to the unit-sphere radius
AXIS = dict(backgroundcolor="#fbfbfa", gridcolor="#e3e5e8", zerolinecolor="#cfd3d8",
            tickfont=dict(size=10), title=dict(font=dict(size=12)))


def _template3d():
    """plotlyhep's look, but at a font scale that suits a 3-D scene.

    The CMS template is built for a 1000 px square figure and its ~26 px ticks swamp a
    3-D scene's axes, so the scale is dropped and the scene axes set their own fonts."""
    try:
        import plotlyhep as php

        return php.template("CMS", scale=0.4)
    except Exception:
        return "plotly_white"


def _cylinder(r: float, z0: float, z1: float, n: int = 72):
    """Parametric barrel surface at radius r between z0 and z1."""
    th = np.linspace(0, 2 * np.pi, n)
    x = r * np.cos(th)[None, :] * np.ones((2, 1))
    y = r * np.sin(th)[None, :] * np.ones((2, 1))
    z = np.array([[z0], [z1]]) * np.ones((1, n))
    return x, y, z


def build3d(
    e: Event,
    *,
    groups: dict | None = None,
    fit_vertices: list | None = None,
    hide: dict | None = None,
    jets: bool = False,
    title: str = "",
    note: str = "",
    show_barrel: bool = True,
    width: int = 1250,
    height: int = 900,
) -> go.Figure:
    groups = groups or {}
    fit_vertices = fit_vertices or []
    hide = hide or {}

    sign, _ = G.curvature_sign(e)
    vtx = dict(e.sv_tracks)
    for xv, ids, _r in fit_vertices:
        for i in ids:
            vtx[i] = xv
    s0, s_pv, _ = G.start_points(e, vtx, sign)

    drawn = [i for i in e.par if i not in hide]
    order = sorted(drawn, key=lambda i: i in groups)
    roles = getattr(e, "roles", {}) or {}
    fig = go.Figure()
    seen = set()

    def once(k):
        first = k not in seen
        seen.add(k)
        return first

    # ---------------- detector barrels
    if show_barrel:
        zvd = (float(np.nanmin(e.vd_z)), float(np.nanmax(e.vd_z))) if len(e.vd_z) else (-100.0, 100.0)
        for r in e.vd_layers:
            x, y, z = _cylinder(r, *zvd)
            fig.add_trace(go.Surface(x=x, y=y, z=z, showscale=False, opacity=0.18,
                                     colorscale=[[0, VDC], [1, VDC]], hoverinfo="skip",
                                     name="VD layers", showlegend=once("vd"), legendgroup="vd",
                                     meta={"role": "vd_hits", "collection": roles.get("vd_hits", "")}))
        x, y, z = _cylinder(e.r_em, -ZLIM * 0.75, ZLIM * 0.75)
        fig.add_trace(go.Surface(x=x, y=y, z=z, showscale=False, opacity=0.05,
                                 colorscale=[[0, HPCC], [1, HPCC]], hoverinfo="skip",
                                 name=f"HPC barrel, r = {e.r_em/1000:.2f} m", showlegend=once("hpc"), legendgroup="hpc",
                                 meta={"role": "em_clusters", "collection": roles.get("em_clusters", "")}))
        # beam line
        fig.add_trace(go.Scatter3d(x=[0, 0], y=[0, 0], z=[-ZLIM, ZLIM], mode="lines",
                                   line=dict(color="#c9ced6", width=2), hoverinfo="skip",
                                   name="beam axis", showlegend=once("beam"), legendgroup="beam"))

    # ---------------- tracks
    for i in order:
        col, lw = (groups[i][1], 5) if i in groups else (GREY, 2)
        lab = groups[i][0] if i in groups else "other charged tracks"
        grp = f"g:{groups[i][0]}" if i in groups else "trkother"
        q, p = int(e.charge[i]), float(e.p_abs[i])
        nvd = len(e.track_hits.get(i, []))
        where = "secondary vertex" if i in e.sv_tracks else "primary vertex / perigee"
        hov = f"<b>track {i}</b><br>q = {q:+d}<br>p = {p:.2f} GeV<br>VD hits: {nvd}<br>starts at the {where}"
        x, y, z, _r = G.track_to(e.par[i], e.r_stop, sign, n=400, s0=s0[i])
        k = int(np.argmax(np.abs(z) > ZLIM)) if np.any(np.abs(z) > ZLIM) else len(z)
        fig.add_trace(go.Scatter3d(x=x[:k], y=y[:k], z=z[:k], mode="lines",
                                   line=dict(color=col, width=lw), name=lab, legendgroup=grp,
                                   showlegend=once(grp), hovertemplate=hov + "<extra></extra>",
                                   meta={"role": "tracks", "collection": roles.get("tracks", "")}))
        if i in s_pv and s_pv[i] < s0[i] - 1e-6:
            xb, yb, zb = G.helix(e.par[i], np.linspace(s_pv[i], s0[i], 120), sign)
            fig.add_trace(go.Scatter3d(x=xb, y=yb, z=zb, mode="lines",
                                       line=dict(color=col, width=max(2, lw // 2), dash="dot"),
                                       name="back-extrapolation to the IP", legendgroup="back",
                                       showlegend=once("back"), hoverinfo="text",
                                       text=f"track {i}: back-extrapolation, not a travelled path",
                                       meta={"role": "tracks", "collection": roles.get("tracks", "")}))

    # ---------------- EM showers, towers pointing outward from the IP
    xs, ys, zs, txt = [], [], [], []
    for x0, y0, z0, en in zip(e.sh_x, e.sh_y, e.sh_z, e.sh_e):
        v = np.array([x0, y0, z0], float)
        u = v / (np.linalg.norm(v) or 1.0)
        w = v + SHOWER_SCALE * en * u
        xs += [v[0], w[0], None]; ys += [v[1], w[1], None]; zs += [v[2], w[2], None]
        txt += [f"EM shower, E = {en:.2f} GeV"] * 2 + [None]
    if xs:
        fig.add_trace(go.Scatter3d(x=xs, y=ys, z=zs, mode="lines", line=dict(color=SHOWER, width=9),
                                   name="EM shower (length ∝ energy)", legendgroup="em",
                                   showlegend=once("em"), hoverinfo="text", text=txt,
                                   meta={"role": "em_clusters", "collection": roles.get("em_clusters", "")}))

    # ---------------- vertex-detector hits: a strip is a line in 3-D
    hidden = {j for i in hide for j in e.track_hits.get(i, [])}
    z_of_hit, own_col = {}, {}
    sgrid = np.linspace(-50.0, 400.0, 9001)
    for i in drawn:
        xs_, ys_, zs_ = G.helix(e.par[i], sgrid, sign)
        rs = np.hypot(xs_, ys_)
        for j in e.track_hits.get(i, []):
            if e.vd_r[j] <= 0:
                continue
            k = int(np.argmin(np.abs(rs - e.vd_r[j])))
            z_of_hit[j] = float(zs_[k])          # z comes from the track, which does measure it
            if i in groups:
                own_col[j] = groups[i][1]
    rphi = [j for j in np.where(~np.isnan(e.vd_x))[0] if j not in hidden]
    placed = [j for j in rphi if j in z_of_hit]
    if placed:
        fig.add_trace(go.Scatter3d(
            x=e.vd_x[placed], y=e.vd_y[placed], z=[z_of_hit[j] for j in placed], mode="markers",
            marker=dict(size=[5 if j not in own_col else 7 for j in placed],
                        color=[own_col.get(j, HITC) for j in placed],
                        line=dict(color="black", width=1)),
            name="VD R-φ hit (z from its track)", legendgroup="hits", showlegend=once("hits"),
            hoverinfo="text", text=[f"VD R-φ hit, R = {e.vd_r[j]:.1f} mm<br>z taken from its own track" for j in placed],
            meta={"role": "vd_hits", "collection": roles.get("vd_hits", "")}))
    # hits on no track constrain only a line parallel to the beam
    loose = [j for j in rphi if j not in z_of_hit]
    if loose:
        zspan = (float(np.nanmin(e.vd_z)), float(np.nanmax(e.vd_z))) if len(e.vd_z) else (-60.0, 60.0)
        lx, ly, lz = [], [], []
        for j in loose:
            lx += [e.vd_x[j], e.vd_x[j], None]; ly += [e.vd_y[j], e.vd_y[j], None]; lz += [zspan[0], zspan[1], None]
        fig.add_trace(go.Scatter3d(x=lx, y=ly, z=lz, mode="lines",
                                   line=dict(color=HITC, width=2), opacity=0.55,
                                   name="VD R-φ hit on no track (z unmeasured)", legendgroup="hitsloose",
                                   showlegend=once("hitsloose"), hoverinfo="text",
                                   text="VD R-φ strip: R and φ measured, z is not",
                                   meta={"role": "vd_hits", "collection": roles.get("vd_hits", "")}))

    # ---------------- vertices
    fig.add_trace(go.Scatter3d(x=[e.pv[0]], y=[e.pv[1]], z=[e.pv[2]], mode="markers",
                               marker=dict(symbol="cross", size=5, color=PVC),
                               name="primary vertex (IP)", legendgroup="pv", showlegend=once("pv"),
                               hoverinfo="text", text=f"primary vertex<br>({e.pv[0]:.3f}, {e.pv[1]:.3f}, {e.pv[2]:.3f}) mm",
                               meta={"role": "primary_vertex", "collection": roles.get("primary_vertex", "")}))
    for k, v in enumerate(e.svs):
        fig.add_trace(go.Scatter3d(x=[v[0]], y=[v[1]], z=[v[2]], mode="markers",
                                   marker=dict(symbol="circle-open", size=7, color=SVC, line=dict(color=SVC, width=3)),
                                   name="reconstructed secondary vertex", legendgroup="sv", showlegend=once("sv"),
                                   hoverinfo="text",
                                   text=f"secondary vertex {k}<br>{np.linalg.norm(v - e.pv):.2f} mm from the PV",
                                   meta={"role": "secondary_vertices", "collection": roles.get("secondary_vertices", "")}))

    if jets:
        for jx, jy, jz, je in e.jets:
            if je < 5:
                continue
            u = np.array([jx, jy, jz], float); u /= np.linalg.norm(u) or 1.0
            L = e.r_em + 330
            fig.add_trace(go.Scatter3d(x=[0, L*u[0]], y=[0, L*u[1]], z=[0, L*u[2]], mode="lines",
                                       line=dict(color="#444", width=3, dash="dash"), opacity=0.55,
                                       name="jet axis", legendgroup="jet", showlegend=once("jet"),
                                       hoverinfo="text", text=f"jet, E = {je:.1f} GeV",
                                       meta={"role": "jets", "collection": roles.get("jets", "")}))

    # see figure.build: the numbers live in layout.meta and are rendered by the page
    fig.update_layout(
        meta=dict(run=e.run, event=e.event, entry=e.entry, source=e.path.split("/")[-1],
                  n_charged=e.n_charged, n_neutral=e.n_neutral, b_field=e.b_field,
                  btag=e.btag_event, title=title, note=note, view="3d"),
        template=_template3d(), showlegend=True, width=width, height=height,
        font=dict(size=12),
        images=[logo_image(x=0.995, size=0.085)],
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=0, r=0, t=66, b=60),
        scene=dict(
            aspectmode="data",  # physically proportional: the barrel is not stretched
            xaxis=dict(**AXIS, title_text="x [mm]"),
            yaxis=dict(**AXIS, title_text="y [mm]"),
            zaxis=dict(**AXIS, title_text="z [mm] (beam)"),
            camera=dict(eye=dict(x=1.45, y=1.05, z=0.85)),
        ),
        paper_bgcolor="white",
    )
    return fig


def build_flow3d(
    e: Event,
    *,
    groups: dict | None = None,
    hide: dict | None = None,
    jets: bool = True,
    title: str = "",
    note: str = "",
    width: int = 1250,
    height: int = 900,
) -> go.Figure:
    """Poynting-style sphere, with quills scaled by the square root of magnitude.

    Magnitude means E for clusters/jets and |p| for charged tracks, in GeV.
    All objects share one per-event normalization; jets are emphasized by a factor
    of 1.3. Equal, hidden axis ranges preserve the spherical geometry while rotating
    it. Positive-axis labels belong to the scene, so they rotate with the sphere;
    the small key above it is a colour key, not a fixed-screen orientation triad.
    """
    groups, hide = groups or {}, hide or {}
    roles = getattr(e, "roles", {}) or {}
    drawn, reference = objects(e, hide, jets)
    fig = go.Figure()
    seen = set()

    def once(group):
        first = group not in seen
        seen.add(group)
        return first

    phi = np.linspace(0, 2 * np.pi, 49)
    theta = np.linspace(0, np.pi, 25)
    fig.add_trace(go.Surface(
        # Lists also work with the site's Plotly.js 2.x (newer plotly.py can
        # encode numpy arrays using a binary JSON format introduced in JS 3.x).
        x=np.outer(np.cos(phi), np.sin(theta)).tolist(),
        y=np.outer(np.sin(phi), np.sin(theta)).tolist(),
        z=np.outer(np.ones_like(phi), np.cos(theta)).tolist(),
        showscale=False, opacity=0.12, colorscale=[[0, VDC], [1, VDC]], hoverinfo="skip",
        name="unit sphere", showlegend=True, legendgroup="sphere", meta={"role": "", "collection": ""},
    ))

    for obj in sorted(drawn, key=lambda obj: obj.role == "tracks" and obj.index in groups):
        scale = 1.0
        if obj.role == "tracks":
            label, color = groups.get(obj.index, ("charged tracks", GREY))
            highlighted = obj.index in groups
            group = f"g:{label}" if highlighted else "trkother"
            line_width, marker_size = (5, 4) if highlighted else (2, 3)
        elif obj.role == "em_clusters":
            label, color, group = "EM clusters (quill ∝ √E)", SHOWER, "em"
            line_width, marker_size = 3, 3
        else:
            label, color, group = "jets (quill ∝ √E)", JETC, "jet"
            line_width, marker_size, scale = 8, 7, 1.3
        start = obj.direction
        end = (1.0 + scale * QUILL * np.sqrt(obj.magnitude / reference)) * obj.direction
        fig.add_trace(go.Scatter3d(
            x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]], mode="lines+markers",
            line=dict(color=color, width=line_width), marker=dict(size=[0, marker_size], color=color),
            name=label, legendgroup=group, showlegend=once(group), hovertemplate=obj.hover + "<extra></extra>",
            meta={"role": obj.role, "collection": roles.get(obj.role, "")},
        ))

    thrust = unit_direction(e.thrust)
    if thrust is not None:
        start, end = -1.35 * thrust, 1.35 * thrust
        fig.add_trace(go.Scatter3d(
            x=[start[0], end[0]], y=[start[1], end[1]], z=[start[2], end[2]], mode="lines",
            line=dict(color=PVC, width=4, dash="dash"), hovertemplate="thrust axis<extra></extra>",
            name="thrust axis", legendgroup="thrust", showlegend=True, meta={"role": "", "collection": ""},
        ))
    fig.add_trace(go.Scatter3d(
        x=[0, 0], y=[0, 0], z=[-1.35, 1.35], mode="lines", line=dict(color="#c9ced6", width=2),
        hoverinfo="skip", name="beam axis (z)", legendgroup="beam", showlegend=True,
        meta={"role": "", "collection": ""},
    ))

    hidden_axis = dict(visible=False, showbackground=False, showgrid=False,
                       zeroline=False, showline=False, showticklabels=False,
                       ticks="", title_text="", range=[-2.3, 2.3])
    axis_colours = ("#b44b4b", "#38805c", "#3d6eac")
    axis_labels = [
        dict(x=float(x), y=float(y), z=float(z), text="+" + axis,
             showarrow=False, font=dict(size=11, color=colour))
        for axis, colour, (x, y, z) in zip("xyz", axis_colours, 1.08 * np.eye(3))
    ]
    axis_key = "axis key: " + " &nbsp; ".join(
        f'<span style="color:{colour}">{axis}</span>'
        for axis, colour in zip("xyz", axis_colours)
    ) + " (z = beam)"

    fig.update_layout(
        meta=dict(run=e.run, event=e.event, entry=e.entry, source=e.path.split("/")[-1],
                  n_charged=e.n_charged, n_neutral=e.n_neutral, b_field=e.b_field,
                  btag=e.btag_event, title=title, note=note, view="flow3d"),
        template=_template3d(), showlegend=True, width=width, height=height, font=dict(size=12),
        images=[logo_image(x=0.995, size=0.085)],
        legend=dict(orientation="h", yanchor="top", y=-0.02, xanchor="center", x=0.5, font=dict(size=12)),
        annotations=[dict(text=axis_key, xref="paper", yref="paper", x=0.02, y=1.04,
                          xanchor="left", yanchor="bottom", showarrow=False,
                          font=dict(size=11, color="#5c636e"))],
        margin=dict(l=0, r=0, t=66, b=60),
        scene=dict(
            aspectmode="cube", bgcolor="white", annotations=axis_labels,
            xaxis=hidden_axis, yaxis=hidden_axis, zaxis=hidden_axis,
            camera=dict(eye=dict(x=1.45, y=1.05, z=0.85)),
        ), paper_bgcolor="white",
    )
    return fig
