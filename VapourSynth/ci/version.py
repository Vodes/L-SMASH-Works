#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


DESCRIBE_RE = re.compile(
    r"^(?P<tag>.+)-(?P<distance>\d+)-g(?P<sha>[0-9a-f]+)(?P<dirty>-dirty)?$"
)


def normalize_tag(tag: str) -> str | None:
    if tag.startswith("v"):
        tag = tag[1:]

    if re.fullmatch(r"\d+\.\d+\.\d+\.\d+", tag):
        parts = tag.split(".")
        if parts[3] == "0":
            return ".".join(parts[:3])
        return tag

    if re.fullmatch(r"\d+\.\d+\.\d+", tag):
        return tag

    if re.fullmatch(r"\d+", tag):
        if len(tag) == 8 and tag.startswith(("19", "20")):
            return None
        return f"{int(tag)}.0.0"

    return None


def pep440_version(repo_root: Path) -> str:
    describe_out = subprocess.run(
        ["git", "-C", str(repo_root), "describe", "--tags", "--long", "--dirty", "--always"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()

    match = DESCRIBE_RE.fullmatch(describe_out)
    if not match:
        sha = describe_out.removeprefix("g")
        return f"0.0.0.dev0+g{sha}"

    tag = match.group("tag")
    distance = int(match.group("distance"))
    sha = match.group("sha")
    dirty = bool(match.group("dirty"))

    base = normalize_tag(tag)
    if base is None:
        return f"0.0.0.dev{distance}+g{sha}"

    version = base
    if distance:
        version += f".dev{distance}+g{sha}"
    elif dirty:
        version += f"+g{sha}.dirty"
    return version


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("repo_root", nargs="?", default=None)
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    repo_root = Path(args.repo_root).resolve() if args.repo_root else Path(__file__).resolve().parents[2]
    print(pep440_version(repo_root))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
