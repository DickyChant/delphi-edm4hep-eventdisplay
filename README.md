# DELPHI event display — edm4hep → Plotly

One DELPHI event drawn straight from an edm4hep file: no DELGRA, no X11, no ROOT, no key4hep.
A Python port of the matplotlib display written for the Sept 2026 talk, rebuilt on Plotly so the
figure zooms, hovers and can be edited in a browser.

**Live:** https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep-eventdisplay/ — the landing page, the
[display](https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep-eventdisplay/app.html) and the
[manual](https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep-eventdisplay/manual/).
A temporary copy is mirrored at <https://sqian.web.cern.ch/delphi-edm4hep-eventdisplay/>.

The display opens on a published showcase event, and you can drop **any**
edm4hep file on it to step through that file's events instead — read in the browser with uproot
under Pyodide, so nothing is uploaded. Beside the figure is every collection in the event with its
type, domain, provenance, links and per-event counts; selecting one dims everything in the figure
that did not come from it, and clicking a track selects its collection. Switch between the four
panels and a 3-D detector scene, or choose **Poynting** for a 2-D projected energy-flow sphere or a
3-D direction sphere. Save any available view as PNG, SVG or figure JSON.

## Install and run

To try all four views without a ROOT file, open
[`app.html?ev=synthetic_flow_demo`](docs/app.html?ev=synthetic_flow_demo) on a hosted copy,
or select **Synthetic two-jet energy-flow demo** in the event menu. Choose **Poynting**,
then switch between **panels** and **3D**. This is a clearly labelled, hand-built
illustration, not DELPHI collision data or a physics simulation. It can be reproduced with
`python examples/make_synthetic_event.py` followed by `delphi-pages`.

```bash
pip install -e .
delphi-display FILE.edm4hep.root --entry 3990 --out docs/events/my_event.html \
    --view all --require-vd --rich 20,22,21 \
    --group 'φ → K⁺K⁻ (both kaons RICH-identified):#d62728:20,22'
delphi-pages      # rebuild docs/events/index.json so the site lists the new event
docs/build.sh     # rebuild the wheel the browser app installs (CI fails if it is stale)
```

By default each run writes a **self-contained `.html`** (plotly.js inlined, ~5 MB, opens offline),
a **`.json`** figure and a `.schema.json` collection sidecar. The site and editor load the JSON;
standalone HTML is not committed. `--view all` additionally writes `.3d`, `.flow2d` and `.flow3d`
HTML/JSON pairs beside the base panels figure. `delphi-pages` discovers only sidecars that exist.
`examples/make_events.sh` holds the commands for all four views of the two talk events; the
original ROOT files are needed to regenerate their new energy-flow sidecars.

Options mirror the matplotlib original: `--title`, `--note`, `--group 'label:colour:i,j,k'`
(repeatable), `--rich i,j,...`, `--fit-vertex i,j`, `--require-vd`, `--max-ip MM`, `--jets`,
`--width/--height`, `--cdn`, `--view panels|3d|both|flow2d|flow3d|all`. Track indices come from the original `dump_event.py --run --event`
(data) or `mc_dump_event.py --entry` (simulation).

## Any file, any collection

Nothing is pinned by name. The collections are discovered from the file's own podio metadata --
the same source the converter's [collection map](https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep/collection_map.html)
is built from -- and each part of the display is bound to one of them by *role*:

```bash
delphi-display FILE.edm4hep.root --entry 3990 --list-collections   # what is in this file
delphi-display FILE.edm4hep.root --entry 3990 --out e.html     --collection vd_hits=sDST_TDVD_VDPoints     --collection secondary_vertices=sDST_V0_V0Candidates
```

Roles: `particles`, `tracks`, `jets`, `primary_vertex`, `secondary_vertices`, `em_clusters`,
`vd_hits`, `hadron_id`. Each resolves to the first collection of the right EDM4hep type matching
its preference list (`schema.ROLES`), so the usual DELPHI names stay the defaults. This matters
because a file offers far more than one of each: the 1994 data file carries 3 `Track` collections,
7 `Vertex`, 4 `Cluster`, 2 `TrackerHit3D` and 24 `ParticleID`.

