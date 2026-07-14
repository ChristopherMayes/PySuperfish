# PySuperfish

Python tools for Poisson Superfish calculations.

**Documentation**: https://christophermayes.github.io/PySuperfish/

## Installation

```bash
pip install pySuperfish
```

PySuperfish also requires the Poisson Superfish executables, which run
natively on Windows or through a container (Docker, Shifter, Singularity) on
Linux and macOS. See below.

## Poisson Superfish executables

https://laacg.lanl.gov

> :warning: As of April 2024, and since at least May 2023, the download site for
Poisson/Superfish is unavailable. Unfortunately, we do not have any information
about when or if it will be made available again. (see https://github.com/ChristopherMayes/PySuperfish/issues/2)

### Native Windows

Download and install Poisson Superfish from:

https://laacg.lanl.gov

*see note above about availability of Poisson/Superfish files.

### Docker

Public (you must provide the executables)

https://github.com/hhslepicka/docker-poisson-superfish-nobin

(Private)

https://github.com/hhslepicka/docker-poisson-superfish

```bash
docker pull hhslepicka/poisson-superfish:latest
```

### Shifter (NERSC)

```bash
shifterimg --user $USER pull hhslepicka/poisson-superfish:latest
```

### Singularity

```bash
singularity pull --docker-login docker://hhslepicka/poisson-superfish:latest
```

### Configuration

The container image, Singularity `.sif` path, and container method can be
configured with the `PYSUPERFISH_CONTAINER_IMAGE`,
`PYSUPERFISH_SINGULARITY_IMAGE`, and `PYSUPERFISH_CONTAINER_METHOD`
environment variables. See the
[documentation](https://christophermayes.github.io/PySuperfish/installation/#environment-variables)
for details.

### macOS setup

Superfish runs on macOS and Linux using docker.

Add `/var/folders/` to Docker's File Sharing list.

## Documentation development

Build the documentation locally with:

```bash
pip install -e ".[docs]"
mkdocs serve
```

The documentation is deployed to GitHub Pages automatically on pushes to
`master` by the [docs workflow](.github/workflows/docs.yml).
