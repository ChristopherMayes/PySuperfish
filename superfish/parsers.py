from typing import Any, cast

import numpy as np

from .types import (
    FishT7Data,
    PoissonT7Data,
    SFOGroup,
    SFOHeader,
    SFOOutput,
    SFOSummary,
    UnparsedGroup,
    WallSegment,
    WallSegmentData,
)


def parse_automesh(file: str) -> list[str]:
    """
    Read an automesh input file into lines.

    Parameters
    ----------
    file : str
        Path to the automesh (.AM) input file.

    Returns
    -------
    list of str
        Lines of the file, with line endings preserved.
    """
    return open(file, "r").readlines()


def parse_sfo(filename: str, verbose: bool = False) -> SFOOutput:
    """
    Master parser for the SFO file.

    Parameters
    ----------
    filename : str
        Path to the SFO file.
    verbose : bool
        Print a message for groups that have no parser.

    Returns
    -------
    SFOOutput
        Parsed output with keys:

        - ``wall_segments`` : list of dict, one per wall segment.
        - ``summary`` : dict with ``data`` and ``units`` for the summary
          quantities (frequency, Q, ...), if present.
        - ``BeamEnergy`` : dict with ``data`` and ``units``, if present.
        - ``header`` : dict of problem variables, descriptions, and comments.
        - ``other`` : dict of unparsed groups, keyed by their raw type line.
    """

    groups = parse_sfo_into_groups(filename)

    d: SFOOutput = {"wall_segments": [], "other": {}}

    for g in groups:
        dat = process_group(g, verbose=verbose)
        gtype = dat["type"]

        if gtype == "wall_segment":
            d["wall_segments"].append(cast(WallSegment, dat))
        elif gtype == "summary":
            d["summary"] = cast(SFOSummary, dat)
        elif gtype == "BeamEnergy":
            d["BeamEnergy"] = cast(SFOSummary, dat)
        elif gtype == "header":
            d["header"] = parse_header_lines(cast(UnparsedGroup, dat)["lines"])

        else:
            d["other"][gtype] = cast(UnparsedGroup, dat)

    # update Kinetic energy in 'summary' with the right value
    if "summary" in d and "BeamEnergy" in d:
        d["summary"]["data"]["kinetic_energy"] = (
            d["BeamEnergy"]["data"]["BeamEnergy"] / 1e6
        )
        d["summary"]["units"]["kinetic_energy"] = "MeV"

    return d


def parse_sfo_into_groups(filename: str) -> list[SFOGroup]:
    """
    Parse an SFO file into groups.

    Groups are delimited by separator lines that start with
    ``-------------------``.

    Parameters
    ----------
    filename : str
        Path to the SFO file.

    Returns
    -------
    list of SFOGroup
        One dict per group, with keys:

        - ``raw_type`` : str, the first line of the group.
        - ``lines`` : list of str, the remaining lines.
    """

    with open(filename, "r") as f:
        lines = f.readlines()

    sep = "-------------------"

    g: SFOGroup = {"raw_type": "header", "lines": []}
    groups: list[SFOGroup] = [g]

    new_group = False

    for line in lines:
        line = line.strip()

        # Skip empty lines
        if not line:
            continue

        # Look for new group
        if line.startswith(sep):
            new_group = True
            continue

        # Check for new group
        if new_group:
            gname = line
            new_group = False
            g = {"raw_type": gname, "lines": []}
            groups.append(g)
            continue

        # regular line
        g["lines"].append(line)

    return groups


def process_group(
    group: SFOGroup,
    verbose: bool = False,
) -> SFOSummary | WallSegment | UnparsedGroup:
    """
    Process a single output group dict into usable data.

    Parameters
    ----------
    group : SFOGroup
        Group dict with ``raw_type`` and ``lines`` keys, as returned by
        :func:`parse_sfo_into_groups`.
    verbose : bool
        Print a message when no parser exists for the group type.

    Returns
    -------
    SFOSummary or WallSegment or UnparsedGroup
        Parsed group with a ``type`` key identifying the group
        (``summary``, ``wall_segment``, ``BeamEnergy``, or the raw type
        line for unparsed groups) and type-dependent data keys.
    """

    rtype = group["raw_type"]
    lines = group["lines"]

    if rtype.startswith("All calculated values below refer to the mesh geometry only"):
        data, units = parse_sfo_summary_group(lines)
        return SFOSummary(type="summary", data=data, units=units)

    if rtype.startswith("Power and fields on wall segment") or rtype.startswith(
        "Fields on segment"
    ):
        line1 = rtype  # This should be parsed fully
        seg = parse_sfo_segment([line1] + lines)
        return WallSegment(
            type="wall_segment",
            wall=seg["wall"],
            info=seg["info"],
            units=seg["units"],
        )

    if rtype.startswith(
        "The field normalization factor ASCALE for this problem is based"
    ):
        data, units = parse_sfo_beam_energy(lines)
        return SFOSummary(type="BeamEnergy", data=data, units=units)

    # No parser yet:
    if verbose:
        print("No parser for:", rtype)

    return UnparsedGroup(type=rtype, lines=lines)


