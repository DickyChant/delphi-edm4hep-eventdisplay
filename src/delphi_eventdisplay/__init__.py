"""DELPHI event display from edm4hep, drawn with Plotly.

    from delphi_eventdisplay import read_event, build
    fig = build(read_event("Y13709.126.edm4hep.root", 3990))
    fig.write_html("event.html")

The command line does the same: `delphi-display FILE --entry N --out event.html`.
"""

from .figure import build, build_flow2d
from .figure3d import build3d, build_flow3d
from .read import Event, n_entries, read_event

__version__ = "0.1.0"
__all__ = ["Event", "build", "build3d", "build_flow2d", "build_flow3d", "n_entries", "read_event"]
