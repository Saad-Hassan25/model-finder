#!/usr/bin/env python3
"""Exercise the packed npx installer in temporary homes; optionally fetch public data.

No login, account credentials, inference, or real client configuration is used.
Raw catalogs and transcripts belong under the ignored .model-finder directory.
"""

from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[1]


def npm_commands():
    node = shutil.which("node")
    if not node:
        raise RuntimeError("Node.js 22+ is required.")
    # Calling the JS entrypoints avoids shell interpretation of Windows .cmd files.
    npm_bin = Path(node).resolve().parent / "node_modules" / "npm" / "bin"
    if (npm_bin / "npm-cli.js").is_file():
        return [node, str(npm_bin / "npm-cli.js")], [node, str(npm_bin / "npx-cli.js")]
    npm, npx = shutil.which("npm"), shutil.which("npx")
    if os.name == "nt" or not npm or not npx:
        raise RuntimeError("Cannot locate npm/npx JS entrypoints; use a standard Node install.")
    return [npm], [npx]


def isolated_env(home):
    allowed = {"PATH", "SYSTEMROOT", "WINDIR", "COMSPEC", "PATHEXT", "TEMP", "TMP",
               "LANG", "LC_ALL", "SSL_CERT_FILE", "SSL_CERT_DIR"}
    env = {key: value for key, value in os.environ.items() if key.upper() in allowed}
    locations = {"HOME": home, "USERPROFILE": home, "CODEX_HOME": home / ".codex",
                 "CLAUDE_CONFIG_DIR": home / ".claude", "APPDATA": home / "AppData/Roaming",
                 "LOCALAPPDATA": home / "AppData/Local", "XDG_CONFIG_HOME": home / ".config",
                 "XDG_DATA_HOME": home / ".local/share", "XDG_CACHE_HOME": home / ".cache",
                 "npm_config_cache": home / ".npm", "npm_config_userconfig": home / ".npmrc",
                 "npm_config_globalconfig": home / "global.npmrc"}
    env.update({key: str(value) for key, value in locations.items()})
    env.update({"npm_config_audit": "false", "npm_config_fund": "false",
                "npm_config_ignore_scripts": "true", "NO_COLOR": "1"})
    return env


def execute(command, cwd, env):
    result = subprocess.run(command, cwd=cwd, env=env, capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=180)
    if result.returncode:
        # Commands have no secrets; avoid dumping arbitrary process errors anyway.
        raise RuntimeError(f"Command failed (exit {result.returncode}): {command[0]}")
    return result.stdout


def run(output, live=False):
    output.mkdir(parents=True, exist_ok=True)
    npm, npx = npm_commands()
    transcript = ["MODEL FINDER 0.1.0 | clean-room launch check", ""]
    report = {"checked_at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "source": "local npm tarball (not GitHub transport)", "clients": [],
              "inference_run": False, "oauth_completed": False}
    with tempfile.TemporaryDirectory(prefix="model-finder-launch-") as directory:
        sandbox = Path(directory)
        pack_home = sandbox / "pack-home"
        pack_home.mkdir()
        packed = json.loads(execute(npm + ["pack", "--ignore-scripts", "--json",
                                             "--pack-destination", str(sandbox)],
                                    ROOT, isolated_env(pack_home)))[0]
        archive = sandbox / packed["filename"]
        for client in ("claude-code", "codex", "opencode"):
            home, project = sandbox / client / "home", sandbox / client / "project with spaces"
            home.mkdir(parents=True)
            project.mkdir()
            env = isolated_env(home)
            args = ["--yes", "--package", str(archive), "--", "model-finder-install",
                    "--agent", client, "--scope", "project", "--project-dir", str(project),
                    "--connections", "both", "--yes", "--json"]
            stdout = execute(npx + args, project, env)
            result = json.loads(stdout)
            assert result["ok"] and len(result["skills"]) == 1
            skill = Path(result["skills"][0]["path"])
            assert skill.is_relative_to(project) and (skill / "SKILL.md").is_file()
            assert all(Path(item["path"]).is_relative_to(project) for item in result["configs"])
            assert len(result["authentication"]) == 2
            assert all(item["state"] == "pending" for item in result["authentication"])
            offline = json.loads(execute([sys.executable, str(skill / "scripts/model_finder.py"),
                                           "shortlist", "--catalog", str(ROOT / "examples/catalog.example.json"),
                                           "--benchmarks", str(ROOT / "examples/benchmarks.example.json"),
                                           "--objective", "value"], project, env))
            assert [item["id"] for item in offline["candidates"]] == [
                "example/budget", "example/balanced", "example/premium"]
            report["clients"].append({"client": client, "npx_install": "passed",
                                      "offline_helper": "passed", "oauth": "pending",
                                      "authentication_commands": [item["command"] + " " + " ".join(item["args"])
                                                                  for item in result["authentication"]]})
            transcript += [f"$ npx --yes --package <local tarball> -- model-finder-install --agent {client}",
                           "  --scope project --connections both --yes --json",
                           "PASS  skill installed; MCP config written in temporary project",
                           "PASS  offline helper: example/budget, example/balanced, example/premium",
                           "PENDING  OAuth; no browser launched and no credentials used", ""]
        if live:
            catalog_path = output.resolve() / "catalog.json"
            helper = skill / "scripts/model_finder.py"
            execute([sys.executable, str(helper), "fetch", "--output", str(catalog_path)], project, env)
            args = [sys.executable, str(helper), "shortlist", "--catalog", str(catalog_path),
                    "--require", "structured_outputs", "--require", "tools", "--input-modality", "text",
                    "--min-context", "131072", "--input-tokens", "10000", "--output-tokens", "1500",
                    "--requests-per-month", "1000", "--exclude-free", "--exclude-aliases", "--limit", "3"]
            live_result = json.loads(execute(args, project, env))
            (output / "shortlist.json").write_text(json.dumps(live_result, indent=2) + "\n", encoding="utf-8")
            report["live_catalog"] = {**live_result["catalog"], "counts": live_result["counts"]}
            transcript += ["$ python <installed skill>/scripts/model_finder.py fetch", "PASS  public OpenRouter catalog fetched without an account",
                           f"Fetched: {live_result['catalog']['retrieved_at']}",
                           "$ python <installed skill>/scripts/model_finder.py shortlist <constraints>",
                           "PRICE-ONLY top 3 | 10,000 input + 1,500 output | 1,000 chunks/month"]
            for item in live_result["candidates"]:
                transcript.append(f"{item['id']}: ${item['input_usd_per_million']}/M in, "
                                  f"${item['output_usd_per_million']}/M out; ${item['estimated_monthly_usd']}/month")
            transcript += ["Task accuracy and provider route unverified. No inference run."]
    (output / "check.json").write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8")
    (output / "transcript.txt").write_text("\n".join(transcript) + "\n", encoding="utf-8")
    print("\n".join(transcript))
    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=ROOT / ".model-finder/launch")
    parser.add_argument("--live", action="store_true", help="Also GET the public OpenRouter catalog.")
    options = parser.parse_args()
    run(options.output_dir, options.live)
