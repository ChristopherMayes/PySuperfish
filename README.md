# pySuperfish
Python tools for Poisson Superfish calculations

https://laacg.lanl.gov

## Native Windows

Download and install Poisson Supefish from:

https://laacg.lanl.gov

## Docker 

(Private)

https://github.com/hhslepicka/docker-poisson-superfish

```bash
docker pull hhslepicka/poisson-superfish:latest
```

Public (you must provide the executables)

https://github.com/hhslepicka/docker-poisson-superfish-nobin

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

