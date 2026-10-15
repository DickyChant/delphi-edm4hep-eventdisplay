"""Build the four-panel DELPHI event display as one Plotly figure.

Panels, all from measured quantities only:
  (a) r-phi, whole event   (b) r-z, r signed by thrust hemisphere
  (c) vertex detector r-phi -- zoom into the vertex region with the mouse
  (d) RICH Cherenkov angle vs momentum, liquid and gas radiators

What Plotly buys over the matplotlib original: hover that names every track, a legend
that switches classes of object on and off, and a zoom that replaces the fixed inset.
"""

from __future__ import annotations

import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from . import geometry as G
from ._flow import objects, unit_direction
from ._logo import LOGO_DATA_URI
from .read import Event


def logo_image(x: float = 1.0, y: float = 1.0, size: float = 0.055, opacity: float = 0.95) -> dict:
    """The DELPHI + EDM4hep mark, as a layout image in the top margin.

    Anchored top-RIGHT: the subplot titles are left-aligned over their own panel, so a
    top-left mark lands straight on top of "(a) r-phi view".

    Embedded as a data URI, so it survives PNG/SVG export and an offline HTML file."""
    return dict(source=LOGO_DATA_URI, xref="paper", yref="paper", x=x, y=y,
                sizex=size, sizey=size, xanchor="right", yanchor="bottom",
                opacity=opacity, layer="above")

GREY, SHOWER, VDC, HPCC = "#a3a8ad", "#e0a100", "#5b7ea6", "#c2a66b"
PVC, SVC, FITC, HITC = "#111111", "#c0392b", "#d35400", "#8aa2bf"
MPI, MK, MP = 0.13957, 0.49368, 0.93827
N_LIQ, N_GAS = 1.2718, 1.0019  # DELPHI RICH refractive indices: C6F14 liquid, C5F12 gas
GAS_THR = {"π": MPI / np.sqrt(N_GAS**2 - 1), "K": MK / np.sqrt(N_GAS**2 - 1), "p": MP / np.sqrt(N_GAS**2 - 1)}
SHOWER_SCALE = 90.0  # mm per GeV, tower length in panels (a) and (b)
JETC = "#2a9d8f"  # separate from the grey jet axes in detector space


def _template():
    """plotlyhep's mplhep look when it is installed, otherwise plain Plotly."""
    try:
        import plotlyhep as php

        return php.template("CMS", scale=0.62)
    except Exception:
        return "plotly_white"


def _cherenkov(p, m, n):
    """Expected Cherenkov angle [mrad] for mass m at momentum p in a radiator of index n."""
    c = np.sqrt(p**2 + m**2) / (n * p)
    out = np.full_like(p, np.nan)
    ok = c < 1
    out[ok] = 1000 * np.arccos(c[ok])
    return out


