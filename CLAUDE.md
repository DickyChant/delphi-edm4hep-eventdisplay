# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
pip install -e .                                   # or: pip install -e '.[dev]'
delphi-display FILE.edm4hep.root --entry N --out docs/events/x.html
delphi-display FILE.edm4hep.root --entry N --list-collections   # no --out needed
delphi-pages                                       # rebuild docs/events/index.json
docs/build.sh                                      # rebuild the wheel the browser app installs
examples/make_events.sh                            # the two talk events (needs $D pointing at the EOS data)
```

Run `pytest` for synthetic-event tests of the flow figures, CLI output modes and site manifest.
The physics self-checks the CLI prints on real input (see below) remain essential; treat a
change in those numbers as a regression. Synthetic tests do not replace the EOS data checks.

Event data is not in the repository. A local copy for development:

```bash
scp -o GSSAPIDelegateCredentials=yes \
  lxplus:/eos/experiment/eealliance/Users/zhangj/edm4hepSimBTagging/data_94c/Y13709.126.edm4hep.root data/
# run 48758 / event 2666 is entry 3990 -- the reference event for every number below
```

`ssh lxplus` needs `-K` (or `GSSAPIDelegateCredentials yes`) or you get no AFS token and cannot
read your own home directory. A Kerberos ticket (`kinit`) is required; the pubkey path is refused.

## Deploying

**GitHub Pages is the official location** — `.github/workflows/pages.yml` builds the manual and
publishes `docs/` on push to main: https://delphi-fulldst-edm4hep.github.io/delphi-edm4hep-eventdisplay/
The repo is private and the org is on the **free** plan, so Pages is refused
(*"Your current plan does not support GitHub Pages for this repository"*). Make the repo public,
as delphi-edm4hep is, or move the org to a paid plan; the workflow passes `enablement: true` so it
turns Pages on by itself once that is possible. Until then the CERN mirror is the only live copy.

The CERN web area is a **temporary** mirror, kept only until Pages is live:

```bash
tar -cf - -C docs . | ssh -K lxplus 'tar -xf - -C /eos/user/s/sqian/www/delphi-edm4hep-eventdisplay'
```

Site shape: `docs/index.html` is the landing page, `docs/app.html` the display,
`docs/manual/` the built manual. `.github/workflows/ci.yml`
lints and fails if the committed wheel is stale against the source or if the site references a file
that is not there; run `docs/build.sh` after changing anything under `src/`.

Only the figure **JSON** is committed (~0.5 MB). The standalone HTML inlines plotly.js (~5 MB) and
is gitignored.

## Architecture

The pipeline is four stages, each usable alone:

```
read.py      edm4hep file + entry  -> Event      (decoding rules live here)
geometry.py  Event                 -> helices, signs, start points, self-checks
figure.py    Event                 -> one go.Figure, four panels
cli.py/pages.py                    -> HTML + JSON + site manifest
schema.py    file                  -> what collections exist, their links and counts
```

`figure.build()` takes an `Event` and returns a figure; it never touches the filesystem. That is
what lets the same code run unmodified in the browser under Pyodide (`docs/app.html`), where
uproot reads a dropped file in WASM and the identical `read_event`/`build` produce the figure.

`build_flow2d` and `build_flow3d` provide Poynting-style direction views: a φ–cos θ map
and a unit sphere with energy quills. The shared `_flow.py` filters undefined/nonfinite
directions and invalid magnitudes before normalization. The app selects dimension and
lab/Poynting frame independently; the CLI supports `--view flow2d|flow3d|all`.
Regenerate the real showcase sidecars with `examples/make_events.sh` on EOS, then run
`delphi-pages`; those ROOT inputs are not in the repository. Rebuild the browser wheel
with `docs/build.sh` whenever package source changes.

**Nothing is pinned by collection name.** `schema.read_schema()` reads podio's own metadata and
`Schema.resolve()` binds each display *role* (`particles`, `tracks`, `primary_vertex`,
`secondary_vertices`, `em_clusters`, `vd_hits`, `hadron_id`, `jets`) to a collection, using the
preference lists in `schema.ROLES`. The historical DELPHI names are simply the first preference.
`--collection role=name` overrides. This matters: the 1994 data file holds 3 `Track` collections,
7 `Vertex`, 4 `Cluster`, 2 `TrackerHit3D` and 24 `ParticleID`.

Every figure trace carries `meta.collection`, which is how the browser app's collection panel and
the figure select each other. Keep that tagging (the `role_of_group` map at the end of
`figure.build`) in step with any new trace.

## Self-checks — the real test suite

On run 48758 / event 2666 the CLI must print:

```
curvature check on 4 track-cluster links: median miss 15 mm (omega as stored) vs 613 mm (flipped) -> sign +1
VD hit decoding check: |d(R*phi)| median 3 um (n=47); z hits |dz| median 0.00 mm (n=32)
track start points: 9 at their secondary vertex (miss 10-49 um), 7 at the primary vertex, 3 at their perigee
hidden 3 tracks: 33 (0.49 GeV, ...), 32 (...), 26 (...)          # with --require-vd
```

A VD residual of hundreds of mm means the strip decoding regressed; a flipped curvature sign means
the omega convention moved in the converter.

## Traps found the hard way

* **VD hits are strip coordinates.** Type 0 (R-φ): x = layer radius R, z = R·φ. Type 1 (z): x = −R,
  z = measured z. Plotting raw (x, y) puts every hit near φ = 0.
* **`tree.keys()` spells branches `parent/parent.field`; `arrays()` calls them `parent.field`.**
  Comparing the two spellings silently finds nothing — every collection reads as empty.
* **Branches are read with `library="np"`** (`read._Entry`), one at a time and cached. uproot ≥ 5.7
  imports awkward itself, so it stays a dependency even though our code never uses it.
* **Open Plotly marker symbols take their stroke from `marker.color`,** not `marker.line.color`;
  leaving it unset tints each one from the default colour cycle.
* **plotlyhep's template sets `showlegend: False`** (mirroring mplhep), so the figure must set
  `showlegend=True` explicitly or the legend silently vanishes.
* **`pip wheel repo` downloads an unrelated PyPI package called `repo`.** Always `./repo`.
* **`.gitignore` has `*.png`** for generated figures, which silently excluded `docs/logo.png`; the
  `!docs/logo.png` negation keeps the site's own asset tracked. Deploying by `tar`-ing `docs/` hides
  this class of bug, because tar does not consult `.gitignore`.
* **Pyodide's `awkward-cpp` fails to dlopen under Node** but works in browsers; do not use Node to
  validate the in-browser path.
* AABTAG secondary vertices count only when their ITSEC parameter is ≥ 0.
* `sDST_RPROCO_CombinedTags` calls ~6% of 3–8 GeV pions kaons; don't use it for single-event claims.

## Related repositories

* `../delphi-edm4hep` — the converter producing these files. Its `docs/collection-map/` builds the
  published collection map this display's schema vocabulary matches.
* `../plotlyhep` — supplies the mplhep-style Plotly template (`figure._template`). Optional: the
  figure falls back to `plotly_white` if it is not installed.
* The matplotlib original this is ported from:
  `/eos/experiment/eealliance/Users/zhangj/event_display/event_display.py` — the reference for the
  physics and every decoding rule.
