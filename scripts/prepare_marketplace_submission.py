"""Create a reviewable, self-contained Dify Marketplace submission directory.

Run after CI has built the official .difypkg installer. Deliberately copies
only allowlisted runtime/source/docs files: never entire developer workspaces.
"""
from __future__ import annotations

import argparse
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
ORGANIZATION = "ahamdjin"
PLUGIN = "agent_safety_toolkit"
FILES = (
    "manifest.yaml",
    "README.md",
    "PRIVACY.md",
    "LICENSE",
    "requirements.txt",
    "pyproject.toml",
    "main.py",
    "agent_safety.py",
    "_assets/icon.svg",
    "provider/agent_safety_toolkit.yaml",
    "provider/agent_safety_toolkit.py",
    "tools/compact_json.yaml",
    "tools/compact_json.py",
    "tools/redact_text.yaml",
    "tools/redact_text.py",
)


def stage_package(package_path: Path, output_root: Path) -> Path:
    package_path = package_path.resolve()
    output_root = output_root.resolve()
    if not package_path.is_file() or package_path.suffix != ".difypkg":
        raise ValueError("Expected an existing .difypkg installer built by the official Dify CLI")
    if package_path.name != "agent_safety_toolkit-0.1.0.difypkg":
        raise ValueError("Installer name must match the v0.1.0 plugin manifest")

    target = output_root / ORGANIZATION / PLUGIN
    if target.exists():
        shutil.rmtree(target)
    target.mkdir(parents=True, exist_ok=True)

    for relative in FILES:
        src = ROOT / relative
        if not src.is_file() or src.is_symlink():
            raise ValueError(f"Missing or symlinked reviewed source: {relative}")
        dest = target / relative
        dest.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest)

    shutil.copy2(package_path, target / package_path.name)
    produced = sorted(str(p.relative_to(target)) for p in target.rglob("*") if p.is_file())
    expected = sorted((*FILES, package_path.name))
    if produced != expected:
        raise ValueError("Unexpected staged files; refusing marketplace bundle")
    return target


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, default=ROOT / "agent_safety_toolkit-0.1.0.difypkg")
    parser.add_argument("--output", type=Path, default=ROOT / "marketplace-submission")
    args = parser.parse_args()
    location = stage_package(args.package, args.output)
    print(f"Prepared exact Marketplace directory: {location}")
    print(f"Included {len(FILES)} source files plus one official .difypkg installer.")
