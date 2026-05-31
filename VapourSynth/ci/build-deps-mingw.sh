#!/bin/sh
set -eu

triplet="${MINGW_TRIPLET:-x86_64-w64-mingw32}"
prefix_input="${1:-.pkg-prefix-mingw}"
jobs="$(getconf _NPROCESSORS_ONLN 2>/dev/null || sysctl -n hw.ncpu 2>/dev/null || echo 4)"
script_dir="$(CDPATH= cd -- "$(dirname "$0")" && pwd)"
repo_root="$(CDPATH= cd -- "${script_dir}/.." && pwd)"
toolchain_file="${script_dir}/${triplet}.cmake"

case "${prefix_input}" in
  /*) prefix="${prefix_input}" ;;
  *) prefix="${repo_root}/${prefix_input}" ;;
esac

build_root="${repo_root}/.cross-build-${triplet}"

for tool in cmake ninja nasm pkg-config "${triplet}-gcc" "${triplet}-g++" "${triplet}-windres"; do
  if ! command -v "${tool}" >/dev/null 2>&1; then
    echo "Missing required tool: ${tool}" >&2
    exit 1
  fi
done

rm -rf "${build_root}" "${prefix}"
mkdir -p "${build_root}" "${prefix}"

obuparse_source="${build_root}/obuparse-src"
mkdir -p "${obuparse_source}"
cp -a "${repo_root}/../obuparse/." "${obuparse_source}"
rm -rf "${obuparse_source}/.git"
git -C "${obuparse_source}" init -q
git -C "${obuparse_source}" apply "${repo_root}/ci/patches/obuparse-build-tools.patch"

cmake -S "${obuparse_source}" -B "${build_root}/obuparse" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="${toolchain_file}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${prefix}" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_STATIC_LIBS=ON \
  -DBUILD_TOOLS:BOOL=OFF
cmake --build "${build_root}/obuparse" -j "${jobs}"
cmake --install "${build_root}/obuparse"

cmake -S "${repo_root}/../l-smash" -B "${build_root}/l-smash" -G Ninja \
  -DCMAKE_TOOLCHAIN_FILE="${toolchain_file}" \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_INSTALL_PREFIX="${prefix}" \
  -DCMAKE_INSTALL_LIBDIR=lib \
  -DCMAKE_PREFIX_PATH="${prefix}" \
  -DBUILD_SHARED_LIBS=OFF \
  -DBUILD_STATIC_LIBS=ON \
  -DLSMASH_BUILD_TOOLS=OFF
cmake --build "${build_root}/l-smash" -j "${jobs}"
cmake --install "${build_root}/l-smash"

mkdir -p "${build_root}/ffmpeg"
rm -f \
  "${repo_root}/../FFmpeg/config.asm" \
  "${repo_root}/../FFmpeg/config.h" \
  "${repo_root}/../FFmpeg/config_components.asm" \
  "${repo_root}/../FFmpeg/config_components.h" \
  "${repo_root}/../FFmpeg/ffbuild/.config" \
  "${repo_root}/../FFmpeg/ffbuild/config.fate" \
  "${repo_root}/../FFmpeg/ffbuild/config.log" \
  "${repo_root}/../FFmpeg/ffbuild/config.mak" \
  "${repo_root}/../FFmpeg/ffbuild/config.sh"
(
  cd "${build_root}/ffmpeg"
  PKG_CONFIG="pkg-config" \
  PKG_CONFIG_PATH="${prefix}/lib/pkgconfig" \
  "${repo_root}/../FFmpeg/configure" \
    --prefix="${prefix}" \
    --libdir="${prefix}/lib" \
    --target-os=mingw32 \
    --arch=x86_64 \
    --cross-prefix="${triplet}-" \
    --cc="${triplet}-gcc" \
    --cxx="${triplet}-g++" \
    --ar="${triplet}-gcc-ar" \
    --ranlib="${triplet}-gcc-ranlib" \
    --windres="${triplet}-windres" \
    --enable-gpl \
    --enable-version3 \
    --disable-programs \
    --disable-doc \
    --disable-avdevice \
    --disable-avfilter \
    --disable-encoders \
    --disable-muxers \
    --enable-static \
    --disable-shared \
    --pkg-config-flags=--static \
    --enable-pic \
    --disable-debug
  make -j "${jobs}"
  make install -j "${jobs}"
)

for pc in "${prefix}"/lib/pkgconfig/libav*.pc; do
  [ -f "${pc}" ] || continue
  sed -i 's/[[:space:]]-latomic//g' "${pc}"
done