def build(
    e: Event,
    *,
    groups: dict | None = None,
    rich: list | None = None,
    fit_vertices: list | None = None,
    hide: dict | None = None,
    jets: bool = False,
    title: str = "",
    note: str = "",
    width: int = 1500,
    height: int = 1450,
) -> go.Figure:
    """Assemble the figure. groups maps particle index -> (label, colour)."""
    groups = groups or {}
    rich = rich or []
    fit_vertices = fit_vertices or []
    hide = hide or {}

    sign, _ = G.curvature_sign(e)
    vtx = dict(e.sv_tracks)
    for xv, ids, _rms in fit_vertices:
        for i in ids:
            vtx[i] = xv
    s0, s_pv, _ = G.start_points(e, vtx, sign)

    drawn = [i for i in e.par if i not in hide]
    order = sorted(drawn, key=lambda i: i in groups)  # highlighted tracks drawn last, on top
    LIM = e.r_em + 450.0
    ZLIM = 3000.0
    RVD = (max(e.vd_layers) if e.vd_layers else 110.0) + 17.0
    Tt = e.thrust[:2] / (np.linalg.norm(e.thrust[:2]) or 1.0)
    side = lambda x, y: 1.0 if (x * Tt[0] + y * Tt[1]) >= 0 else -1.0

    fig = make_subplots(
        rows=4,
        cols=2,
        specs=[[{"rowspan": 2}, {"rowspan": 2}], [None, None], [{"rowspan": 2}, {}], [None, {}]],
        subplot_titles=(
            "<b>(a)</b>  r-φ view",
            "<b>(b)</b>  r-z view",
            "<b>(c)</b>  vertex detector, r-φ: layers and hits — zoom into the vertex region",
            "<b>(d)</b>  RICH Cherenkov angle — liquid radiator (C<sub>6</sub>F<sub>14</sub>)",
            "gas radiator (C<sub>5</sub>F<sub>12</sub>)",
        ),
        horizontal_spacing=0.085,
        vertical_spacing=0.075,
    )

    seen = set()  # legend entries already emitted

    def legend_once(key):
        first = key not in seen
        seen.add(key)
        return first

    # ---------------- detector outlines
    th = np.linspace(0, 2 * np.pi, 241)
    for r in e.vd_layers:
        for rc, cc in ((1, 1), (3, 1)):
            fig.add_trace(
                go.Scatter(
                    x=r * np.cos(th), y=r * np.sin(th), mode="lines", line=dict(color=VDC, width=1), opacity=0.6,
                    name="VD layers (radii from hits)", legendgroup="vd", showlegend=legend_once("vd"),
                    hoverinfo="text", text=f"VD layer, R = {r:.1f} mm",
                ), row=rc, col=cc,
            )
    fig.add_trace(
        go.Scatter(
            x=e.r_em * np.cos(th), y=e.r_em * np.sin(th), mode="lines", line=dict(color=HPCC, width=1.4, dash="dash"),
            name=f"EM calorimeter (HPC) at r = {e.r_em / 1000:.2f} m", legendgroup="hpc", showlegend=legend_once("hpc"),
            hoverinfo="text", text=f"HPC, r = {e.r_em:.0f} mm (from shower positions)",
        ), row=1, col=1,
    )
    if len(e.vd_z):
        zvd = (float(np.nanmin(e.vd_z)), float(np.nanmax(e.vd_z)))
        for r in e.vd_layers:
            for sg in (1, -1):
                fig.add_trace(
                    go.Scatter(x=list(zvd), y=[sg * r, sg * r], mode="lines", line=dict(color=VDC, width=1),
                               opacity=0.7, legendgroup="vd", showlegend=False, hoverinfo="skip"),
                    row=1, col=2,
                )

    # ---------------- tracks, panels (a) (b) (c)
    for i in order:
        col, lw = (groups[i][1], 2.6) if i in groups else (GREY, 1.2)
        lab = groups[i][0] if i in groups else "other charged tracks"
        grp = f"g:{groups[i][0]}" if i in groups else "trkother"  # by label, not by index: one entry per class
        q = int(e.charge[i])
        p = float(e.p_abs[i])
        nvd = len(e.track_hits.get(i, []))
        where = "secondary vertex" if i in e.sv_tracks else ("fitted vertex" if any(i in ids for _, ids, _ in fit_vertices) else "primary vertex / perigee")
        hov = f"<b>track {i}</b><br>q = {q:+d}<br>p = {p:.2f} GeV<br>VD hits: {nvd}<br>starts at the {where}"
        if i in groups:
            hov += f"<br>{groups[i][0]}"

        x, y, z, r = G.track_to(e.par[i], e.r_stop, sign, n=420, s0=s0[i])
        fig.add_trace(
            go.Scatter(x=x, y=y, mode="lines", line=dict(color=col, width=lw), name=lab, legendgroup=grp,
                       showlegend=legend_once(grp), hovertemplate=hov + "<extra></extra>"),
            row=1, col=1,
        )
        # (b) r-z, radius signed by the thrust hemisphere the track's momentum points into
        sg = side(e.momentum[i, 0], e.momentum[i, 1])
        k = int(np.argmax(np.abs(z) > ZLIM)) if np.any(np.abs(z) > ZLIM) else len(z)
        fig.add_trace(
            go.Scatter(x=z[:k], y=sg * r[:k], mode="lines", line=dict(color=col, width=lw), legendgroup=grp,
                       showlegend=False, hovertemplate=hov + "<extra></extra>"),
            row=1, col=2,
        )
        # (c) same track, out to the edge of the vertex detector
        xc, yc, _, _ = G.track_to(e.par[i], RVD * 1.5, sign, n=320, s0=s0[i])
        fig.add_trace(
            go.Scatter(x=xc, y=yc, mode="lines", line=dict(color=col, width=lw), legendgroup=grp,
                       showlegend=False, hovertemplate=hov + "<extra></extra>"),
            row=3, col=1,
        )
        # the piece between the IP and the vertex the track starts at: dotted, it was not travelled
        if i in s_pv and s_pv[i] < s0[i] - 1e-6:
            xb, yb, _ = G.helix(e.par[i], np.linspace(s_pv[i], s0[i], 140), sign)
            for rc, cc in ((1, 1), (3, 1)):
                fig.add_trace(
                    go.Scatter(x=xb, y=yb, mode="lines", line=dict(color=col, width=max(1.1, 0.6 * lw), dash="dot"),
                               opacity=0.75, name="back-extrapolation to the IP", legendgroup="back",
                               showlegend=legend_once("back") and rc == 1, hoverinfo="text",
                               text=f"track {i}: back-extrapolation, not a travelled path"),
                    row=rc, col=cc,
                )

    # ---------------- EM showers as towers, length proportional to energy
    for panel, (rc, cc) in enumerate(((1, 1), (1, 2))):
        xs, ys, txt = [], [], []
        for x0, y0, z0, en in zip(e.sh_x, e.sh_y, e.sh_z, e.sh_e):
            if panel == 0:
                v = np.array([x0, y0])
            else:
                v = np.array([z0, side(x0, y0) * np.hypot(x0, y0)])
            u = v / (np.linalg.norm(v) or 1.0)
            w = v + SHOWER_SCALE * en * u
            xs += [v[0], w[0], None]
            ys += [v[1], w[1], None]
            txt += [f"EM shower, E = {en:.2f} GeV", f"EM shower, E = {en:.2f} GeV", None]
        fig.add_trace(
            go.Scatter(x=xs, y=ys, mode="lines", line=dict(color=SHOWER, width=5),
                       name="EM shower (length ∝ energy)", legendgroup="em", showlegend=legend_once("em"),
                       hoverinfo="text", text=txt),
            row=rc, col=cc,
        )

    # ---------------- jet axes (off by default)
    if jets:
        for jx, jy, _jz, je in e.jets:
            if je < 5:
                continue
            u = np.array([jx, jy]) / (np.hypot(jx, jy) or 1.0)
            fig.add_trace(
                go.Scatter(x=[0, (e.r_em + 330) * u[0]], y=[0, (e.r_em + 330) * u[1]], mode="lines",
                           line=dict(color="#444", width=1, dash="dash"), opacity=0.5, name="jet axis",
                           legendgroup="jet", showlegend=legend_once("jet"), hoverinfo="text", text=f"jet, E = {je:.1f} GeV"),
                row=1, col=1,
            )

    # ---------------- vertex detector hits, panel (c)
    hit_col = {}
    for i in groups:
        if i in drawn:
            for j in e.track_hits.get(i, []):
                hit_col[j] = groups[i][1]
    hidden_hits = {j for i in hide for j in e.track_hits.get(i, [])}
    rphi = np.where(~np.isnan(e.vd_x))[0]
    plain = [j for j in rphi if j not in hit_col and j not in hidden_hits]
    if plain:
        fig.add_trace(
            go.Scatter(x=e.vd_x[plain], y=e.vd_y[plain], mode="markers", marker=dict(size=5, color=HITC),
                       name="VD R-φ hits", legendgroup="hits", showlegend=legend_once("hits"),
                       hoverinfo="text", text=[f"VD R-φ hit, R = {e.vd_r[j]:.1f} mm" for j in plain]),
            row=3, col=1,
        )
    own = [j for j in rphi if j in hit_col]
    if own:
        fig.add_trace(
            go.Scatter(x=e.vd_x[own], y=e.vd_y[own], mode="markers",
                       marker=dict(size=10, color=[hit_col[j] for j in own], line=dict(color="black", width=1)),
                       name="VD hit on a highlighted track", legendgroup="hitsown", showlegend=legend_once("hitsown"),
                       hoverinfo="text", text=[f"VD R-φ hit, R = {e.vd_r[j]:.1f} mm (highlighted track)" for j in own]),
            row=3, col=1,
        )

    # ---------------- vertices
    for rc, cc, ms in ((1, 1, 9), (3, 1, 13)):
        fig.add_trace(
            go.Scatter(x=[e.pv[0]], y=[e.pv[1]], mode="markers",
                       marker=dict(symbol="cross-thin", size=ms, color=PVC, line=dict(color=PVC, width=2.4)),
                       name="primary vertex (IP)", legendgroup="pv", showlegend=legend_once("pv") and rc == 3,
                       hoverinfo="text", text=f"primary vertex<br>({e.pv[0]:.3f}, {e.pv[1]:.3f}, {e.pv[2]:.3f}) mm"),
            row=rc, col=cc,
        )
    for k, v in enumerate(e.svs):
        d = float(np.linalg.norm(v - e.pv))
        fig.add_trace(
            go.Scatter(x=[v[0]], y=[v[1]], mode="markers",
                       marker=dict(symbol="circle-open", size=13, color=SVC, line=dict(color=SVC, width=2.4)),
                       name="reconstructed secondary vertex", legendgroup="sv", showlegend=legend_once("sv"),
                       hoverinfo="text", text=f"AABTAG secondary vertex {k}<br>{d:.2f} mm from the PV"),
            row=3, col=1,
        )
    for xv, ids, rms in fit_vertices:
        d = float(np.linalg.norm(xv - e.pv))
        fig.add_trace(
            go.Scatter(x=[xv[0]], y=[xv[1]], mode="markers",
                       marker=dict(symbol="diamond-open", size=12, color=FITC, line=dict(color=FITC, width=2.4)),
                       name="2-track vertex (our straight-line fit)", legendgroup="fit", showlegend=legend_once("fit"),
                       hoverinfo="text", text=f"fitted vertex from tracks {ids}<br>{d:.2f} mm from the PV, rms {rms:.0f} µm"),
            row=3, col=1,
        )

    # ---------------- (d) RICH
    pp = np.linspace(0.25, 16, 600)
    curves = [(MPI, "π", "solid", "#555555"), (MK, "K", "dash", "#000000"), (MP, "p", "dot", "#555555")]
    liq_meas = [1000 * e.haid[i][13] for i in rich if i in e.haid and len(e.haid[i]) >= 18 and e.haid[i][15] > 0]
    ylo = min(560.0, 10.0 * np.floor((min(liq_meas, default=560.0) - 30.0) / 10.0))
    for (rc, n_ref, ylim) in ((3, N_LIQ, (ylo, 690)), (4, N_GAS, (0, 75))):
        for m, lab, dash, col in curves:
            fig.add_trace(
                go.Scatter(x=pp, y=_cherenkov(pp, m, n_ref), mode="lines", line=dict(color=col, width=1.5, dash=dash),
                           name=f"expected θ<sub>C</sub> for {lab}", legendgroup=f"pid{lab}",
                           showlegend=legend_once(f"pid{lab}"), hoverinfo="skip"),
                row=rc, col=2,
            )
        fig.update_yaxes(range=list(ylim), title_text="θ<sub>C</sub> [mrad]", row=rc, col=2)
        fig.update_xaxes(range=[0.8, 14.5], row=rc, col=2)

    ordered = sorted([i for i in rich if i in e.haid and len(e.haid[i]) >= 18], key=lambda i: e.p_abs[i])
    for k, i in enumerate(ordered, 1):
        h = e.haid[i]
        col = groups.get(i, ("", "#333333"))[1]
        p = float(e.p_abs[i])
        if h[15] > 0:  # liquid radiator saw photons
            fig.add_trace(
                go.Scatter(x=[p], y=[1000 * h[13]], mode="markers+text", text=[str(k)], textposition="top right",
                           textfont=dict(color=col, size=13),
                           marker=dict(size=13, color=col, line=dict(color="black", width=1)),
                           legendgroup="richpt", showlegend=False, hoverinfo="text",
                           hovertext=f"<b>track {i}</b> (#{k})<br>q = {int(e.charge[i]):+d}, p = {p:.2f} GeV"
                                     f"<br>liquid: {int(h[15])} photons, θ<sub>C</sub> = {1000 * h[13]:.1f} mrad"),
                row=3, col=2,
            )
        if h[10] > 0 and h[8] > 0:  # gas radiator saw photons and got an angle
            fig.add_trace(
                go.Scatter(x=[p], y=[1000 * h[8]], mode="markers+text", text=[str(k)], textposition="top right",
                           textfont=dict(color=col, size=13),
                           marker=dict(size=13, color=col, line=dict(color="black", width=1)),
                           legendgroup="richpt", showlegend=False, hoverinfo="text",
                           hovertext=f"<b>track {i}</b> (#{k})<br>p = {p:.2f} GeV"
                                     f"<br>gas: {int(h[10])} photons, θ<sub>C</sub> = {1000 * h[8]:.1f} mrad"),
                row=4, col=2,
            )
        elif h[10] == 0 and p > GAS_THR["π"]:
            # above the pion threshold with no gas photons: that is a veto, not a missing measurement
            fig.add_trace(
                go.Scatter(x=[p], y=[3], mode="markers+text", text=[str(k)], textposition="top center",
                           textfont=dict(color=col, size=13),
                           marker=dict(symbol="triangle-down", size=14, color=col, line=dict(color="black", width=1)),
                           legendgroup="richpt", showlegend=False, hoverinfo="text",
                           hovertext=f"<b>track {i}</b> (#{k})<br>p = {p:.2f} GeV<br>gas: 0 photons above the π threshold — not a pion (veto)"),
                row=4, col=2,
            )
    fig.add_annotation(
        text="a pion above threshold would radiate here;<br>0 photons (▼) = not a pion (veto)",
        xref="x5 domain", yref="y5 domain", x=0.02, y=0.96, showarrow=False, align="left",
        font=dict(size=11, color="#333333"),
    )

    # ---------------- axes
    fig.update_xaxes(title_text="x [mm]", range=[-LIM, LIM], row=1, col=1)
    fig.update_yaxes(title_text="y [mm]", range=[-LIM, LIM], scaleanchor="x", scaleratio=1, row=1, col=1)
    fig.update_xaxes(title_text="z [mm]  (beam axis)", range=[-ZLIM, ZLIM], row=1, col=2)
    fig.update_yaxes(title_text="±r [mm]  (sign = thrust hemisphere)", range=[-LIM, LIM], scaleanchor="x2", scaleratio=1, row=1, col=2)
    fig.update_xaxes(title_text="x [mm]", range=[-RVD, RVD], row=3, col=1)
    fig.update_yaxes(title_text="y [mm]", range=[-RVD, RVD], scaleanchor="x3", scaleratio=1, row=3, col=1)
    fig.update_xaxes(title_text="track momentum [GeV]", row=4, col=2)

    # No title or run/event line is drawn into the figure: every number is carried in
    # layout.meta below, so the page renders them as live text that can be restyled,
    # copied and re-laid-out. Baking them into the image only freezes them.
    fig.update_layout(
        # carried into the figure JSON so the Pages manifest can be built without reopening the ROOT file
        meta=dict(run=e.run, event=e.event, entry=e.entry, source=e.path.split("/")[-1],
                  n_charged=e.n_charged, n_neutral=e.n_neutral, b_field=e.b_field,
                  btag=e.btag_event, title=title, note=note),
        template=_template(),
        showlegend=True,  # the mplhep template defaults it off, as matplotlib does
        width=width,
        height=height,
        images=[logo_image(size=0.055)],
        legend=dict(orientation="h", yanchor="top", y=-0.045, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=70, r=30, t=76, b=130),
        hovermode="closest",
        hoverlabel=dict(bgcolor="white", font_size=12),
        plot_bgcolor="white",
        paper_bgcolor="white",
    )
    role_of_group = {
        "vd": "vd_hits", "hits": "vd_hits", "hitsown": "vd_hits",
        "hpc": "em_clusters", "em": "em_clusters",
        "trkother": "tracks", "back": "tracks",
        "jet": "jets", "pv": "primary_vertex", "sv": "secondary_vertices",
        "richpt": "hadron_id", "pidπ": "hadron_id", "pidK": "hadron_id", "pidp": "hadron_id",
    }
    roles = getattr(e, "roles", {}) or {}
    for tr in fig.data:
        grp = tr.legendgroup or ""
        role = role_of_group.get(grp, "tracks" if grp.startswith("g:") else None)
        if role:
            tr.meta = {"role": role, "collection": roles.get(role, "")}

    for ann, ax in zip(fig.layout.annotations[:5], ("xaxis", "xaxis2", "xaxis3", "xaxis4", "xaxis5")):
        ann.update(font=dict(size=13.5), x=fig.layout[ax].domain[0], xanchor="left")
    return fig


