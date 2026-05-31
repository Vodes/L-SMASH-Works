#!/usr/bin/env python3

from __future__ import annotations

import argparse
import gzip
import importlib.util
import os
import subprocess
import tarfile
from pathlib import Path
import tomllib


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out-dir", default="dist")
    parser.add_argument("--repo-root", default=None)
    parser.add_argument("--pyproject", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    script_path = Path(__file__).resolve()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else script_path.parents[2]
    pyproject = Path(args.pyproject).resolve() if args.pyproject else repo_root / "VapourSynth" / "pyproject.toml"
    meta = tomllib.loads(pyproject.read_text())
    project_name = meta["project"]["name"].replace("-", "_")
    version_py = script_path.parent / "version.py"
    spec = importlib.util.spec_from_file_location("lsmas_version", version_py)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    version = module.pep440_version(repo_root)
    archive_stem = f"{project_name}-{version}"
    out_dir = Path(args.out_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    archive_path = out_dir / f"{archive_stem}.tar.gz"

    tracked = subprocess.run(
        ["git", "-C", os.fspath(repo_root), "ls-files", "--recurse-submodules", "-z"],
        check=True,
        capture_output=True,
    ).stdout.split(b"\0")

    with archive_path.open("wb") as raw:
        with gzip.GzipFile(filename="", mode="wb", fileobj=raw, mtime=0) as gz:
            with tarfile.open(fileobj=gz, mode="w") as tar:
                for entry in tracked:
                    if not entry:
                        continue
                    relpath = Path(entry.decode())
                    src = repo_root / relpath
                    if not src.exists():
                        continue
                    tar.add(src, arcname=Path(archive_stem) / relpath, recursive=False)

    print(archive_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
