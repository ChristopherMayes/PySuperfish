# PySuperfish

Python tools for [Poisson Superfish](https://laacg.lanl.gov) calculations.

PySuperfish wraps the Poisson Superfish suite of electromagnetic field solvers
from LANL, providing:

- A [`Superfish`][superfish.Superfish] class to set up, run, and load the
  output of Fish (RF cavity) and Poisson (magnetostatic/electrostatic)
  problems.
- Automatic execution through Docker, Shifter, or Singularity containers on
  Linux and macOS, or the native executables on Windows.
- Parsers for `.SFO`, `.T7`, and automesh files.
- Plotting utilities for problem geometry and field maps.
- Conversion of field maps to [openPMD-beamphysics](https://github.com/ChristopherMayes/openPMD-beamphysics)
  `FieldMesh` objects.

!!! warning

    As of April 2024, and since at least May 2023, the download site for
    Poisson/Superfish is unavailable. Unfortunately, we do not have any
    information about when or if it will be made available again. See
    [issue #2](https://github.com/ChristopherMayes/PySuperfish/issues/2).

## Quick start

```python
from superfish import Superfish

sf = Superfish("cavity.am")  # an automesh input file
sf.run()

sf.output["sfo"]["summary"]["data"]  # parsed SFO summary
sf.plot_wall()
```

See [Installation](installation.md) for how to set up the Poisson Superfish
executables, and [Usage](usage.md) for a walkthrough.
