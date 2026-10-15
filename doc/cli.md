# Command line

```bash
delphi-display FILE.edm4hep.root --entry N --out event.html [options]
delphi-display FILE.edm4hep.root --entry N --list-collections     # --out not needed
delphi-pages [--docs docs]                                        # rebuild the site manifest
docs/build.sh                                                     # rebuild the wheel the app installs
```

## Options

| flag | meaning |
|---|---|
| `--entry N` | entry number within the file (required) |
| `--out PATH` | output `.html`; a `.json` and `.schema.json` are written beside it |
| `--view panels\|3d\|flow2d\|flow3d\|both\|all` | detector panels/scene or Poynting map/sphere; `both` adds the detector scene; `all` writes all four |
| `--group 'LABEL:COLOUR:i,j,k'` | highlight these tracks, repeatable |
| `--rich i,j,...` | tracks to show in the RICH panel |
| `--fit-vertex i,j` | straight-line vertex from those tracks; they start there |
| `--require-vd` | hide tracks with no VD hits that belong to no vertex and no group |
| `--max-ip MM` | hide unattached tracks passing further than this from the PV |
| `--jets` | draw the AABTAG jet axes in detector views; flow views include jets by default |
| `--collection ROLE=NAME` | draw ROLE from another collection, repeatable |
| `--domains FILE` | collection → domain table (default `docs/collection_domains.json`) |
| `--title` / `--note` | caption for **this** event; stored in metadata, not drawn |
| `--width` / `--height` | figure size in px |
| `--cdn` | load plotly.js from the CDN instead of inlining it (small file, needs network) |
| `--list-collections` | print every collection with type, counts and links, then exit |

Track indices come from the original `dump_event.py --run --event` (data) or
`mc_dump_event.py --entry` (simulation).

## Outputs

Each run writes:

* `event.html` — self-contained, plotly.js inlined (~5 MB), opens offline, with an HTML header
* `event.json` — the Plotly figure (~0.5 MB); **this** is what the site and editor load
* `event.schema.json` — the collections, counts, links and provenance for the panel

Only the JSON is committed; the standalone HTML is gitignored.

`--view both` also writes `event.3d.html` and `event.3d.json`. `--view all` adds
`event.flow2d.{html,json}` and `event.flow3d.{html,json}` for the energy-flow map
and sphere. Run `delphi-pages` afterward to advertise available views to the app.
`--view flow2d` or `--view flow3d` writes just that view to the requested output stem.

## Worked example

`examples/make_events.sh` holds the exact commands for the talk events. The data one:

```bash
delphi-display "$D/data_94c/Y13709.126.edm4hep.root" --entry 3990 \
  --out docs/events/data_48758_2666.html --view all --require-vd \
  --title 'Z → bb̄ with a displaced φ → K⁺K⁻' \
  --note 'SVs at 9.66 mm (φ side) and 2.87 mm' \
  --group 'φ → K⁺K⁻ (both kaons RICH-identified):#d62728:20,22' \
  --group 'third identified K⁻, same SV:#ff7f0e:21' \
  --group 'identified K⁺ at the other SV:#1f77b4:6' \
  --group 'p̄ candidate (RICH), other SV:#9467bd:25' \
  --rich 20,22,21,6,25
```
