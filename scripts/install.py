#!/usr/bin/env python3
"""Install the complete skill without modifying MCP settings or replacing existing files."""

import argparse
import os
from pathlib import Path
import shutil
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "skills" / "model-finder"


def destination(target, scope, home, project):
    if scope == "project":
        return project / {"claude": ".claude", "codex": ".agents", "opencode": ".opencode"}[target] / "skills" / "model-finder"
    if target == "opencode":
        config = Path(os.environ.get("XDG_CONFIG_HOME") or home / ".config")
        return config / "opencode" / "skills" / "model-finder"
    return home / {"claude": ".claude", "codex": ".agents"}[target] / "skills" / "model-finder"


def install(source, target, dry_run=False):
    if not (source / "SKILL.md").is_file():
        raise ValueError("Source skill is missing; use a complete checkout or release archive.")
    if target.exists() or target.is_symlink():
        raise ValueError(f"Already exists; left unchanged: {target}. Move the old folder aside before upgrading.")
    if dry_run:
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    # Stage on the same volume; interruption during copy cannot expose a partial skill.
    with tempfile.TemporaryDirectory(prefix=".model-finder-install-", dir=target.parent) as stage:
        staged = Path(stage) / "model-finder"
        shutil.copytree(source, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc"))
        if target.exists() or target.is_symlink():
            raise ValueError(f"Destination appeared during installation; left unchanged: {target}")
        staged.rename(target)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--target", choices=("claude", "codex", "opencode"), required=True)
    parser.add_argument("--scope", choices=("user", "project"), default="user")
    parser.add_argument("--project-dir", type=Path, help="Required for --scope project.")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.scope == "project" and args.project_dir is None:
        parser.error("--scope project requires --project-dir")
    if args.scope == "user" and args.project_dir is not None:
        parser.error("--project-dir requires --scope project")
    project = args.project_dir.resolve() if args.project_dir else Path.cwd()
    if args.scope == "project" and not project.is_dir():
        parser.error("--project-dir must be an existing directory")
    target = destination(args.target, args.scope, Path.home(), project)
    try:
        install(SOURCE, target, args.dry_run)
    except (ValueError, OSError) as exc:
        print(f"install: {exc}", file=sys.stderr)
        return 1
    print(f"{'Would install' if args.dry_run else 'Installed'}: {target}")
    print("Next: connect the research sources in docs/setup.md. MCP settings were not changed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
