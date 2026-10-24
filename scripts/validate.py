#!/usr/bin/env python3
"""Validate distributable structure, local references, and synchronized versions offline."""

import ast
import json
from pathlib import Path
import re
import sys
from urllib.parse import unquote

ROOT = Path(__file__).resolve().parents[1]


def validate(root=ROOT):
    errors = []
    manifests = []
    for name in (".claude-plugin/plugin.json", ".codex-plugin/plugin.json", ".claude-plugin/marketplace.json", ".mcp.json"):
        try:
            manifests.append(json.loads((root / name).read_text(encoding="utf-8")))
        except (OSError, ValueError):
            errors.append(f"Missing or invalid JSON: {name}")
    if errors:
        return errors
    claude, codex, marketplace, mcp = manifests
    try:
        native = json.loads((root / ".agents/plugins/marketplace.json").read_text(encoding="utf-8"))
        native_entry = native["plugins"][0]
        if native["name"] != marketplace["name"] or native_entry["name"] != "model-finder" or native_entry["source"] != {"source": "local", "path": "./"}:
            errors.append("Native Codex marketplace must reference the root plugin.")
    except (OSError, ValueError, KeyError, IndexError, TypeError):
        errors.append("Missing or invalid native Codex marketplace.")
    for manifest in (claude, codex):
        if manifest.get("name") != "model-finder":
            errors.append("Plugin names must match the model-finder skill.")
    try:
        versions = [claude["version"], codex["version"], marketplace["plugins"][0]["version"]]
        package = json.loads((root / "package.json").read_text(encoding="utf-8"))
        versions.append(package["version"])
        if package.get("bin") != {"model-finder-install": "bin/install.mjs"} or not (root / "bin/install.mjs").is_file():
            errors.append("The npm package must expose the guided installer.")
        tree = ast.parse((root / "skills/model-finder/scripts/model_finder.py").read_text(encoding="utf-8"))
        versions.extend(ast.literal_eval(node.value) for node in tree.body if isinstance(node, ast.Assign)
                        and any(isinstance(t, ast.Name) and t.id == "VERSION" for t in node.targets))
        if len(versions) != 5 or len(set(versions)) != 1:
            errors.append("Helper, plugin, and marketplace versions must agree.")
        if not all(re.fullmatch(r"\d+\.\d+\.\d+", version) for version in versions):
            errors.append("Versions must use major.minor.patch.")
    except (KeyError, IndexError, OSError, SyntaxError, ValueError, TypeError):
        errors.append("Cannot validate package versions.")
    for key in ("skills", "mcpServers"):
        value = codex.get(key, "")
        if not isinstance(value, str) or not value.startswith("./") or ".." in Path(value).parts or not (root / value).exists():
            errors.append(f"Codex {key} must resolve within the plugin.")
    expected = {
        "openrouter": "https://mcp.openrouter.ai/mcp",
        "artificial-analysis": "https://mcp.artificialanalysis.ai/mcp",
    }
    if set(mcp.get("mcpServers", {})) != set(expected):
        errors.append("MCP server set differs from the documented research sources.")
    for name, url in expected.items():
        entry = mcp.get("mcpServers", {}).get(name, {})
        if entry != {"type": "http", "url": url}:
            errors.append(f"Unexpected MCP configuration for {name}.")
    try:
        skill = (root / "skills/model-finder/SKILL.md").read_text(encoding="utf-8")
        frontmatter = skill.split("---", 2)[1] if skill.startswith("---\n") else ""
        if not re.search(r"^name: model-finder$", frontmatter, re.M):
            errors.append("Skill frontmatter must name model-finder.")
        if not re.search(r"^description: .+", frontmatter, re.M):
            errors.append("Skill description is missing.")
    except (OSError, IndexError):
        errors.append("Skill entrypoint missing or invalid.")
    try:
        if (root / "LICENSE").read_bytes() != (root / "skills/model-finder/LICENSE").read_bytes():
            errors.append("Installed skill must carry the repository's MIT license.")
    except OSError:
        errors.append("Repository or skill license missing.")
    paths = [root / "README.md", root / "CONTRIBUTING.md", root / "INSTALL.md", root / "AGENTS.md"]
    for folder in ("skills", "docs"):
        paths.extend((root / folder).rglob("*.md"))
    for path in paths:
        try:
            content = path.read_text(encoding="utf-8")
        except OSError:
            errors.append(f"Missing documentation: {path.relative_to(root)}")
            continue
        for target in re.findall(r"\[[^\]]+\]\(([^)]+)\)", content):
            if re.match(r"[a-z]+:", target) or target.startswith("#"):
                continue
            relative = unquote(target.split("#", 1)[0])
            resolved = (path.parent / relative).resolve()
            if not resolved.is_relative_to(root.resolve()) or not resolved.exists():
                errors.append(f"Broken local reference in {path.relative_to(root)}: {target}")
    return errors


if __name__ == "__main__":
    failures = validate()
    if failures:
        for failure in failures:
            print(f"ERROR: {failure}", file=sys.stderr)
        raise SystemExit(1)
    print("Validated plugin manifests, versions, skill entrypoint, and local documentation references.")
