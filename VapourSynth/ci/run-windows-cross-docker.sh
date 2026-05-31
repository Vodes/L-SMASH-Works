#!/bin/sh
set -eu

script_dir="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "${script_dir}/../.." && pwd)"
container_tool="${CONTAINER_TOOL:-}"
image_name="${LSMAS_WINDOWS_CROSS_IMAGE:-lsmas-windows-cross}"

if [ -z "${container_tool}" ]; then
  if command -v docker >/dev/null 2>&1; then
    container_tool=docker
  elif command -v podman >/dev/null 2>&1; then
    container_tool=podman
  else
    echo "Need docker or podman in PATH." >&2
    exit 1
  fi
fi

volume_suffix=
user_args=
if [ "${container_tool}" = "podman" ]; then
  volume_suffix=:Z
  user_args="--userns keep-id"
else
  user_args="--user $(id -u):$(id -g)"
fi

"${container_tool}" build \
  -t "${image_name}" \
  -f "${script_dir}/Dockerfile.mingw-cross" \
  "${script_dir}"

"${container_tool}" run --rm \
  ${user_args} \
  -e HOME=/tmp/lsmas-home \
  -v "${repo_root}:/work/L-SMASH-Works${volume_suffix}" \
  -w /work/L-SMASH-Works/VapourSynth \
  "${image_name}" \
  sh -lc 'mkdir -p "$HOME" && git config --global --add safe.directory /work/L-SMASH-Works && sh ci/build-windows-cross.sh .pkg-prefix-mingw build-mingw dist'
