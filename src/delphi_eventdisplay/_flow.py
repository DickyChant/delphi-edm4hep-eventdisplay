"""Shared, finite direction-space objects for the two energy-flow views.

Charged tracks use their reconstructed momentum; clusters use their position
relative to the detector origin; jets use their reconstructed axis. A zero or
non-finite vector has no direction, so it must not invent a point on the sphere.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from .read import Event


def unit_direction(vector):
    """Return a finite unit vector, or None when a direction is undefined."""
    if vector is None:
        return None
    v = np.asarray(vector, dtype=float)
    if v.shape != (3,) or not np.all(np.isfinite(v)):
        return None
    scale = float(np.max(np.abs(v)))
    if scale == 0:
        return None
    v = v / scale  # avoid over/underflow in the norm
    return v / np.linalg.norm(v)


def angles(direction):
    """Unit vector -> azimuth [degrees], cos(theta), polar angle [degrees]."""
    cth = float(np.clip(direction[2], -1.0, 1.0))
    return float(np.degrees(np.arctan2(direction[1], direction[0]))), cth, float(np.degrees(np.arccos(cth)))


@dataclass
class FlowObject:
    direction: np.ndarray
    magnitude: float
    role: str
    index: int

    @property
    def hover(self):
        phi, _cth, theta = angles(self.direction)
        label, quantity = {
            "tracks": ("track", "|p|"),
            "em_clusters": ("EM cluster", "E"),
            "jets": ("jet", "E"),
        }[self.role]
        return (f"<b>{label} {self.index}</b><br>{quantity} = {self.magnitude:.2f} GeV"
                f"<br>φ = {phi:.1f}°, θ = {theta:.1f}°")


def objects(e: Event, hide: dict, jets: bool):
    """Gather only drawable objects; return them and their shared magnitude scale."""
    result = []

    def add(direction, magnitude, role, index):
        unit = unit_direction(direction)
        magnitude = float(magnitude)
        if unit is not None and np.isfinite(magnitude) and magnitude >= 0:
            result.append(FlowObject(unit, magnitude, role, index))

    if e.momentum is not None and e.p_abs is not None:
        for i in e.par:
            if i not in hide:
                add(e.momentum[i], e.p_abs[i], "tracks", i)
    if all(v is not None for v in (e.sh_x, e.sh_y, e.sh_z, e.sh_e)):
        for k, (x, y, z, energy) in enumerate(zip(e.sh_x, e.sh_y, e.sh_z, e.sh_e)):
            add((x, y, z), energy, "em_clusters", k)
    if jets:
        for k, (x, y, z, energy) in enumerate(e.jets):
            add((x, y, z), energy, "jets", k)
    reference = max((obj.magnitude for obj in result), default=1.0) or 1.0
    return result, reference