# _________________________________
# T7 files


def parse_fish_t7(t7file: str, geometry: str = "cylindrical") -> FishT7Data:
    """
    Parse a Fish T7 file.

    The T7 header should have::

        xmin(cm), xmax(cm), nx-1
        freq(MHz)
        ymin(cm), ymax(cm), ny-1

    followed by 4 columns of data: Ez, Er, E, Hphi.

    TODO: Poisson problems, detect rectangular or cylindrical coordinates

    Parameters
    ----------
    t7file : str
        Path to the T7 file.
    geometry : str
        Problem geometry. Only ``"cylindrical"`` is currently handled.

    Returns
    -------
    FishT7Data
        Parsed data with keys:

        - ``geometry`` : str
        - ``problem`` : ``"fish"``
        - ``zmin``, ``zmax`` : float, z extent in cm.
        - ``nz`` : int, number of z points.
        - ``rmin``, ``rmax`` : float, radial extent in cm.
        - ``nr`` : int, number of radius points.
        - ``freq`` : float, frequency in MHz.
        - ``Ez``, ``Er``, ``E``, ``Hphi`` : ndarray of shape (nr, nz).
    """

    # Read header
    # xmin(cm), xmax(cm), nx-1
    # freq(MHz)
    # ymin(cm), ymax(cm), ny-1
    with open(t7file, "r") as f:
        line1 = f.readline().split()
        freq_MHz = float(f.readline())
        line3 = f.readline().split()

    nz = int(line1[2]) + 1
    nr = int(line3[2]) + 1

    # Read and reshape. Columns are Ez, Er, E, Hphi
    dat4 = np.loadtxt(t7file, skiprows=3).reshape(nr, nz, 4)

    return FishT7Data(
        geometry=geometry,
        problem="fish",
        zmin=float(line1[0]),
        zmax=float(line1[1]),
        nz=nz,
        freq=freq_MHz,
        rmin=float(line3[0]),
        rmax=float(line3[1]),
        nr=nr,
        Ez=dat4[:, :, 0],
        Er=dat4[:, :, 1],
        E=dat4[:, :, 2],
        Hphi=dat4[:, :, 3],
    )


def parse_poisson_t7(
    t7file: str,
    type: str = "electric",
    geometry: str = "cylindrical",
) -> PoissonT7Data:
    """
    Parse a Poisson T7 file.

    The T7 header should have::

        xmin(cm), xmax(cm), nx-1
        ymin(cm), ymax(cm), ny-1

    followed by 2 columns of data:

    - ``type == "electric"`` : Er, Ez in V/cm.
    - ``type == "magnetic"`` : Br, Bz in G.

    Parameters
    ----------
    t7file : str
        Path to the T7 file.
    type : {"electric", "magnetic"}
        Type of field data in the file.
    geometry : str
        Problem geometry. Only ``"cylindrical"`` is currently handled.

    Returns
    -------
    PoissonT7Data
        Parsed data with keys:

        - ``geometry`` : str
        - ``problem`` : ``"poisson"``
        - ``zmin``, ``zmax`` : float, z extent in cm.
        - ``nz`` : int, number of z points.
        - ``rmin``, ``rmax`` : float, radial extent in cm.
        - ``nr`` : int, number of radius points.
        - ``Er``, ``Ez`` or ``Br``, ``Bz`` : ndarray of shape (nr, nz).
    """
    assert geometry == "cylindrical", "TODO: other geometries"

    if type not in ("electric", "magnetic"):
        raise ValueError(f"Unknown type: {type}. Allowed: 'electric' or 'magnetic'")

    # Read header
    # xmin(cm), xmax(cm), nx-1    # r in cylindrical geometry
    # ymin(cm), ymax(cm), ny-1    # z in cylindrical geometry
    with open(t7file, "r") as f:
        xline = f.readline().split()
        yline = f.readline().split()

    nr = int(xline[2]) + 1
    nz = int(yline[2]) + 1

    d: PoissonT7Data = {
        "geometry": geometry,
        "problem": "poisson",
        "rmin": float(xline[0]),
        "rmax": float(xline[1]),
        "nr": nr,
        "zmin": float(yline[0]),
        "zmax": float(yline[1]),
        "nz": nz,
    }

    # Read and reshape
    dat = np.loadtxt(t7file, skiprows=2).reshape(nz, nr, 2)

    if type == "electric":
        d["Er"] = dat[:, :, 0].T
        d["Ez"] = dat[:, :, 1].T
    else:
        d["Br"] = dat[:, :, 0].T
        d["Bz"] = dat[:, :, 1].T

    return d


