#!/usr/bin/env python3
"""Build a portable plugin ZIP from an explicit allowlist, excluding local source data."""

from pathlib import Path
import sys
from zipfile import ZIP_DEFLATED, ZipFile

ROOT = Path(__file__).resolve().parents[1]
INCLUDE = (".claude-plugin", ".codex-plugin", ".agents/plugins", ".mcp.json", "skills", "scripts", "assets/brand", "install.ps1", "install.sh", "README.md", "LICENSE", "docs", "examples")


def build(output=None):
    output = Path(output) if output else ROOT / "dist" / "model-finder.zip"
    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as archive:
        for entry in INCLUDE:
            path = ROOT / entry
            files = sorted(path.rglob("*")) if path.is_dir() else [path]
            for file in files:
                if file.is_file() and "__pycache__" not in file.parts and file.suffix != ".pyc":
                    archive.write(file, file.relative_to(ROOT).as_posix())
    return output


if __name__ == "__main__":
    print(build(sys.argv[1] if len(sys.argv) > 1 else None))
