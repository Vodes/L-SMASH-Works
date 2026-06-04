#!/bin/sh
set -eu

prefix_input="${1:-.pkg-prefix}"
jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
script_dir="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "${script_dir}/.." && pwd)"

case "${prefix_input}" in
  /*) prefix="${prefix_input}" ;;
  *) prefix="${repo_root}/${prefix_input}" ;;
esac
build_root="${repo_root}/.cibw-build"
cleanup_prefix=1

case "${prefix}" in
  /usr|/usr/*|/usr/local|/usr/local/*|/opt/homebrew|/opt/homebrew/*)
    cleanup_prefix=0
    ;;
esac

case "$(uname -s)" in
  MINGW*|MSYS*|CYGWIN*)
    echo "ci/build-deps.sh is for Linux/macOS. Use ci/build-deps-mingw.sh for Windows cross-builds." >&2
    exit 1
    ;;
esac

if ! command -v cmake >/dev/null 2>&1 || ! command -v ninja >/dev/null 2>&1 || { ! command -v nasm >/dev/null 2>&1 && ! command -v yasm >/dev/null 2>&1; }; then
  if command -v dnf >/dev/null 2>&1; then
    dnf install -y cmake ninja-build nasm
  elif command -v yum >/dev/null 2>&1; then
    yum install -y cmake ninja-build nasm
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache cmake ninja nasm
  fi
fi

rm -rf "${build_root}"
if [ "${cleanup_prefix}" -eq 1 ]; then
  rm -rf "${prefix}"
fi
mkdir -p "${build_root}" "${prefix}"

cmake -S "${repo_root}/../obuparse" -B "${build_root}/obuparse" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${prefix}" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_STATIC_LIBS=OFF \
  -DBUILD_TOOLS:BOOL=OFF
cmake --build "${build_root}/obuparse" -j "${jobs}"
cmake --install "${build_root}/obuparse"

cmake -S "${repo_root}/../l-smash" -B "${build_root}/l-smash" -G Ninja \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${prefix}" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_PREFIX_PATH="${prefix}" \
  -DBUILD_SHARED_LIBS=ON \
  -DBUILD_STATIC_LIBS=OFF \
  -DLSMASH_BUILD_TOOLS=OFF
cmake --build "${build_root}/l-smash" -j "${jobs}"
cmake --install "${build_root}/l-smash"

(
  cd "${repo_root}/../FFmpeg"
  if [ -f Makefile ]; then
    make distclean || true
  fi
  ffmpeg_args="
    --prefix=${prefix}
    --libdir=${prefix}/lib
    --enable-gpl
    --enable-version3
    --disable-programs
    --disable-doc
    --disable-avdevice
    --disable-avfilter
    --disable-encoders
    --disable-muxers
    --enable-pic
    --disable-debug
    --disable-static
    --enable-shared
  "
  # shellcheck disable=SC2086
  ./configure ${ffmpeg_args}
  make -j "${jobs}"
  make install -j "${jobs}"
)
