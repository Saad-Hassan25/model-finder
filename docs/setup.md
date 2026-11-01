# Setup

## Guided installation

Run from your terminal in any directory:

```bash
npx --yes github:Saad-Hassan25/model-finder
```

Choose your clients, project/all-project scope, data connections, and whether to sign in. The installer handles skill files and MCP configuration together. Node.js 22+ and Git are required; Python is only needed for the optional research helper.

For non-interactive installation, upgrades, paths, and JSON results, see [INSTALL.md](../INSTALL.md). The sections below describe alternative/manual routes and how to manage individual connections after installation.

Documentation and installed CLI syntax were checked on **2026-11-01**. See the [release verification record](release.md) for client versions, clean-room install results and the distinction between documented OAuth steps and completed sign-in. A successful install can still require workspace trust and provider consent.

In a fresh Claude Code project, `claude mcp get openrouter` can show **Pending approval (run `claude` to approve)**. Approve the project connection in Claude before signing in. Codex project settings require workspace trust; after trusting the project, `codex mcp get openrouter` should show the configured HTTP URL. These states are separate from successful OAuth.

## Pick an installation route

| Client | Skill-only location (user scope) | Invocation |
| --- | --- | --- |
| Claude Code | `~/.claude/skills/model-finder/` | `/model-finder` |
| Codex | `~/.agents/skills/model-finder/` | `$model-finder`, or natural language |
| OpenCode | `~/.config/opencode/skills/model-finder/` | Ask it to load `model-finder` |

OpenCode also discovers `.agents/skills` and `.claude/skills`. If you already installed there for another client, OpenCode can reuse that copy; avoid an extra copy with the same skill name. Its native user directory honors `XDG_CONFIG_HOME` in the installer. Agent Skills clients beyond these three can use the same directory if they support the format.

### Legacy Python copy helper

Python 3.10+; no pip packages. Run from the checkout or extracted release:

```bash
python scripts/install.py --target codex --dry-run
python scripts/install.py --target codex
```

Replace `codex` with `claude` or `opencode`. For project scope, specify an existing target project:

```bash
python scripts/install.py --target claude --scope project --project-dir /path/to/project
```

On Windows, a quoted path such as `"D:\Work\My App"` works. Wrappers `install.ps1` and `install.sh` accept the same arguments. All scripts resolve bundled resources relative to their own location, so you can run them from another working directory.

This Python copy helper stages the entire skill then renames it into place. It does not overwrite, authenticate, install dependencies, or edit client configuration. For upgrades, move the old `model-finder` directory aside and run the helper again. For removal, remove that installed directory. MCP connections are independent and remain until removed with the client's settings or MCP commands. The guided npx installer above also handles MCP setup and backed-up upgrades.

### Manual installation (no Python)

Copy the complete `skills/model-finder` directory to the appropriate location in the table. Keep `SKILL.md`, `references/`, `scripts/`, and `agents/` together. Python is needed only if the agent uses the optional helper.

Project equivalents are `.claude/skills/model-finder`, `.agents/skills/model-finder`, and `.opencode/skills/model-finder` under the target project. Restart/reload the client if its skill list does not refresh.

### Claude Code plugin

The checkout root is a Claude plugin. For one local session, start:

```bash
claude --plugin-dir .
```

For persistent installation, inside Claude Code:

```text
/plugin marketplace add /absolute/path/to/model-finder
/plugin install model-finder@model-finder-marketplace
```

Use the absolute path of this checkout/extracted archive. On Windows, quote paths containing spaces as supported by the client UI. After you publish the repository, the same marketplace can be added using your actual `owner/repository`; there is no hard-coded GitHub account in the manifests.

The plugin command is namespaced: `/model-finder:model-finder`. The standalone copied skill uses `/model-finder`. The plugin bundles both remote MCP entries in `.mcp.json`; authenticate through the client's `/mcp` panel. Do not add duplicate manual connections for a plugin already exposing these tools.

Validate locally with `claude plugin validate .`. Plugin installation is separate from repository generation; this project does not install itself into your current client.

### Codex plugin

The root includes a `.codex-plugin/plugin.json` compatibility manifest declaring `./skills/` and `./.mcp.json`, and a native marketplace at `.agents/plugins/marketplace.json` pointing at the plugin root. With a recent Codex CLI, from the checkout:

```bash
codex plugin marketplace add .
codex plugin add model-finder@model-finder-marketplace
```

These subcommands are present in the locally checked Codex CLI 0.141.0. Client support varies; check `codex plugin --help` in your version. Supported desktop clients also expose local marketplace plugins in their plugin directory. Authenticate the bundled research sources through that client's connection UI. The copied skill plus `codex mcp add` remains a fallback for versions without plugin support.

