#!/usr/bin/env python3
from __future__ import annotations

import argparse
import base64
import csv
import hashlib
import importlib.util
import pathlib
import tomllib
import zipfile


def wheel_dist_name(name: str) -> str:
    return name.replace("-", "_")


def metadata_name(name: str) -> str:
    return name.replace("-", "_")


def hash_bytes(data: bytes) -> str:
    digest = hashlib.sha256(data).digest()
    return "sha256=" + base64.urlsafe_b64encode(digest).rstrip(b"=").decode("ascii")


def build_metadata(pyproject: dict, version: str) -> str:
    project = pyproject["project"]
    lines = [
        "Metadata-Version: 2.1",
        f"Name: {project['name']}",
        f"Version: {version}",
        f"Summary: {project['description']}",
        f"Requires-Python: {project['requires-python']}",
    ]
    license_info = project.get("license")
    if isinstance(license_info, dict) and "text" in license_info:
        lines.append(f"License: {license_info['text']}")
    for dep in project.get("dependencies", []):
        lines.append(f"Requires-Dist: {dep}")
    return "\n".join(lines) + "\n"


def load_version(pyproject_path: pathlib.Path) -> str:
    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    version = pyproject["project"].get("version")
    if version:
        return version

    version_py = pyproject_path.parent / "ci" / "version.py"
    spec = importlib.util.spec_from_file_location("lsmas_version", version_py)
    module = importlib.util.module_from_spec(spec)
    assert spec.loader is not None
    spec.loader.exec_module(module)
    return module.pep440_version(pyproject_path.parent.parent)


def build_wheel_file(tag: str) -> str:
    return "\n".join(
        [
            "Wheel-Version: 1.0",
            "Generator: lsmas-cross-wheel",
            "Root-Is-Purelib: false",
            f"Tag: py3-none-{tag}",
            "",
        ]
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dll", required=True)
    parser.add_argument("--out-dir", required=True)
    parser.add_argument("--tag", default="win_amd64")
    parser.add_argument("--pyproject", default="pyproject.toml")
    args = parser.parse_args()

    dll_path = pathlib.Path(args.dll)
    out_dir = pathlib.Path(args.out_dir)
    pyproject_path = pathlib.Path(args.pyproject)

    pyproject = tomllib.loads(pyproject_path.read_text(encoding="utf-8"))
    project = pyproject["project"]
    dist = wheel_dist_name(project["name"])
    metadata_dist = metadata_name(project["name"])
    version = load_version(pyproject_path)
    dist_info = f"{metadata_dist}-{version}.dist-info"
    wheel_name = f"{dist}-{version}-py3-none-{args.tag}.whl"
    wheel_path = out_dir / wheel_name

    dll_bytes = dll_path.read_bytes()
    metadata_bytes = build_metadata(pyproject, version).encode("utf-8")
    wheel_bytes = build_wheel_file(args.tag).encode("utf-8")

    files = {
        "vapoursynth/plugins/vslsmashsource.dll": dll_bytes,
        f"{dist_info}/METADATA": metadata_bytes,
        f"{dist_info}/WHEEL": wheel_bytes,
    }

    out_dir.mkdir(parents=True, exist_ok=True)
    records: list[tuple[str, str, str]] = []
    with zipfile.ZipFile(wheel_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        for path, data in files.items():
            zf.writestr(path, data)
            records.append((path, hash_bytes(data), str(len(data))))

        record_path = f"{dist_info}/RECORD"
        record_rows = records + [(record_path, "", "")]
        record_data = "".join(",".join(row) + "\n" for row in record_rows).encode("utf-8")
        zf.writestr(record_path, record_data)


if __name__ == "__main__":
    main()
