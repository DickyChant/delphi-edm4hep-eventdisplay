# Python API

```python
from delphi_eventdisplay import read_event, build, build3d, build_flow2d, build_flow3d
from delphi_eventdisplay.schema import to_dict

e = read_event("Y13709.126.edm4hep.root", 3990)
fig = build(e, rich=[20, 22, 21], groups={20: ("φ → K⁺K⁻", "#d62728")})
fig.write_html("event.html")
build_flow2d(e).write_html("flow_map.html")
build_flow3d(e).write_html("flow_sphere.html")
```

All four builders take an `Event` and return a `plotly.graph_objects.Figure`. None touches
the filesystem, which is what lets the same code run unmodified in the browser under Pyodide.

The flow builders share `groups`, `hide`, `jets` (default `True`), `title`, `note`,
`width` and `height`. Tracks use momentum directions, clusters use position directions
from the detector origin, and jets use their reconstructed axes. Undefined directions
and negative/nonfinite magnitudes are omitted. These are direction-space visualizations;
the overlapping track, cluster and jet collections must not be summed as an energy total.

## Reading

::: delphi_eventdisplay.read
    options:
      members: [read_event, Event, n_entries]

## Collection discovery

::: delphi_eventdisplay.schema
    options:
      members: [read_schema, Schema, Collection, to_dict, load_domains, short_type]

## Geometry

::: delphi_eventdisplay.geometry
    options:
      members: [helix, track_to, curvature_sign, start_points, fit_vertex, vd_residuals, impact_parameter]

## Figures

::: delphi_eventdisplay.figure
    options:
      members: [build, build_flow2d, logo_image]

::: delphi_eventdisplay.figure3d
    options:
      members: [build3d, build_flow3d]

## Site manifest

::: delphi_eventdisplay.pages
    options:
      members: [build_index]
