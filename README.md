# PySuperfish
Python tools for Poisson Superfish calculations

https://laacg.lanl.gov

> :warning: As of April 2024, and since at least May 2023, the download site for
Poisson/Superfish is unavailable. Unfortunately, we do not have any information
about when or if it will be made available again. (see https://github.com/ChristopherMayes/PySuperfish/issues/2)

## Native Windows

Download and install Poisson Supefish from:

https://laacg.lanl.gov

*see note above about availability of Poisson/Superfish files.

## Docker 

Public (you must provide the executables)

https://github.com/hhslepicka/docker-poisson-superfish-nobin

(Private)

https://github.com/hhslepicka/docker-poisson-superfish

```bash
docker pull hhslepicka/poisson-superfish:latest
```

## Shifter (NERSC)

```bash
shifterimg --user $USER pull hhslepicka/poisson-superfish:latest
```


## Singularity

```bash
singularity pull --docker-login docker://hhslepicka/poisson-superfish:latest
```

## macOS setup

Superfish runs on macOS and Linux using docker.

Add `/var/folders/` to Docker's File Sharing list. 