In the browser app the same choice is a set of dropdowns, beside a panel listing every collection
with its per-event count, domain, provenance and links. Selecting a collection dims everything in
the figure that did not come from it; clicking a track or hit selects its collection. Every trace
carries `meta.collection`, which is what wires the two together.

## What it draws

Four panels, all from measured quantities only:

* **(a) r-φ** whole event: track helices, EM showers (tower length ∝ energy), the HPC radius taken
  from the shower positions.
* **(b) r-z**: the same tracks, r signed by thrust hemisphere.
* **(c) vertex detector, r-φ**: the three VD layers (radii from the hits themselves), the R-φ hits,
  the primary vertex and the accepted AABTAG secondary vertices. The matplotlib version needed a
  fixed inset for the vertex region; here you zoom with the mouse.
* **(d) RICH**: Cherenkov angle vs momentum, liquid and gas radiators, with the expected π/K/p
  curves (n_liq 1.2718, n_gas 1.0019; gas thresholds π 2.26 / K 8.0 / p 15.2 GeV). A track above
  the pion threshold with zero gas photons is drawn as a veto marker.

Tracks are helices from the AtIP (perigee) track state. A track belonging to a reconstructed
secondary vertex starts at that vertex, with the back-extrapolation to the IP dotted, so nothing
suggests a path the particle never travelled.

What Plotly adds over the original: hover naming each track (charge, momentum, VD hits, which
vertex it starts from), a legend that switches whole classes of object off, and free zoom.

### Spherical energy-flow views

The browser's dimension (`panels` / `3D`) and frame (`lab` / `Poynting`) toggles offer four views.
Poynting displays charged-track momentum directions, EM-cluster directions from the detector
origin, jets and the thrust axis on a fixed 2-D sphere projection or a draggable 3-D unit sphere. In 2-D, marker area
scales with energy (clusters/jets) or |p| (tracks), above a small visibility floor; the sphere adds
radial quills whose lengths scale with the square root of the same weight. Collection selection and track highlighting work in these views too.

“Poynting” names an angular energy-flow visualization, not a computation of **E × H** or a
Lorentz transformation. Tracks and clusters may overlap physically, so their displayed weights
are not an additive reconstructed energy total. See [the view guide](doc/views.md).

Use `--view flow2d` or `--view flow3d` for a single flow figure, `--view all` for all four, and
`--view both` for the original two lab views. Live-file mode builds all four. Existing showcase
events offer Poynting only after their flow sidecars have been generated and indexed.

## Captions, not headings

`--title` and `--note` describe **one event** ("Z → bb̄ with a displaced φ → K⁺K⁻"), so they are
never drawn into the figure and never shown as a heading for the tool -- they are stored in
`layout.meta` and rendered by the page as a trailing caption. Everything true of any event (run,
event, source, charged/neutral, b-tag, B field) is rendered live from the same metadata. The
figures themselves carry no text that would go stale on the next event, except the embedded
DELPHI + EDM4hep mark (`_logo.py`, a data URI, so it survives PNG/SVG export and offline HTML).

The browser app saves the current view as **PNG**, **SVG** or the **figure JSON**, named after the
run and event, with `_3d`, `_poynt` or `_3d_poynt` identifying the selected view.

## Layout

