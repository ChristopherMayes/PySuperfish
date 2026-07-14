import os
from glob import glob
from typing import TYPE_CHECKING

from beamphysics import FieldMesh

from superfish.parsers import parse_fish_t7, parse_poisson_t7
from superfish.types import FishT7Data, PoissonT7Data

if TYPE_CHECKING:
    from superfish.superfish import Superfish


def get_t7(path: str) -> list[str]:
    """
    Find T7 files in a directory.

    Parameters
    ----------
    path : str
        Directory to search.

    Returns
    -------
    list of str
        Paths of the T7 files found.
    """
    return glob(os.path.join(path, "*T7"))


def interpolate2d(
    sf: "Superfish",
    zmin: float = -1000,
    zmax: float = 1000,
    nz: int = 100,
    rmin: float = 0,
    rmax: float = 0,
    nr: int = 1,
    return_fieldmesh: bool = False,
) -> FishT7Data | PoissonT7Data | FieldMesh:
    """
    Interpolate the solved field onto a grid using SF7.

    Runs SF7 on a Superfish object, requesting interpolating data, and
    reads the resulting Parmela T7 file.

    SF7 automatically adjusts the bounds if they are requested outside of
    the computational domain.

    TODO: detect the column labels from the SF object

    Parameters
    ----------
    sf : Superfish
        Superfish object that has been run.
    zmin, zmax : float
        z extent of the grid, in the input units of the program.
    nz : int
        Number of z points.
    rmin, rmax : float
        Radial extent of the grid, in the input units of the program.
    nr : int
        Number of radius points.
    return_fieldmesh : bool
        Return an openPMD-beamphysics FieldMesh instead of a t7data dict.

    Returns
    -------
    FishT7Data or PoissonT7Data or FieldMesh
        If ``return_fieldmesh`` is False, a t7data dict with keys:

        - ``rmin``, ``rmax`` : float, radial extent in cm.
        - ``nr`` : int, number of radius points.
        - ``zmin``, ``zmax`` : float, z extent in cm.
        - ``nz`` : int, number of z points.
        - ``freq`` : float, frequency in MHz (fish problems).
        - field components : ndarray of shape (nr, nz).

        Otherwise, an openPMD-beamphysics FieldMesh.
    """

    problem = sf.problem

    # fish and poisson have the opposite conventions:
    if problem == "fish":
        # The interpolation grid
        F = f"""Parmela
{zmin} {rmin} {zmax} {rmax}
{nz - 1} {nr - 1}
End"""

    elif problem == "poisson":
        F = f"""Parmela
{rmin} {zmin} {rmax} {zmax}
{nr - 1} {nz - 1}
End"""
    else:
        raise ValueError(f"unknowm problem: {problem}")

    # Clear old T7
    for f in get_t7(sf.path):
        os.remove(f)

    # Write
    ifile = sf.basename + ".IN7"
    with open(os.path.join(sf.path, ifile), "w") as f:
        f.write(F)

    # Needed so that the fields aren't normalized to 1 MV/m average
    inifile = os.path.join(sf.path, "SF.INI")
    with open(inifile, "w") as f:
        f.write("""[global]
Force1MVperMeter=No""")

    # Needed on WSL, otherwise optional
    t35file = sf.basename + ".T35"

    # Run
    sf.run_cmd("sf7", ifile, t35file)

    # Get the filename
    t7file = get_t7(sf.path)
    assert len(t7file) == 1, "T7 file is missing."
    t7file = t7file[0]

    # Optional fieldmesh parsing
    if return_fieldmesh:
        # Parsing is different for each:
        if problem == "fish":
            type = "electric"
            return FieldMesh.from_superfish(t7file)
        else:
            if sf.output["sfo"]["header"]["variable"]["XJFACT"] == 0:
                type = "electric"
            else:
                type = "magnetic"
            return FieldMesh.from_superfish(t7file, type=type)

    # Parsing is different for each:
    if problem == "fish":
        type = "electric"
        d = parse_fish_t7(t7file)
    else:
        if sf.output["sfo"]["header"]["variable"]["XJFACT"] == 0:
            type = "electric"
        else:
            type = "magnetic"
        d = parse_poisson_t7(t7file, type=type)

    return d