# _________________________________
# _________________________________
# Individual parsers


# _________________________________
# Header


def parse_header_variable(line: str) -> tuple[str, int | float, str, bool]:
    """
    Parse a single variable line from the SFO header table.

    The line follows the table header::

        Variable Code         Value     Description

    Parameters
    ----------
    line : str
        Line from the header table.

    Returns
    -------
    key : str
        Variable name.
    value : int or float
        Variable value.
    description : str
        Variable description.
    in_automesh : bool
        True if the variable was set in the automesh input (code ``A``).
    """
    x = line.split()

    key = x[0]

    if x[1] == "A":
        in_automesh = True

        s = x[2]
        d = x[3:]
    else:
        in_automesh = False
        s = x[1]
        d = x[2:]

    descrip = " ".join(d)

    try:
        val = int(s)
    except ValueError:
        val = float(s)

    return key, val, descrip, in_automesh


def parse_header_lines(lines: list[str]) -> SFOHeader:
    """
    Parse the SFO header lines.

    Parameters
    ----------
    lines : list of str
        Lines of the header group.

    Returns
    -------
    SFOHeader
        Parsed header with keys:

        - ``variable`` : dict of variable name to value.
        - ``description`` : dict of variable name to description.
        - ``in_automesh`` : dict of variable name to bool.
        - ``comments`` : str, lines preceding the variable table.
    """

    header = "Variable Code         Value     Description"

    d = {}
    description = {}
    in_automesh = {}

    comments = []

    in_header = False
    for line in lines:
        if line == header:
            in_header = True
            continue
        if not in_header:
            comments.append(line)
            continue

        key, val, descrip, in_am = parse_header_variable(line)

        d[key] = val
        description[key] = descrip
        in_automesh[key] = in_am

    return {
        "variable": d,
        "description": description,
        "in_automesh": in_automesh,
        "comments": "\n".join(comments),
    }


# _________________________________
# Wall segments


def parse_wall_segment_line1(line: str) -> dict[str, int]:
    """
    Parse the first line of a wall segment group.

    Helper for :func:`parse_sfo_segment`.

    Parameters
    ----------
    line : str
        Line of the form
        ``Power and fields on wall segment 1   K,L = 1,2 to 3,4``.

    Returns
    -------
    dict
        Keys ``segment_number``, ``K_beg``, ``L_beg``, ``K_end``, ``L_end``.
    """
    d = {}
    ix, x = line.split("segment")[1].split(" K,L =")
    d["segment_number"] = int(float((ix)))
    kl0, kl1 = x.split("to")
    k0, l0 = kl0.split(",")
    d["K_beg"], d["L_beg"] = int(k0), int(l0)
    k1, l1 = kl1.split(",")
    d["K_end"], d["L_end"] = int(k1), int(l1)
    return d


def parse_sfo_segment(lines: list[str]) -> WallSegmentData:
    """
    Parse a wall segment group.

    The group starts with a line like
    ``Power and fields on wall segment``.

    Parameters
    ----------
    lines : list of str
        Lines of the wall segment group, including the first (type) line.

    Returns
    -------
    WallSegmentData
        Parsed segment with keys:

        - ``wall`` : dict of column name to ndarray of values.
        - ``info`` : dict of segment info (segment number, K/L range, and
          any ``key = value`` lines).
        - ``units`` : dict of column name to unit string.
    """

    # key = value lines

    info: dict[str, Any] = dict(parse_wall_segment_line1(lines[0]))

    inside = False
    fields: dict[str, list[float]] | None = None
    units: dict[str, str] | None = None

    for L in lines[1:]:
        L = L.strip()

        # Look for key=value
        if "=" in L:
            key, val = L.split("=")
            info[key.strip()] = val
            continue

        if L.startswith("K    L"):
            nskip = 2
            fields = {name.strip("|"): [] for name in L.split()[nskip:]}
            continue
        elif L.startswith("m     K     L"):
            nskip = 3
            fields = {name.strip("|"): [] for name in L.split()[nskip:]}
            continue

        if not fields:
            continue

        # Look for units
        if fields and not units:
            unit_labels = L.split()
            assert len(unit_labels) == len(fields), print(unit_labels)
            # make dict
            units = dict(zip(list(fields), unit_labels))
            inside = True
            continue

        # This might come at the end
        if L.startswith("Summary"):
            inside = False

        # Must be inside. Add data
        if inside:
            x = [float(y) for y in L.split()]
            # Special care if there are blanks for the skip columns
            if len(x) == len(fields) + nskip:
                x = x[nskip:]
            for i, name in enumerate(fields):
                fields[name].append(x[i])

    # Exiting
    assert fields is not None and units is not None, "No field table found"
    wall = {k: np.array(v) for k, v in fields.items()}

    return {"wall": wall, "info": info, "units": units}


