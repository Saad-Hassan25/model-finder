# Install Model Finder

## One command

Run in your VS Code terminal, another terminal, or the project where you want the skill:

```bash
npx --yes github:Saad-Hassan25/Model-Selector
```

You need Node.js 22+ (includes `npx`) and Git for the GitHub package source. The command downloads the installer for you. No manual clone, Python setup, or npm publication is required.

The wizard asks for:

1. Claude Code, Codex, OpenCode, or several clients.
2. This project or all projects for your user.
3. OpenRouter, OpenRouter plus Artificial Analysis, or skill only.
4. Whether to start browser sign-in now.

It shows the destination paths before installing, copies the complete skill, and merges the selected MCP connections. After login, start a new client session. Project-scoped connections may require that client's workspace trust or MCP approval.

## For coding agents

When a user gives you this repository and asks you to install it:

- Use the host client named by the user or established by your environment. Supported names are `claude-code`, `codex`, and `opencode`.
- Default to the current project when the user has not requested a global installation. Resolve the user's project path before running. Do not use the downloaded npm package directory as the project.
- Use explicit flags and JSON mode. An installation request permits the selected skill and MCP setup; it does not authorize paid inference, credential disclosure, or unrelated config changes.

For Codex in the current project:

```bash
npx --yes github:Saad-Hassan25/Model-Selector --agent codex --scope project --yes --json
```

For Claude Code across projects, when requested:

```bash
npx --yes github:Saad-Hassan25/Model-Selector --agent claude-code --scope global --yes --json
```

Use `--project-dir /absolute/path/to/project` if the terminal is elsewhere. Use `--agent claude-code,codex` for several clients. `--connections both` includes Artificial Analysis; `--connections none` installs only the skill. `--dry-run` returns the plan without changing files. `--replace` backs up and upgrades an existing different skill when the user has requested that upgrade.

JSON mode never prompts or opens a browser. Read the `ok` field and exit code. Report the installed paths and any pending `authentication` entries; each contains a command, argument array, and working directory. Hand OAuth approval to the user through the client's UI or the returned login command. Do not report pending authentication as completed. Errors report `completed` paths if an unexpected filesystem error interrupted an installation.

## Flags

| Flag | Meaning |
| --- | --- |
| `--agent NAME` | `claude-code` (`claude` alias), `codex`, `opencode`, or `all`; repeat or use commas |
| `--scope project` | Install skill and MCP settings in the current/selected project |
| `--scope global` or `-g` | Install for all projects under the current user |
| `--project-dir PATH` | Existing target project directory; project scope only |
| `--connections openrouter` | OpenRouter only; default in non-interactive mode |
| `--connections both` | OpenRouter plus Artificial Analysis |
| `--connections none` | Skill only; no config changes or authentication |
| `--login` | Run client-native sign-in after installing; cannot be combined with JSON mode |
| `--no-login` | Leave sign-in for later; default with `--yes`/`--json` |
| `--yes` / `-y` | Skip prompts; requires explicit client and scope |
| `--json` | Machine-readable result; also requires explicit client and scope |
| `--dry-run` | Plan only, no writes or login |
| `--replace` | Back up a differing skill directory before upgrading |

The first `--yes` before the GitHub address belongs to `npx`. Flags after the address belong to Model Finder.

## Files and existing settings

| Client | This project | All projects |
| --- | --- | --- |
| Claude skill | `.claude/skills/model-finder/` | `~/.claude/skills/model-finder/` |
| Claude MCP | `.mcp.json` | `~/.claude.json` |
| Codex skill | `.agents/skills/model-finder/` | `~/.agents/skills/model-finder/` |
| Codex MCP | `.codex/config.toml` | `~/.codex/config.toml` |
| OpenCode skill | `.opencode/skills/model-finder/` | `~/.config/opencode/skills/model-finder/` |
| OpenCode MCP | `opencode.json` or existing `opencode.jsonc` | `~/.config/opencode/opencode.json` or existing `.jsonc` |

The installer honors `XDG_CONFIG_HOME`, `CODEX_HOME`, and `CLAUDE_CONFIG_DIR` when reading their configured locations. OpenCode reuses a selected/identical Claude or shared skill copy when possible; it does not assume a custom Claude account directory is discoverable by OpenCode.

Existing source connections are reused if they match. Conflicting or disabled entries stop setup during preflight. JSONC comments and unrelated JSON/TOML settings are preserved; unsupported TOML layouts are left untouched. Changed config files and explicitly replaced skills receive sibling `.model-finder-backup-…` backups. Keep private config backups out of version control.

Rerunning the same installation is safe: identical copies/settings are reused. To upgrade a differing copy, rerun with `--replace`; the old directory is retained. To remove the skill, remove its installed directory; remove MCP entries through the client if no longer needed.

## Other installation tools

For broader Agent Skills clients, use the ecosystem CLI:

```bash
npx skills add Saad-Hassan25/Model-Selector --skill model-finder
```

That tool installs the skill and manages its own prompts/flags. It does not run Model Finder's MCP setup wizard. See [Skills CLI documentation](https://skills.sh/docs/cli) and the repository's [manual MCP setup](docs/setup.md#connect-research-data) when using that route.

Native [Claude](docs/setup.md#claude-code-plugin) and [Codex](docs/setup.md#codex-plugin) plugins remain alternatives. Choose one route per client to avoid duplicate skill entries.
