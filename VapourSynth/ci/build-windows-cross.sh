#!/bin/sh
set -eu

prefix_input="${1:-.pkg-prefix-mingw}"
builddir="${2:-build-mingw}"
outdir="${3:-dist}"
triplet="${MINGW_TRIPLET:-x86_64-w64-mingw32}"
script_dir="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "${script_dir}/.." && pwd)"
cross_file="${script_dir}/${triplet}.ini"

case "${prefix_input}" in
  /*) prefix="${prefix_input}" ;;
  *) prefix="${repo_root}/${prefix_input}" ;;
esac

sh "${script_dir}/build-deps-mingw.sh" "${prefix_input}"

rm -rf "${repo_root}/${builddir}"
PKG_CONFIG_PATH="${prefix}/lib/pkgconfig" \
CMAKE_PREFIX_PATH="${prefix}" \
meson setup "${repo_root}/${builddir}" "${repo_root}" \
  --cross-file "${cross_file}" \
  -Ddependency_root="${prefix_input}" \
  -Dprefer_static=true \
  -Dc_link_args=-static

meson compile -C "${repo_root}/${builddir}"
"${triplet}-objdump" -p "${repo_root}/${builddir}/vslsmashsource.dll" > "${repo_root}/${builddir}/imports.txt"
python3 "${script_dir}/build-wheel-mingw.py" \
  --dll "${repo_root}/${builddir}/vslsmashsource.dll" \
  --out-dir "${repo_root}/${outdir}" \
  --pyproject "${repo_root}/pyproject.toml"
