#!/usr/bin/env python3

from __future__ import annotations

import argparse
from email.generator import Generator
from email.message import Message
import gzip
import importlib.util
from io import BytesIO, StringIO
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


def add_header(message: Message, key: str, value: object | None) -> None:
    if value is not None:
        message[key] = str(value)


def sdist_metadata(pyproject: Path, meta: dict[str, object], version: str) -> bytes:
    project = meta["project"]
    assert isinstance(project, dict)

    message = Message()
    message["Metadata-Version"] = "2.2"
    add_header(message, "Name", project.get("name"))
    add_header(message, "Version", version)
    add_header(message, "Summary", project.get("description"))

    authors = project.get("authors")
    if isinstance(authors, list):
        author_names = [
            author["name"]
            for author in authors
            if isinstance(author, dict) and isinstance(author.get("name"), str)
        ]
        if author_names:
            message["Author"] = ", ".join(author_names)

    license_info = project.get("license")
    if isinstance(license_info, dict):
        add_header(message, "License", license_info.get("text"))
    elif isinstance(license_info, str):
        message["License"] = license_info

    add_header(message, "Requires-Python", project.get("requires-python"))

    classifiers = project.get("classifiers")
    if isinstance(classifiers, list):
        for classifier in classifiers:
            add_header(message, "Classifier", classifier)

    dependencies = project.get("dependencies")
    if isinstance(dependencies, list):
        for dependency in dependencies:
            add_header(message, "Requires-Dist", dependency)

    urls = project.get("urls")
    if isinstance(urls, dict):
        for label, url in urls.items():
            if isinstance(label, str) and isinstance(url, str):
                message["Project-URL"] = f"{label}, {url}"

    readme = project.get("readme")
    if isinstance(readme, str):
        readme_path = pyproject.parent / readme
        if readme_path.suffix.lower() == ".md":
            message["Description-Content-Type"] = "text/markdown"
        message.set_payload(readme_path.read_text(encoding="utf-8"))

    output = StringIO()
    Generator(output, maxheaderlen=0).flatten(message)
    return output.getvalue().encode("utf-8")


def add_bytes(tar: tarfile.TarFile, arcname: Path, data: bytes) -> None:
    info = tarfile.TarInfo(os.fspath(arcname))
    info.size = len(data)
    info.mtime = 0
    info.mode = 0o644
    with BytesIO(data) as stream:
        tar.addfile(info, stream)


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
    pkg_info = sdist_metadata(pyproject, meta, version)
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
                add_bytes(tar, Path(archive_stem) / "PKG-INFO", pkg_info)
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
