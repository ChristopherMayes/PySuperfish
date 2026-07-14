"""Typed dictionary shapes for parsed Superfish data."""

from typing import Any, TypedDict

import numpy as np


class SFOGroup(TypedDict):
    """Raw group of lines from an SFO file, delimited by separator lines."""

    raw_type: str
    lines: list[str]


class UnparsedGroup(TypedDict):
    """SFO group with no dedicated parser; ``type`` is the raw type line."""

    type: str
    lines: list[str]


class SFOSummary(TypedDict):
    """Parsed summary-style SFO group, with values and their units."""

    type: str
    data: dict[str, float]
    units: dict[str, str]


class SFOHeader(TypedDict):
    """Parsed SFO header table, keyed by variable name."""

    variable: dict[str, int | float]
    description: dict[str, str]
    in_automesh: dict[str, bool]
    comments: str


class WallSegmentData(TypedDict):
    """Parsed wall segment table, with per-column data and units."""

    wall: dict[str, np.ndarray]
    info: dict[str, Any]
    units: dict[str, str]


class WallSegment(WallSegmentData):
    """Wall segment group, as stored in :class:`SFOOutput`."""

    type: str


class _SFOOutputBase(TypedDict):
    wall_segments: list[WallSegment]
    other: dict[str, UnparsedGroup]


class SFOOutput(_SFOOutputBase, total=False):
    """Fully parsed SFO file, as returned by
    :func:`superfish.parsers.parse_sfo`."""

    summary: SFOSummary
    BeamEnergy: SFOSummary
    header: SFOHeader


class T7Data(TypedDict):
    """Common grid data for a parsed T7 file. Extents are in cm."""

    geometry: str
    problem: str
    zmin: float
    zmax: float
    nz: int
    rmin: float
    rmax: float
    nr: int


class FishT7Data(T7Data):
    """Parsed Fish T7 file. Field arrays have shape (nr, nz)."""

    freq: float
    Ez: np.ndarray
    Er: np.ndarray
    E: np.ndarray
    Hphi: np.ndarray


class PoissonT7Data(T7Data, total=False):
    """Parsed Poisson T7 file.

    Has either ``Er``/``Ez`` (electric, V/cm) or ``Br``/``Bz``
    (magnetic, G) arrays of shape (nr, nz).
    """

    Er: np.ndarray
    Ez: np.ndarray
    Br: np.ndarray
    Bz: np.ndarray


class ExternalFieldData(TypedDict):
    """openPMD external field data, ready to be written to an HDF5 file."""

    attrs: dict[str, Any]
    components: dict[str, np.ndarray]
