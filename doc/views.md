# Panels and the 3-D scene

## The four panels

The layout of the original matplotlib figure, for slides and papers.

**(a) r-φ, whole event** — track helices, EM showers as towers of length proportional to energy,
and the HPC radius taken from the shower positions themselves (a dashed circle at r ≈ 2.14 m).

**(b) r-z** — the same tracks, with r signed by which thrust hemisphere the track's momentum
points into, so the two jets separate.

**(c) vertex detector, r-φ** — the three VD layers, their radii clustered out of the hits
(62.5, 87.8, 106.5 mm in the reference event), the R-φ hits, the primary vertex and the accepted
AABTAG secondary vertices. The matplotlib version needed a fixed inset for the vertex region;
here you zoom with the mouse, which is the one place interactivity pays for itself immediately.

**(d) RICH** — Cherenkov angle against momentum for chosen tracks, liquid and gas radiators, with
the expected π/K/p curves (n_liq 1.2718, n_gas 1.0019; gas thresholds π 2.26, K 8.0, p 15.2 GeV).
A track above the pion threshold with **zero** gas photons is drawn as a veto marker (▼), because
that absence is a measurement, not missing data.

## The 3-D scene

The layout a general-purpose event display uses: the VD layers and HPC as translucent barrels, the
helices in space, showers as towers pointing outward, vertices as markers, and the beam line.

`scene.aspectmode="data"` keeps it physically proportional, which is why the 2.1 m barrel dwarfs
the vertex region — that ratio is real, and stretching it would be a lie about the detector.

!!! important "A VD hit is not a point in space"
    A type-0 (R-φ) strip measures R and φ but **not** z; a type-1 strip measures R and z but not
    φ. So in three dimensions a single hit constrains a *line*, not a dot.

    * A hit belonging to a track is drawn at the z its **own track** measures — a real quantity.
    * A hit belonging to no track is drawn as the line parallel to the beam that it actually
      constrains, not as an invented point.

## The energy-flow (Poynting) views

The `Poynting` toggle shows a direction-space energy-flow visualization. It is not a calculation
of the electromagnetic Poynting vector **E × H**, and the toggle does not perform a Lorentz-frame
transformation. Objects are placed by their directions, with energy or momentum controlling their
size, to make jet structure and angular balance easier to inspect without detector geometry.

**2-D projected sphere** — a fixed orthographic view of the same unit direction sphere,
seen from azimuth 45° and elevation 30° in the +x/+y/+z octant. A circular silhouette and
projected equator establish the sphere. The rear equator and far-hemisphere rays are dashed;
front rays are solid. Directions on opposite sides can overlap in projection: this is not a
one-to-one angular map. Ray length represents projected direction, **not energy**. Endpoint
marker area is proportional to |p| for tracks or energy for clusters and jets, apart from the
small visibility floor; jets have larger markers. The thrust direction and its opposite are
shown. Charged tracks use momentum directions, EM clusters use their positions relative to
the detector origin, and jets use their momentum directions. Hover retains φ, θ and the
underlying weight, so projection does not substitute a different physical quantity.

**3-D direction sphere** — the same objects sit on a translucent unit sphere. Each has an outward
radial line (an energy *quill*) and an endpoint marker; quill length scales with the square root
of the normalized energy or |p|, and jets receive an additional length multiplier. The dashed
thrust axis passes through the sphere. A cubic aspect ratio keeps direction space undistorted;
the coordinates are dimensionless, not detector lengths. The white scene has no Cartesian box,
background planes, grid or tick labels. Small +x/+y/+z labels sit on the sphere's positive axes
and rotate with it; a compact colour key at the top identifies them (z is the beam direction).

Both views preserve track highlights, hidden-track choices and collection tagging. Hover gives
the underlying kinematics and collection selection works as in the detector views. Invalid or
zero directions and negative/non-finite energies are omitted. Charged tracks and calorimeter
clusters can describe the same particle: this is an angular visualization, not a calibrated
particle-flow reconstruction or an independently additive total-energy measurement.

Generate them with `--view flow2d` or `--view flow3d`, or use `--view all` to write both lab and
both energy-flow views together. `--view both` retains its original meaning: the two lab views.

## What the interactivity adds

* hover names each track: index, charge, momentum, VD hit count, which vertex it starts from
* the legend switches whole classes of object off
* zoom replaces the fixed inset in panel (c)
* selecting a collection dims everything that did not come from it

## All views carry

The DELPHI + EDM4hep mark, embedded as a data URI so it survives PNG/SVG export and an offline
HTML file, anchored top-right — the subplot titles are left-aligned over their own panel, so a
top-left mark lands on "(a) r-φ view".

No title and no run/event line are drawn into the figures: every number lives in `layout.meta`
and the page renders it as live text.
