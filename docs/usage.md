# Usage

The main entry point is the [`Superfish`][superfish.Superfish] class, which
manages a working directory, runs the Poisson Superfish programs, and parses
their output.

## Running a problem

```python
from superfish import Superfish

sf = Superfish("cavity.am", problem="fish", verbose=True)
sf.run()
```

- `problem="fish"` runs the RF cavity solver chain (`automesh`, `fish`,
  `sfo`); `problem="poisson"` runs the magnetostatic/electrostatic chain
  (`automesh`, `poisson`, `sfo`).
- By default a temporary working directory is used (`use_tempdir=True`); pass
  `workdir=` to keep files in a specific location.
- `use_container="auto"` picks a container runtime (Singularity, Docker, or
  Shifter) on Linux/macOS, or runs the native executables on Windows. Pass
  `use_container=False` to force native execution. The image used is
  configurable via
  [environment variables](installation.md#environment-variables).
- `container_method="docker"` (or `"shifter"`, `"singularity"`) forces a
  specific container runtime instead of auto-detecting the first available
  one. The default can also be set with the `PYSUPERFISH_CONTAINER_METHOD`
  environment variable.

## Inspecting output

`run()` automatically loads output; `load_output()` can be called manually.
Parsed results live in the `output` dictionary:

```python
sf.output["sfo"]["header"]           # problem variables and descriptions
sf.output["sfo"]["summary"]["data"]  # summary quantities (frequency, Q, ...)
sf.output["sfo"]["wall"]             # wall segments and power densities
```

## Field maps

Interpolate the solved field onto a grid using SF7.
[`interpolate`][superfish.Superfish.interpolate] works in the problem's
length units and returns a `t7data` dictionary, while
[`fieldmesh`][superfish.Superfish.fieldmesh] works in meters and returns an
[openPMD-beamphysics](https://github.com/ChristopherMayes/openPMD-beamphysics)
`FieldMesh` for use with particle tracking codes:

```python
t7data = sf.interpolate(zmin=0, zmax=30, nz=300, rmin=0, rmax=3, nr=30)

fm = sf.fieldmesh(zmin=0, zmax=0.30, nz=300, rmin=0, rmax=0.03, nr=30)
fm.write("cavity_field.h5")
```

## Plotting

```python
sf.plot_wall()  # problem geometry
```

See the example notebooks in the navigation for complete worked problems.