`python scripts/package.py` produces `dist/model-finder.zip`. Extract it to use the same local marketplace commands, or use a compatible client import UI. A GitHub repository and this local marketplace do not automatically publish the plugin to a public directory.

## Connect research data

For **skill-only installations**, configure the integrations below. The plugin already bundles their URLs. The legacy Python helper does not configure these connections; the guided npx installer can add them and launch the client's OAuth flow.

### OpenRouter

Claude Code, user scope:

```bash
claude mcp add --transport http --scope user openrouter https://mcp.openrouter.ai/mcp
claude mcp login openrouter
```

Codex:

```bash
codex mcp add openrouter --url https://mcp.openrouter.ai/mcp
codex mcp login openrouter
```

OAuth runs in a browser. Review the provider's displayed permissions and limits. The server exposes read-only research tools and inference tools; the skill uses research tools by default. A research request does not authorize `send-message` inference.

If an older Claude release lacks `mcp login`, start Claude Code and use `/mcp` to authenticate, following the [official MCP guide](https://code.claude.com/docs/en/mcp). No private API key is required for the helper's public OpenRouter catalog fallback.

### Artificial Analysis (optional independent connection)

OpenRouter's MCP benchmark tools may already supply the relevant AA evidence. Add a separate connection for independent cross-checks and additional accessible metrics:

```bash
# Claude Code, user scope
claude mcp add --transport http --scope user artificial-analysis https://mcp.artificialanalysis.ai/mcp
claude mcp login artificial-analysis

# Codex
codex mcp add artificial-analysis --url https://mcp.artificialanalysis.ai/mcp
codex mcp login artificial-analysis
```

AA supports OAuth and API-key access. Coverage, quotas, and detailed evaluation access depend on the plan. See [AA MCP authentication](https://artificialanalysis.ai/data-api/docs/mcp) and [data API documentation](https://artificialanalysis.ai/data-api/docs). The helper's REST fallback reads `AA_API_KEY` from the environment; MCP OAuth credentials are managed by your client and are not automatically exported to Python.

### OpenCode

Merge the `mcp` entries from [examples/opencode.json](../examples/opencode.json) into your existing `opencode.json`. Do not replace the rest of your configuration. Then authenticate:

```bash
opencode mcp auth openrouter
opencode mcp auth artificial-analysis
```

Only the first connection is needed to start. See [OpenCode remote MCP and OAuth](https://opencode.ai/docs/mcp-servers/).

### Optional upstream skills

Model Finder references the official [openrouter-benchmarks](https://openrouter.ai/skills/openrouter-benchmarks) and [openrouter-analytics](https://openrouter.ai/skills/openrouter-analytics) skills without bundling or automatically installing them. Their pages provide installation instructions if you want the full upstream workflows.

The helper's direct `benchmarks` command uses a regular `OPENROUTER_API_KEY`; MCP OAuth credentials are not automatically available to Python. Account analytics requires a management key and is only relevant to requests based on existing account usage. Keep these credentials in the appropriate tool environment, outside this repository. No management key is needed to discover models.

### Optional browser access

Web/search capabilities can fill gaps without a browser MCP. If your workflow needs public interactive pages, [Microsoft Playwright MCP](https://github.com/microsoft/playwright-mcp) is an optional fallback. It is not bundled or installed automatically. For example:

```bash
claude mcp add --scope user playwright -- npx -y @playwright/mcp@latest
codex mcp add playwright -- npx -y @playwright/mcp@latest
```

Follow its current Node.js/browser requirements and your client's platform-specific stdio instructions. Prefer structured MCP/API data when available.

## Check the setup

Ask the agent to load `model-finder` and list which research sources it can actually access. Then try a narrow request:

```text
Find three low-cost text models with tool calling on OpenRouter.
Use current pricing and a 2,000 input / 500 output token estimate.
State which models lack independent task-relevant benchmarks.
```

If a source is unavailable, the answer should state the limitation, use a documented fallback if available, and preserve unknowns. It should not call inference or silently alter the agent's model.

| Problem | Action |
| --- | --- |
| Skill missing | Confirm the whole folder was copied to the right client path; reload the client. |
| Duplicate skill/command | Keep one route per client; OpenCode also scans Claude and shared skill folders. |
| OAuth missing/expired | Reauthenticate using the client's MCP panel or login command. |
| AA 401/403 | Check authentication, organization, and plan; use accessible evidence and state gaps. |
| Rate limited | Wait for the source quota window; label any reused snapshot's timestamp. |
| No eligible candidates | Read exclusion counts, check unknown fields, and relax only preferences—not hard requirements. |
| No live tools/network | Use saved data only as dated/offline evidence; do not claim current recommendations. |
| Agent won't switch to an OpenRouter ID | Model Finder selects application models; host model switching depends on the client's own support. |