def build_flow2d(
    e: Event,
    *,
    groups: dict | None = None,
    hide: dict | None = None,
    jets: bool = True,
    title: str = "",
    note: str = "",
    width: int = 1100,
    height: int = 1000,
) -> go.Figure:
    """Orthographic projection of measured directions onto a unit celestial sphere.

    The fixed viewpoint is azimuth 45 degrees from +x toward +y and elevation
    30 degrees above the xy plane. Screen-right is (-1, 1, 0)/sqrt(2), screen-up
    is (-1/(2*sqrt(2)), -1/(2*sqrt(2)), sqrt(3)/2), and positive depth points
    toward the viewer. Rear directions have dashed, faded rays; both hemispheres
    remain visible. Rays join the origin to the projected *unit* direction, so
    their screen lengths encode orientation/foreshortening, not energy.

    Endpoint marker area scales with |p| for tracks and E for clusters/jets,
    with a 4-pixel diameter floor. Jets use a larger marker scale. This is a
    direction-space display, not a calculation of the electromagnetic Poynting
    vector, and tracks/clusters/jets are not summed as independent deposits.
    """
    groups, hide = groups or {}, hide or {}
    roles = getattr(e, "roles", {}) or {}
    drawn, reference = objects(e, hide, jets)
    fig = go.Figure()
    right = np.array([-1.0, 1.0, 0.0]) / np.sqrt(2.0)
    up = np.array([-1.0 / np.sqrt(8.0), -1.0 / np.sqrt(8.0), np.sqrt(3.0) / 2.0])
    toward_eye = np.array([np.sqrt(3.0 / 8.0), np.sqrt(3.0 / 8.0), 0.5])

    def project(direction):
        return float(direction @ right), float(direction @ up), float(direction @ toward_eye)

    # Every coordinate is a plain list, including guides, for Plotly.js 2.x.
    # The circle is the sphere's silhouette, not an equator in detector space.
    angle = np.linspace(0.0, 2.0 * np.pi, 361)
    fig.add_trace(go.Scatter(
        x=np.cos(angle).tolist(), y=np.sin(angle).tolist(), mode="lines",
        line=dict(color="#b8c2cb", width=1.2), fill="toself", fillcolor="rgba(200,210,218,0.06)",
        name="unit sphere", legendgroup="sphere", showlegend=False, hoverinfo="skip",
        meta={"role": "", "collection": "", "component": "silhouette"},
    ))
    # z=0 projects to an ellipse. Its front half has cos(phi-45 degrees)>=0.
    for front, start in ((False, 3.0 * np.pi / 4.0), (True, -np.pi / 4.0)):
        phi = np.linspace(start, start + np.pi, 181)
        equator = np.column_stack((np.cos(phi), np.sin(phi), np.zeros_like(phi)))
        fig.add_trace(go.Scatter(
            x=(equator @ right).tolist(), y=(equator @ up).tolist(), mode="lines",
            line=dict(color="#c4ccd3", width=1.0, dash="solid" if front else "dash"),
            opacity=0.85 if front else 0.65,
            name="equator (z = 0)", legendgroup="sphere", showlegend=False, hoverinfo="skip",
            meta={"role": "", "collection": "", "component": "equator",
                  "hemisphere": "front" if front else "rear"},
        ))

    seen = set()
    # Rear hemisphere first; within each hemisphere, draw emphasized objects last.
    order = sorted(drawn, key=lambda obj: (
        project(obj.direction)[2] >= 0.0,
        obj.role == "jets" or (obj.role == "tracks" and obj.index in groups),
    ))
    for obj in order:
        if obj.role == "tracks":
            label, color = groups.get(obj.index, ("charged tracks (area ∝ |p|)", GREY))
            group = f"g:{label}" if obj.index in groups else "trkother"
            symbol, maximum = "circle", 22.0
            line_width = 2.0 if obj.index in groups else 1.1
        elif obj.role == "em_clusters":
            label, color, group, symbol, maximum = "EM clusters (area ∝ E)", SHOWER, "em", "diamond", 22.0
            line_width = 1.4
        else:
            label, color, group, symbol, maximum = "jets (area ∝ E; enlarged)", JETC, "jet", "square", 40.0
            line_width = 3.0
        x, y, depth = project(obj.direction)
        front = depth >= 0.0
        hemisphere = "front" if front else "rear"
        size = max(4.0, maximum * np.sqrt(obj.magnitude / reference))
        hover = f"{obj.hover}<br>{hemisphere} hemisphere"
        fig.add_trace(go.Scatter(
            x=[0.0, x], y=[0.0, y], mode="lines+markers",
            line=dict(color=color, width=line_width, dash="solid" if front else "dash"),
            marker=dict(size=[0.0, size], sizemode="diameter", symbol=symbol, color=color,
                        line=dict(color="black", width=0.6)),
            opacity=0.9 if front else 0.42,
            name=label, legendgroup=group, showlegend=group not in seen,
            hovertemplate="%{text}<extra></extra>", text=[hover, hover],
            meta={"role": obj.role, "collection": roles.get(obj.role, ""),
                  "object_index": obj.index, "depth": depth, "hemisphere": hemisphere},
        ))
        seen.add(group)

    thrust = unit_direction(e.thrust)
    if thrust is not None:
        for sign, tag in ((1.0, "+"), (-1.0, "−")):
            x, y, depth = project(sign * thrust)
            front = depth >= 0.0
            hemisphere = "front" if front else "rear"
            fig.add_trace(go.Scatter(
                x=[0.0, x], y=[0.0, y], mode="lines+markers",
                line=dict(color=PVC, width=2.5, dash="solid" if front else "dash"),
                marker=dict(symbol="star", size=[0.0, 17.0], color=PVC,
                            line=dict(color="black", width=0.7)),
                opacity=0.9 if front else 0.48,
                name="thrust axis (±)", legendgroup="thrust", showlegend=sign > 0,
                hovertemplate=f"thrust axis ({tag})<br>{hemisphere} hemisphere<extra></extra>",
                meta={"role": "", "collection": "", "component": "thrust",
                      "depth": depth, "hemisphere": hemisphere, "sign": sign},
            ))

    annotations = [dict(
        text="Orthographic sphere · view az 45°, el 30° · z = beam"
             "<br>Solid: front · dashed/faded: rear · marker area ∝ |p| / E; jets enlarged; 4 px floor",
        x=0.0, y=1.025, xref="paper", yref="paper", xanchor="left", yanchor="bottom",
        showarrow=False, align="left", font=dict(size=11, color="#68737d"),
    )]
    for label, direction in zip(("+x", "+y", "+z"), np.eye(3)):
        x, y, _depth = project(direction)
        annotations.append(dict(
            text=label, x=1.09 * x, y=1.09 * y, xref="x", yref="y",
            showarrow=False, font=dict(size=11, color="#8b959e"),
        ))
    fig.update_layout(
        meta=dict(run=e.run, event=e.event, entry=e.entry, source=e.path.split("/")[-1],
                  n_charged=e.n_charged, n_neutral=e.n_neutral, b_field=e.b_field,
                  btag=e.btag_event, title=title, note=note, view="flow2d"),
        template=_template(), showlegend=True, width=width, height=height,
        images=[logo_image(size=0.07)], annotations=annotations,
        legend=dict(orientation="h", yanchor="top", y=-0.04, xanchor="center", x=0.5, font=dict(size=12)),
        margin=dict(l=35, r=35, t=90, b=100), hovermode="closest",
        hoverlabel=dict(bgcolor="white", font_size=12), plot_bgcolor="white", paper_bgcolor="white",
    )
    axes = dict(visible=False, title_text="", range=[-1.16, 1.16],
                showgrid=False, zeroline=False, showline=False, showticklabels=False,
                ticks="", constrain="domain")
    fig.update_xaxes(**axes)
    fig.update_yaxes(**axes, scaleanchor="x", scaleratio=1.0)
    return fig
