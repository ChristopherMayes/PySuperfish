# Installation

## Python package

Install from PyPI:

```bash
pip install pySuperfish
```

Or install the development version from GitHub:

```bash
pip install git+https://github.com/ChristopherMayes/PySuperfish.git
```

## Poisson Superfish executables

PySuperfish drives the Poisson Superfish programs (`automesh`, `fish`,
`poisson`, `sfo`, `sf7`, ...), which must be available separately. They run
natively on Windows, or through a container on Linux and macOS.

!!! warning

    As of April 2024, the download site for Poisson/Superfish at
    [laacg.lanl.gov](https://laacg.lanl.gov) is unavailable. See
    [issue #2](https://github.com/ChristopherMayes/PySuperfish/issues/2).

### Native Windows

Download and install Poisson Superfish from [laacg.lanl.gov](https://laacg.lanl.gov)
(see the note above about availability). PySuperfish expects the executables in
`C:\LANL\` by default; this can be changed via the `Superfish._windows_exe_path`
class attribute.

### Docker (Linux, macOS)

Build a container with your own executables using
[docker-poisson-superfish-nobin](https://github.com/hhslepicka/docker-poisson-superfish-nobin),
or pull the private image:

```bash
docker pull hhslepicka/poisson-superfish:latest
```

The image used at runtime can be configured with the
`PYSUPERFISH_CONTAINER_IMAGE` environment variable.

#### macOS note

Add `/var/folders/` to Docker's File Sharing list so that PySuperfish's
temporary working directories can be mounted into the container.

### Shifter (NERSC)

```bash
shifterimg --user $USER pull hhslepicka/poisson-superfish:latest
```

### Singularity / Apptainer

```bash
singularity pull --docker-login docker://hhslepicka/poisson-superfish:latest
```

The path to the `.sif` image can be configured with the
`PYSUPERFISH_SINGULARITY_IMAGE` environment variable (default:
`~/poisson-superfish_latest.sif`).

## Environment variables

| Variable | Default | Purpose |
| --- | --- | --- |
| `PYSUPERFISH_CONTAINER_IMAGE` | `poisson-superfish:latest` | Image tag used when running through Docker or Shifter. |
| `PYSUPERFISH_SINGULARITY_IMAGE` | `~/poisson-superfish_latest.sif` | Path to the Singularity `.sif` image. If Singularity is available and this file exists, it is preferred over the other runtimes. |
| `PYSUPERFISH_CONTAINER_METHOD` | auto-detect | Container method to use: `docker`, `shifter`, or `singularity`. The `container_method` argument to `Superfish` takes precedence. |

The container build script (`docker-poisson-superfish/build.sh`) honors the
two image variables, so a single setting configures both the build and
runtime.

The variables are read when the `superfish` module is imported, so set them
before importing (or override the `Superfish._container_image` /
`Superfish._singularity_image` class attributes afterwards):

```bash
export PYSUPERFISH_CONTAINER_IMAGE="my-registry/poisson-superfish:dev"
export PYSUPERFISH_SINGULARITY_IMAGE="$HOME/images/poisson-superfish.sif"
```

### Inside the container

These are set on the container itself, not read by PySuperfish:

- `INTERACTIVE_FISH` — enables interactive (X11) mode. PySuperfish sets this
  automatically when constructed with `interactive=True` (currently macOS
  only, along with `DISPLAY`).
- `FISH_TIMEOUT` — timeout in seconds for the container's process watcher
  (default: 120). Increase for long-running problems.
