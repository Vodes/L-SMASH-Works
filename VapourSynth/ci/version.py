#!/usr/bin/env python3

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


DESCRIBE_RE = re.compile(
    r"^(?P<tag>.+)-(?P<distance>\d+)-g(?P<sha>[0-9a-f]+)(?P<dirty>-dirty)?$"
)
TAG_RE = re.compile(
    r"^(?P<release>\d+(?:\.\d+){0,3})(?:(?:\.|-)?(?P<phase>a|b|rc|dev|post)(?P<phase_num>\d+))?$"
)


def normalize_tag(tag: str) -> str | None:
    if tag.startswith("v"):
        tag = tag[1:]

    match = TAG_RE.fullmatch(tag)
    if match is None:
        if re.fullmatch(r"\d{8}", tag) and tag.startswith(("19", "20")):
            return None
        if re.fullmatch(r"\d+", tag):
            return f"{int(tag)}.0.0"
        return None

    parts = match.group("release").split(".")
    if len(parts) == 4 and parts[3] == "0":
        parts = parts[:3]
    elif len(parts) == 1:
        parts.extend(["0", "0"])

    version = ".".join(parts)
    phase = match.group("phase")
    phase_num = match.group("phase_num")
    if phase is None:
        return version
    if phase == "dev":
        return f"{version}.dev{phase_num}"
    return f"{version}.{phase}{phase_num}"


def version_from_describe(describe_out: str) -> str:
    def local_suffix(sha: str, dirty: bool) -> str:
        suffix = f"+g{sha}"
        if dirty:
            suffix += ".dirty"
        return suffix

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
        return f"0.0.0.dev{distance}{local_suffix(sha, dirty)}"

    version = base
    if distance:
        if re.search(r"\.dev\d+$", base):
            version += local_suffix(sha, dirty)
        else:
            version += f".dev{distance}{local_suffix(sha, dirty)}"
    elif dirty:
        version += local_suffix(sha, dirty)
    return version


def pep440_version(repo_root: Path) -> str:
    describe_out = subprocess.run(
        ["git", "-C", str(repo_root), "describe", "--tags", "--long", "--dirty", "--always"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    return version_from_describe(describe_out)


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