# _________________________________
# Summary


def parse_sfo_beam_energy(
    lines: list[str],
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Parse the beam energy group.

    Extracts the ``V0`` value from the field normalization group.

    Parameters
    ----------
    lines : list of str
        Lines of the group.

    Returns
    -------
    values : dict
        ``{"BeamEnergy": value}``.
    units : dict
        ``{"BeamEnergy": unit}``.
    """
    d_vals = {}
    d_units = {}
    for line in lines:
        line = line.strip()
        if line.startswith("V0"):
            parts = line.split("=")[-1].strip().split(" ")
            data = float(parts[0])
            unit = parts[1]
    d_vals["BeamEnergy"] = data
    d_units["BeamEnergy"] = unit
    return d_vals, d_units


def parse_sfo_summary_group(
    lines: list[str],
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Parse the summary group lines.

    Parameters
    ----------
    lines : list of str
        Lines of the summary group.

    Returns
    -------
    values : dict
        Summary quantity name to value.
    units : dict
        Summary quantity name to unit string.
    """
    d_vals = {}
    d_units = {}
    for line in lines:
        if line == "":
            break
        else:
            d_val, d_unit = parse_sfo_summary_group_line(line)
            d_vals.update(d_val)
            d_units.update(d_unit)
    return d_vals, d_units


def parse_simple_summary_line(
    line: str,
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Parse a simple summary line with one key and one value.

    Parameters
    ----------
    line : str
        Line of the form ``key = value [unit]``.

    Returns
    -------
    values : dict
        Key to value. Empty if the line has no ``=``.
    units : dict
        Key to unit string (empty string if the line has no unit).
    """
    d_val = {}
    d_unit = {}
    parts = line.split("=")
    if len(parts) == 1:
        return d_val, d_unit
    key = parts[0].strip()
    val = parts[-1].strip().split(" ")
    d_val[key] = float(val[0])
    if len(val) > 1:
        d_unit[key] = val[1]
    else:
        d_unit[key] = ""
    return d_val, d_unit


def parse_sfo_summary_group_line(
    line: str,
) -> tuple[dict[str, float], dict[str, str]]:
    """
    Parse a single summary group line.

    Handles the special multi-value lines (field normalization,
    integration path, beta, Q, Rs*Q, r/Q, average/maximum fields);
    anything else falls back to :func:`parse_simple_summary_line`.

    Parameters
    ----------
    line : str
        Summary line.

    Returns
    -------
    values : dict
        Quantity name to value.
    units : dict
        Quantity name to unit string.
    """
    d_val = {}
    d_unit = {}
    if line.startswith("Field normalization"):
        parts = line.split("=")
        val = parts[-1]
        val = val.strip()
        val = val.split(" ")
        d_val["Enorm"] = float(val[0])
        d_unit["Enorm"] = val[1]
        return d_val, d_unit
    # 'for the integration path from point Z1,R1 =     50.50000 cm,   0.00000 cm',
    if line.startswith("for the integration path"):
        parts = line.split("=")
        val = parts[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        v2 = val[1].strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val["integration_Z1"] = float(v1)
        d_unit["integration_Z1"] = "cm"
        d_val["integration_R1"] = float(v2)
        d_unit["integration_R1"] = "cm"
        return d_val, d_unit
    #  'to ending point                     Z2,R2 =     50.51000 cm,   0.00000 cm',
    if line.startswith("to ending point"):
        parts = line.split("=")
        val = parts[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        v2 = val[1].strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val["integration_Z2"] = float(v1)
        d_unit["integration_Z2"] = "cm"
        d_val["integration_R2"] = float(v2)
        d_unit["integration_R2"] = "cm"
        return d_val, d_unit
    if line.startswith("Beta "):
        # custom parse the beta line
        parts = line.split("=")
        beta = parts[1].strip()
        beta = beta.split(" ")
        beta = beta[0]
        ke = parts[-1]
        ke = ke.strip()
        ke = ke.split(" ")
        ke = ke[0]
        d_val["beta"] = float(beta)
        d_val["kinetic_energy"] = float(ke)
        d_unit["beta"] = ""
        d_unit["kinetic_energy"] = "MeV"
        return d_val, d_unit
    #   'Q    =  0.334933E+10      Shunt impedance =  2001715.397 MOhm/m',
    if line.startswith("Q "):
        # Q factor line
        parts = line.split("=")
        v1 = parts[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = parts[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val["Q"] = float(v1)
        d_val["Shunt impedance"] = float(v2)
        d_unit["Q"] = ""
        d_unit["Shunt impedance"] = "MOhm/m"
        return d_val, d_unit
    #          'Rs*Q =    81.364 Ohm                Z*T*T =  1956056.397 MOhm/m',
    if line.startswith("Rs*Q "):
        # Q factor line
        parts = line.split("=")
        v1 = parts[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = parts[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val["Rs*Q"] = float(v1)
        d_val["Z*T*T"] = float(v2)
        d_unit["Rs*Q"] = "Ohm"
        d_unit["Z*T*T"] = "MOhm/m"
        return d_val, d_unit
    # 'r/Q  =   134.323 Ohm  Wake loss parameter =      0.04044 V/pC',
    if line.startswith("r/Q "):
        # r/Q line
        parts = line.split("=")
        v1 = parts[1].strip()
        v1 = v1.split(" ")
        v1 = v1[0]
        v2 = parts[-1]
        v2 = v2.strip()
        v2 = v2.split(" ")
        v2 = v2[0]
        d_val["r/Q"] = float(v1)
        d_val["Wake loss parameter"] = float(v2)
        d_unit["r/Q"] = "Ohm"
        d_unit["Wake loss parameter"] = "V/pC"
        return d_val, d_unit
    #  'Average magnetic field on the outer wall  =      16678.8 A/m, 0.337887 mW/cm^2',
    if line.startswith("Average magnetic "):
        # Average magnetic field line
        parts = line.split("=")
        val = parts[-1]
        val = val.strip()
        val = val.split(",")
        v1 = val[0].split(" ")
        v1 = v1[0]
        d_val["AvgH"] = float(v1)
        d_unit["AvgH"] = "A/m"
        return d_val, d_unit
    #  'Maximum H (at Z,R = 25.1487,18.4727)      =       41189. A/m, 2.06066 mW/cm^2',
    if line.startswith("Maximum H "):
        # Maximum H line
        parts = line.split("=")
        val = parts[1].strip()
        val = val.split(",")
        v1 = val[0]
        v2 = val[1].split(")")
        v2 = v2[0]
        v3 = parts[-1]
        v3 = v3.strip()
        v3 = v3.split(",")
        v3 = v3[0].split(" ")
        v3 = v3[0]
        d_val["MaxH_z"] = float(v1)
        d_val["MaxH_r"] = float(v2)
        d_val["MaxH"] = float(v3)
        d_unit["MaxH_z"] = "cm"
        d_unit["MaxH_r"] = "cm"
        d_unit["MaxH"] = "A/m"
        return d_val, d_unit
    #  'Maximum E (at Z,R = 49.9969,0.624269)     =      41.1564 MV/m, 2.84161 Kilp.',
    if line.startswith("Maximum E "):
        # Maximum E line
        parts = line.split("=")
        val = parts[1].strip()
        val = val.split(",")
        v1 = val[0]
        v2 = val[1].split(")")
        v2 = v2[0]
        v3 = parts[-1]
        v3 = v3.strip()
        v3 = v3.split(",")
        v3 = v3[0].split(" ")
        v3 = v3[0]
        d_val["MaxE_z"] = float(v1)
        d_val["MaxE_r"] = float(v2)
        d_val["MaxE"] = float(v3)
        d_unit["MaxE_z"] = "cm"
        d_unit["MaxE_r"] = "cm"
        d_unit["MaxE"] = "MV/m"
        return d_val, d_unit
    else:
        d_val, d_unit = parse_simple_summary_line(line)
    return d_val, d_unit