| | |
|---|---|
| `src/delphi_eventdisplay/read.py` | edm4hep → an `Event`: the collection names and every decoding rule |
| `src/delphi_eventdisplay/geometry.py` | helices, the curvature-sign check, where each track starts, the self-checks |
| `src/delphi_eventdisplay/figure.py` | the four panels and the 2-D projected sphere → `go.Figure` |
| `src/delphi_eventdisplay/figure3d.py` | the detector scene and the direction sphere → `go.Figure` |
| `src/delphi_eventdisplay/cli.py` | `delphi-display` |
| `src/delphi_eventdisplay/pages.py` | `delphi-pages`, rebuilds the site manifest |
| `src/delphi_eventdisplay/schema.py` | collection discovery from podio metadata; roles, counts, links |
| `docs/` | the published site: `index.html` landing, `app.html` the display, `editor.html`, `events/*.json`, `wheels/` the wheel the app installs |
| `doc/` | manual sources; `mkdocs build` renders them into `docs/manual/` |
| `docs/build.sh` | rebuilds the wheel the browser app installs |

## Self-checks printed on every run

The display re-derives rather than hard-codes the things that have moved between converter
versions, and prints what it found. On the 1994 data event (run 48758, event 2666):

```
curvature check on 4 track-cluster links: median miss 15 mm (omega as stored) vs 613 mm (flipped) -> sign +1
VD hit decoding check: r-phi hits vs own track |d(R*phi)| median 3 um (n=47); z hits |dz| median 0.00 mm (n=32)
track start points: 9 at their secondary vertex (miss 10-49 um), 7 at the primary vertex, 3 at their perigee
hidden 3 tracks: 33 (0.49 GeV, 189.5 mm, 0 VD hits: no VD hits), ...
```

A r-φ residual of a few µm is what says the VD strip decoding is right; if it ever reads hundreds
of mm, the decoding below has regressed.

## Things worth knowing before extending it

* **VD hits are strip coordinates, not space points.** In `sDST_TDVD_VDHits`, a type-0 (R-φ) hit
  stores x = layer radius R and z = R·φ; a type-1 (z) hit stores x = −R and z = the measured z.
  Plotting the raw (x, y) puts every hit near φ = 0.
* **Curvature sign** is re-checked per event by extrapolating tracks to their linked calorimeter
  clusters and comparing both signs.
* AABTAG secondary vertices are accepted when their ITSEC parameter is ≥ 0; rejected hypotheses
  are not drawn.
* **Open Plotly marker symbols take their stroke from `marker.color`**, not `marker.line.color` —
  leaving it unset silently tints each vertex a different colour from the default cycle.
* **Branches are read with `library="np"`** (`read._Entry`), not awkward arrays -- one branch at a
  time, cached. `uproot >= 5.7` still imports awkward itself, so it stays a dependency.
* **`tree.keys()` spells branches `parent/parent.field`** while `arrays()` calls them
  `parent.field`. Comparing the two spellings silently finds nothing.
* **`pip wheel repo` installs a package named `repo` from PyPI**, not your directory. Use `./repo`.
* **plotlyhep's template sets `showlegend: False`** (it mirrors mplhep, where you call `legend()`
  yourself), so the figure sets `showlegend=True` explicitly.
* Particle ID: `sDST_XNEWTAG_RichTags` plus the raw HAID angles/photon counts.
  `sDST_RPROCO_CombinedTags` calls ~6% of 3–8 GeV pions that radiate in the gas kaons — don't
  trust it for single-event claims. TPC dE/dx is in `sDST_BBDXGET_Dedx`; it cannot separate p from
  π around 1.7 GeV.

## Data

The edm4hep files are not in this repository. The talk events live on EOS:

```
/eos/experiment/eealliance/Users/zhangj/edm4hepSimBTagging/data_94c/Y13709.126.edm4hep.root   # entry 3990
/eos/experiment/eealliance/Users/zhangj/edm4hepSimBTagging/Zbb/bb_1000182.edm4hep.root        # entry 422
```

They are produced by [delphi-edm4hep](https://github.com/delphi-fullDST-edm4hep/delphi-edm4hep).

## Credits

Ported from `event_display.py` by J. Zhang
(`/eos/experiment/eealliance/Users/zhangj/event_display/`), which is the reference for the physics
and for every decoding rule above. Styling via [plotlyhep](https://github.com/DickyChant/plotlyhep).
