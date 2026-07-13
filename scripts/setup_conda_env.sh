#!/usr/bin/env bash --login
#
# Set up a (shared) conda environment for pySuperfish.
#
# This:
#   1. Creates or reuses a conda environment (by name or explicit prefix).
#   2. Installs pySuperfish and its dependencies into it.
#   3. Builds the Poisson Superfish container image into the environment's
#      share/ directory via docker-poisson-superfish/build.sh, preferring
#      Singularity/Apptainer (the .sif lands at
#      $CONDA_PREFIX/share/pysuperfish/poisson-superfish_latest.sif).
#   4. Wires up activate.d/deactivate.d hooks so PYSUPERFISH_SINGULARITY_IMAGE
#      points at that .sif for everyone who activates the environment.
#
# Usage:
#   scripts/setup_conda_env.sh [options]
#
# Options:
#   -n, --name NAME      conda env name to create/use (default: pysuperfish)
#   -p, --prefix PATH    create/use env at an explicit prefix (overrides --name;
#                        recommended for shared installs, e.g. /opt/envs/pysuperfish)
#       --builder TOOL   force the image builder (singularity|apptainer|podman|docker)
#   -e, --editable       install pySuperfish in editable mode (pip install -e)
#       --no-build       set up the env only; skip building the container image
#   -h, --help           show this help

set -euo pipefail

usage() { sed -n '2,/^set -euo/p' "$0" | sed 's/^# \{0,1\}//; $d'; }

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
BUILD_SH="$REPO_ROOT/docker-poisson-superfish/build.sh"

ENV_NAME="pysuperfish"
ENV_PREFIX=""
BUILDER=""
EDITABLE=0
DO_BUILD=1

while [[ $# -gt 0 ]]; do
  case "$1" in
  -n | --name)
    ENV_NAME="$2"
    shift 2
    ;;
  -p | --prefix)
    ENV_PREFIX="$2"
    shift 2
    ;;
  --builder)
    BUILDER="$2"
    shift 2
    ;;
  -e | --editable)
    EDITABLE=1
    shift
    ;;
  --no-build)
    DO_BUILD=0
    shift
    ;;
  -h | --help)
    usage
    exit 0
    ;;
  *)
    echo "error: unknown argument '$1'" >&2
    usage >&2
    exit 1
    ;;
  esac
done

if command -v micromamba >/dev/null 2>&1 || [[ -n "${MAMBA_EXE:-}" ]]; then
  CONDA=micromamba
  # shellcheck disable=SC1090
  eval "$("${MAMBA_EXE:-micromamba}" shell hook --shell bash)"
  activate_env() { micromamba activate "$1"; }
elif command -v mamba >/dev/null 2>&1; then
  CONDA=mamba
  # shellcheck disable=SC1091
  source "$(mamba info --base)/etc/profile.d/conda.sh"
  activate_env() { conda activate "$1"; }
elif command -v conda >/dev/null 2>&1; then
  CONDA=conda
  # shellcheck disable=SC1091
  source "$(conda info --base)/etc/profile.d/conda.sh"
  activate_env() { conda activate "$1"; }
else
  echo "error: none of micromamba, mamba, or conda found on PATH" >&2
  exit 1
fi

echo "Using: $CONDA."

if [[ -n "$ENV_PREFIX" ]]; then
  TARGET_FLAG=(-p "$ENV_PREFIX")
  TARGET_DESC="$ENV_PREFIX"
else
  TARGET_FLAG=(-n "$ENV_NAME")
  TARGET_DESC="$ENV_NAME"
fi

# Try to activate an existing environment; create it only if activation fails.
if activate_env "$TARGET_DESC" 2>/dev/null; then
  echo ">> Environment already exists, reusing: $TARGET_DESC"
else
  echo ">> Creating conda environment: $TARGET_DESC"
  "$CONDA" create -y -c conda-forge "${TARGET_FLAG[@]}" \
    python numpy matplotlib pip
  activate_env "$TARGET_DESC"
fi

echo ">> Active environment prefix: $CONDA_PREFIX"

echo ">> Installing pySuperfish from $REPO_ROOT"
if [[ "$EDITABLE" -eq 1 ]]; then
  pip install -e "$REPO_ROOT"
else
  pip install "$REPO_ROOT"
fi

SHARE_DIR="$CONDA_PREFIX/share/pysuperfish"
SIF_PATH="$SHARE_DIR/poisson-superfish_latest.sif"

if [[ "$DO_BUILD" -eq 1 ]]; then
  mkdir -p "$SHARE_DIR"
  echo ">> Building container image into $SHARE_DIR"
  PYSUPERFISH_SINGULARITY_IMAGE="$SIF_PATH" bash "$BUILD_SH" ${BUILDER:+"$BUILDER"}
fi

# Wire up activation hooks only when a .sif actually landed in the env. If the
# build fell back to an OCI image (podman/docker), pySuperfish's default image
# tag already applies and no per-env override is needed.
if [[ -f "$SIF_PATH" ]]; then
  ACTIVATE_D="$CONDA_PREFIX/etc/conda/activate.d"
  DEACTIVATE_D="$CONDA_PREFIX/etc/conda/deactivate.d"
  mkdir -p "$ACTIVATE_D" "$DEACTIVATE_D"

  # Use $CONDA_PREFIX (resolved at activation time) so the env stays relocatable.
  cat >"$ACTIVATE_D/pysuperfish.sh" <<'EOF'
export PYSUPERFISH_SINGULARITY_IMAGE="$CONDA_PREFIX/share/pysuperfish/poisson-superfish_latest.sif"
EOF
  cat >"$DEACTIVATE_D/pysuperfish.sh" <<'EOF'
unset PYSUPERFISH_SINGULARITY_IMAGE
EOF
  echo ">> Wired PYSUPERFISH_SINGULARITY_IMAGE -> $SIF_PATH on activation"
  echo ">> Re-activate the environment to pick it up:"
  echo "     conda activate $TARGET_DESC"
elif [[ "$DO_BUILD" -eq 1 ]]; then
  echo ">> No .sif produced (OCI image built instead); using pySuperfish default image tag."
fi

echo ">> Done."
