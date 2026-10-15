"""Command line: one edm4hep entry -> one interactive HTML page (and its figure JSON).

Flags mirror the matplotlib original so the commands in examples/ carry over.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np

from . import geometry as G
from .figure import build, build_flow2d
from .figure3d import build3d, build_flow3d
from .read import n_entries, read_event
from .schema import ROLES, load_domains, read_schema, to_dict


def _standalone(fig, path, *, cdn: bool, meta: dict, title: str):
    """write_html plus a small HTML header, since the figure itself carries no title."""
    html = fig.to_html(include_plotlyjs="cdn" if cdn else True, full_html=True,
                       config={"displaylogo": False, "scrollZoom": True,
                               "toImageButtonOptions": {"format": "png", "filename": path.stem, "scale": 2}})
    bits = []
    if meta.get("run") is not None:
        bits.append(f"run {meta['run']}, event {meta['event']}")
    if meta.get("source"):
        bits.append(f"{meta['source']} entry {meta['entry']}")
    if meta.get("n_charged") is not None:
        bits.append(f"{meta['n_charged']} charged, {meta['n_neutral']} neutral")
    if meta.get("btag") is not None:
        bits.append(f"b-tag X<sub>ev</sub> = {meta['btag']:.2f}")
    if meta.get("b_field") is not None:
        bits.append(f"B = {meta['b_field']:.3f} T")
    if meta.get("note"):
        bits.append(meta["note"])
    head = (
        '<style>body{margin:0;font:14px/1.5 -apple-system,"Segoe UI",Helvetica,Arial,sans-serif}'
        '#hdr{padding:10px 18px;border-bottom:1px solid rgba(25,28,32,.14)}'
        '#hdr h1{font:700 17px "TeX Gyre Heros",Helvetica,Arial,sans-serif;margin:0 0 2px}'
        '#hdr p{margin:0;color:#5c636e;font:12.5px "IBM Plex Mono",Menlo,monospace}</style>'
        '<div id="hdr">' + (f"<h1>{title}</h1>" if title else "")
        + "<p>" + "  |  ".join(bits) + "</p></div>"
    )
    html = html.replace("<body>", "<body>" + head, 1)
    if title:
        html = html.replace("<head>", f"<head><title>{title}</title>", 1)
    path.write_text(html)


def parse_group(spec: str):
    """'label:colour:i,j,k' -> (label, colour, [i, j, k])."""
    try:
        lab, col, idx = spec.split(":", 2)
    except ValueError:
        raise SystemExit(f"--group wants 'label:colour:i,j,k', got {spec!r}") from None
    return lab, col, [int(x) for x in idx.split(",") if x.strip()]


def main(argv=None):
    ap = argparse.ArgumentParser(prog="delphi-display", description="DELPHI event display from edm4hep, as an interactive Plotly page")
    ap.add_argument("file", help="edm4hep ROOT file")
    ap.add_argument("--entry", type=int, required=True, help="entry number within the file")
    ap.add_argument("--out", help="output .html (a .json of the same stem is written beside it, for the editor)")
    ap.add_argument("--title", default="",
                    help="caption for THIS event (e.g. what the event shows); it is not a heading "
                         "for the display, and is stored in the figure metadata, not drawn into the plot")
    ap.add_argument("--note", default="", help="further caption text for this event")
    ap.add_argument("--group", action="append", default=[], metavar="LABEL:COLOUR:i,j,k",
                    help="highlight these tracks with a colour and a legend label (repeatable)")
    ap.add_argument("--rich", default="", help="comma-separated track indices to show in panel (d)")
    ap.add_argument("--fit-vertex", action="append", default=[], metavar="i,j",
                    help="fit a straight-line vertex from these tracks and start them there (repeatable)")
    ap.add_argument("--require-vd", action="store_true",
                    help="hide tracks with no VD hits that belong to no vertex and no highlighted group")
    ap.add_argument("--max-ip", type=float, default=None,
                    help="hide unattached tracks whose r-phi closest approach to the PV exceeds this [mm]")
    ap.add_argument("--jets", action="store_true", help="draw the AABTAG jet axes in panel (a)")
    ap.add_argument("--view", choices=("panels", "3d", "flow2d", "flow3d", "both", "all"), default="panels",
                    help="panels: the four-panel figure; 3d: the detector scene; "
                         "flow2d/flow3d: the Poynting energy-flow map / sphere; "
                         "both: add <stem>.3d.{html,json}; all: also add .flow2d and .flow3d sidecars")
    ap.add_argument("--collection", action="append", default=[], metavar="ROLE=NAME",
                    help="draw ROLE from collection NAME instead of the default "
                         "(roles: " + ", ".join(ROLES) + "); repeatable")
    ap.add_argument("--domains", default="docs/collection_domains.json",
                    help="collection -> domain table from the converter's collection map "
                         "(podio metadata does not carry domains); ignored if absent")
    ap.add_argument("--list-collections", action="store_true",
                    help="print every collection in the file with its type, counts and links, then exit")
    ap.add_argument("--width", type=int, default=1500)
    ap.add_argument("--height", type=int, default=1450)
    ap.add_argument("--cdn", action="store_true",
                    help="load plotly.js from the CDN instead of inlining it (small file, needs the network to open)")
    ap.add_argument("--quiet", action="store_true", help="only print what was written")
    a = ap.parse_args(argv)

    say = (lambda *x: None) if a.quiet else (lambda *x: print(*x))

    if not Path(a.file).exists():
        raise SystemExit(f"no such file: {a.file}")
    total = n_entries(a.file)
    if not 0 <= a.entry < total:
        raise SystemExit(f"--entry {a.entry} out of range: the file holds {total} events (0-{total - 1})")

    overrides = {}
    for spec in a.collection:
        if "=" not in spec:
            raise SystemExit(f"--collection wants ROLE=NAME, got {spec!r}")
        role, name = spec.split("=", 1)
        if role not in ROLES:
            raise SystemExit(f"unknown role {role!r}; choose from: {', '.join(ROLES)}")
        overrides[role] = name

    doms = load_domains(a.domains)

    if a.list_collections:
        sch = read_schema(a.file, entry=a.entry, domains=doms)
        roles = sch.resolve(overrides)
        used = {v: k for k, v in roles.items()}
        print(f"{Path(a.file).name}: {sch.entries} entries, {len(sch.collections)} collections, entry {a.entry}")
        for name, c in sorted(sch.collections.items(), key=lambda kv: (kv[1].kind, kv[0])):
            mark = f"  <- {used[name]}" if name in used else ""
            print(f"  {c.count:5d}  {c.kind:24s} {name}{mark}")
            for r, t in c.links:
                print(f"         {'':24s}   {r} -> {t}")
        return 0

    if not a.out:
        ap.error("--out is required (except with --list-collections)")

    e = read_event(a.file, a.entry, collections=overrides, domains=doms)
    say(f"{Path(a.file).name} entry {a.entry}: run {e.run}, event {e.event}, {len(e.par)} tracks with a perigee state")

    sign, msg = G.curvature_sign(e)
    say(msg)
    _, _, vdmsg = G.vd_residuals(e, sign)
    say(vdmsg)

    groups = {}
    for spec in a.group:
        lab, col, idx = parse_group(spec)
        for i in idx:
            groups[i] = (lab, col)

    fit_vertices = []
    for spec in a.fit_vertex:
        got = G.fit_vertex(e, [int(x) for x in spec.split(",") if x.strip()], sign)
        if got is None:
            say(f"--fit-vertex {spec}: needs at least two tracks that have a perigee state, skipped")
            continue
        xv, ids, rms = got
        fit_vertices.append(got)
        say(f"fitted vertex from tracks {ids}: {np.round(xv, 3).tolist()} mm, {np.linalg.norm(xv - e.pv):.2f} mm from the PV, rms {rms:.0f} um")

    vtx = dict(e.sv_tracks)
    for xv, ids, _ in fit_vertices:
        for i in ids:
            vtx[i] = xv
    _, _, startmsg = G.start_points(e, vtx, sign)
    say(startmsg)

    hide = {}
    if a.require_vd or a.max_ip is not None:
        for i in list(e.par):
            if i in vtx or i in groups:
                continue
            nvd = len(e.track_hits.get(i, []))
            d = G.impact_parameter(e, i, sign)
            why = (["no VD hits"] if (a.require_vd and nvd == 0) else []) + ([f"IP > {a.max_ip:g} mm"] if (a.max_ip is not None and d > a.max_ip) else [])
            if why:
                hide[i] = (d, float(e.p_abs[i]), nvd, why)
        if hide:
            say(f"hidden {len(hide)} tracks: " + ", ".join(
                f"{i} ({v[1]:.2f} GeV, {v[0]:.1f} mm, {v[2]} VD hits: {'+'.join(v[3])})"
                for i, v in sorted(hide.items(), key=lambda kv: kv[1][0])))

    def build_3d():
        return build3d(e, groups=groups, fit_vertices=fit_vertices, hide=hide, jets=a.jets,
                       title=a.title, note=a.note)

    def build_flow_2d():
        return build_flow2d(e, groups=groups, hide=hide, title=a.title, note=a.note,
                            width=a.width, height=a.height)

    def build_flow_3d():
        return build_flow3d(e, groups=groups, hide=hide, title=a.title, note=a.note,
                            width=a.width, height=a.height)

    if a.view == "3d":
        fig = build_3d()
    elif a.view == "flow2d":
        fig = build_flow_2d()
    elif a.view == "flow3d":
        fig = build_flow_3d()
    else:
        fig = build(
            e,
            groups=groups,
            rich=[int(x) for x in a.rich.split(",") if x.strip()],
            fit_vertices=fit_vertices,
            hide=hide,
            jets=a.jets,
            title=a.title,
            note=a.note,
            width=a.width,
            height=a.height,
        )

    out = Path(a.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    _standalone(fig, out, cdn=a.cdn, meta=dict(fig.layout.meta or {}), title=a.title)
    js = out.with_suffix(".json")
    js.write_text(json.dumps(json.loads(fig.to_json()), separators=(",", ":")))
    # the collection panel on the web page reads this beside the figure
    out.with_suffix(".schema.json").write_text(json.dumps(to_dict(e.schema, e.roles), separators=(",", ":")))

    def sidecar(suffix, builder):
        side = builder()
        html = out.with_suffix(suffix + ".html")
        _standalone(side, html, cdn=a.cdn, meta=dict(side.layout.meta or {}), title=a.title)
        json_path = out.with_suffix(suffix + ".json")
        json_path.write_text(json.dumps(json.loads(side.to_json()), separators=(",", ":")))
        print(f"wrote {html} and {json_path} ({json_path.stat().st_size / 1e6:.2f} MB)")

    if a.view in ("both", "all"):
        sidecar(".3d", build_3d)
    if a.view == "all":
        sidecar(".flow2d", build_flow_2d)
        sidecar(".flow3d", build_flow_3d)
    print(f"wrote {out} ({out.stat().st_size / 1e6:.1f} MB) and {js} ({js.stat().st_size / 1e6:.2f} MB)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
