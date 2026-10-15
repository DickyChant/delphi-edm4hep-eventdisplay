# The browser app

The display opens on a showcase event and needs nothing installed.

[Open it](../app.html){ .md-button .md-button--primary }

## Two modes

| | showcase | live |
|---|---|---|
| source | the published figure JSON | a `.root` file you drop on the page |
| Python | none — instant | uproot under Pyodide, in your browser |
| entry stepping | disabled | enabled |
| rebinding collections | disabled | enabled |

Dropping a file switches to live mode. The file never leaves your machine: it is read with
[uproot](https://github.com/scikit-hep/uproot5) compiled to WebAssembly.

!!! note "First load"
    Live mode downloads Python, numpy, uproot, awkward and plotly once — roughly 30 MB, cached
    afterwards. The showcase does not need any of it, so the page is useful immediately and still
    works if Pyodide cannot start.

## The collection panel

Beside the figure is every collection in the event: per-event object count, EDM4hep type, domain,
provenance (transcribed from a DST bank, derived by SKELANA, or produced by the converter) and
the relations in and out.

* **Select a collection** — everything in the figure that did not come from it dims to 12 %.
* **Click a track, hit or vertex** — its collection is selected and described.
* **The dropdowns at the top** rebind a role to another collection and re-render (live mode).

The wiring is `meta.collection` on every trace, set by `figure.build`.

## Views and saving

Two toggles choose a **dimension** (`panels` / `3D`) and a **frame** (`lab` / `Poynting`).
The lab views show detector positions: the original four panels or the 3-D detector scene.
Poynting shows directions: a fixed 2-D sphere projection or a draggable 3-D direction sphere. See the
[energy-flow views](views.md#the-energy-flow-poynting-views).

Live mode builds all four views from the same entry and collection choices, so switching does
not reread the file or recompute the figures. A published event offers only the views present
in its manifest; unavailable buttons are disabled. If one combination is missing, changing an
axis selects the available view on that axis. The current collection selection carries across.

`PNG`, `SVG` and `JSON` save the view currently on screen, named from the run and event. The
suffix is `_3d` for 3-D, `_poynt` for energy flow, or `_3d_poynt` for both
(`delphi_run48758_evt2666_3d_poynt.svg`). JSON captures the current camera, zoom and visibility
and can be reopened in the [editor](../editor.html). Plotly's WebGL content in 3-D SVG exports
is embedded as a raster image rather than fully editable vector paths.

To publish all four views, generate an event with `--view all`, then run `delphi-pages`.
The extra files are `<stem>.3d.json`, `<stem>.flow2d.json` and `<stem>.flow3d.json`; the manifest
references them as `figure3d`, `figureflow2d` and `figureflow3d`. Existing showcase events need
regeneration from their original ROOT files before Poynting becomes available. Those files
are not in the repository; `examples/make_events.sh` generates all views when the data is available.

## Captions

`--title` and `--note` describe **one event**. They are stored in figure metadata, never drawn
into the plot and never used as a heading, so a file you open yourself shows no caption rather
than inheriting someone else's physics. Everything true of any event — run, event, source,
charged/neutral, b-tag, B field — is rendered live from the same metadata.
