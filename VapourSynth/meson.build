project('L-SMASH-Works', 'c',
  default_options: ['buildtype=release', 'b_ndebug=if-release', 'c_std=c99'],
  meson_version: '>=0.64.0',
  version: run_command('python3', files('ci/version.py'), meson.project_source_root(), check: true).stdout().strip()
)

cc = meson.get_compiler('c')

version_h = declare_dependency(
    sources: vcs_tag(
        command: ['git', 'describe', '--tags', '--long'],
        input: 'version.h.in',
        output: 'version.h'
    )
)
no_as_needed = declare_dependency(link_args: ['-Wl,--no-as-needed'])
as_needed = declare_dependency(link_args: ['-Wl,--as-needed'])

add_project_arguments(
  '-DXXH_INLINE_ALL',
  '-D_FILE_OFFSET_BITS=64',
  '-DDEFAULT_CACHEDIR=' + get_option('cachedir'),
  language: 'c'
)

sources = [
  'libavsmash_source.c',
  'lsmashsource.c',
  'lsmashsource.h',
  'lwlibav_source.c',
  'video_output.c',
  'video_output.h',
  '../common/decode.c',
  '../common/decode.h',
  '../common/libavsmash.c',
  '../common/libavsmash.h',
  '../common/libavsmash_video.c',
  '../common/libavsmash_video.h',
  '../common/lwindex.c',
  '../common/lwindex.h',
  '../common/lwindex_sscanf_unrolled.h',
  '../common/lwindex_utils.c',
  '../common/lwindex_utils.h',
  '../common/lwindex_parser.c',
  '../common/lwindex_parser.h',
  '../common/lwlibav_audio.c',
  '../common/lwlibav_audio.h',
  '../common/lwlibav_dec.c',
  '../common/lwlibav_dec.h',
  '../common/lwlibav_video.c',
  '../common/lwlibav_video.h',
  '../common/osdep.c',
  '../common/osdep.h',
  '../common/utils.c',
  '../common/utils.h',
  '../common/video_output.c',
  '../common/video_output.h'
]

py = import('python').find_installation(pure: false)
fs = import('fs')

vsinclude = get_option('vapoursynth_include')
if vsinclude == ''
  # prefer the local vapoursynth-include submodule
  vsinclude = '../vapoursynth-include/include'
endif

if not fs.is_dir(vsinclude)
  if get_option('vapoursynth_include') != ''
    error('vapoursynth_include does not exist: ' + vsinclude)
  endif
  # fallback to the installed python package
  vsinclude = run_command(py, '-c', 'import vapoursynth as vs; print(vs.get_include())', check: true).stdout().strip()
endif

dep_include = []
dep_root = get_option('dependency_root')
prefer_static = get_option('prefer_static')
if dep_root != ''
  dep_root_lookup = dep_root
  if not fs.is_absolute(dep_root)
    dep_root_lookup = join_paths(meson.project_source_root(), dep_root)
  endif
  dep_lib = [
    join_paths(dep_root_lookup, 'lib'),
    join_paths(dep_root_lookup, 'lib64'),
    join_paths(dep_root_lookup, 'bin')
  ]
  dep_include += [join_paths(dep_root, 'include')]
  if host_machine.system() == 'windows' and prefer_static
    obuparse_dep = dependency('obuparse', method: 'cmake', modules: ['OBUParse::static'], required: false)
    if not obuparse_dep.found()
      obuparse_dep = cc.find_library('obuparse', dirs: dep_lib, required: false)
    endif
    lsmash_dep = dependency('lsmash', method: 'cmake', modules: ['LSMASH::static'], required: false)
    if not lsmash_dep.found()
      lsmash_dep = cc.find_library('lsmash', dirs: dep_lib, required: true)
    endif
    deps = [
      lsmash_dep,
      dependency('libavcodec', static: true),
      dependency('libavformat', static: true),
      dependency('libswresample', static: true),
      dependency('libavutil', static: true),
      dependency('libswscale', static: true),
      version_h
    ]
    if obuparse_dep.found()
      deps = [no_as_needed, obuparse_dep, as_needed] + deps
    endif
  else
    obuparse_dep = cc.find_library('obuparse', dirs: dep_lib, required: false)
    deps = [
      cc.find_library('lsmash', dirs: dep_lib, required: true),
      cc.find_library('avcodec', dirs: dep_lib, required: true),
      cc.find_library('avformat', dirs: dep_lib, required: true),
      cc.find_library('swresample', dirs: dep_lib, required: true),
      cc.find_library('avutil', dirs: dep_lib, required: true),
      cc.find_library('swscale', dirs: dep_lib, required: true),
      dependency('zlib'),
      version_h
    ]
    if obuparse_dep.found()
      deps = [no_as_needed, obuparse_dep, as_needed] + deps
    endif
  endif
else
  lsmash_dep = dependency('liblsmash', required: false)
  if not lsmash_dep.found()
    obuparse_dep = dependency('obuparse', method: 'cmake', modules: ['OBUParse::shared'], required: false)
    lsmash_dep = dependency('lsmash', method: 'cmake', modules: ['LSMASH::shared'])
  else
    obuparse_dep = disabler()
  endif
  deps = [
    lsmash_dep,
    dependency('libavcodec', version: '>=58.91.0'),
    dependency('libavformat', version: '>=58.45.0'),
    dependency('libswresample'),
    dependency('libavutil', version: '>=56.51.0'),
    dependency('libswscale', version: '>=5.7.0'),
    dependency('zlib'),
    version_h
  ]
  if obuparse_dep.found()
    deps = [no_as_needed, obuparse_dep, as_needed] + deps
  endif
endif

if host_machine.cpu_family().startswith('x86')
  add_project_arguments('-mfpmath=sse', '-msse2', language: 'c')
endif

if host_machine.system() == 'windows'
  add_project_arguments('-D__USE_MINGW_ANSI_STDIO', language: 'c')
  if host_machine.cpu_family() == 'x86'
    add_project_arguments('-static-libgcc', language: 'c')
    add_global_link_arguments('-static-libgcc', language: 'c')
    add_global_link_arguments('-Wl,--add-stdcall-alias', language: 'c')
  endif
else
  # needed for POSIX functions like realpath().
  add_project_arguments('-D_DEFAULT_SOURCE', language: 'c')
endif

shared_module('vslsmashsource', sources,
  include_directories: include_directories(vsinclude, '../xxHash', dep_include),
  dependencies: deps,
  install: true,
  install_dir: py.get_install_dir() / 'vapoursynth/plugins',
  name_prefix: '',
  gnu_symbol_visibility: 'hidden'
)
