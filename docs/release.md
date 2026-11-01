# Model Finder 0.1.0 launch

Public display name: **Model Finder**. Repository, skill and package identifier: **`model-finder`**. The installer executable is `model-finder-install`. No npm publication is required for GitHub-based installation.

## GitHub page

- Repository: `Saad-Hassan25/model-finder` (existing repository renamed on 2026-11-01; stable GitHub ID `1432404481`).
- Description: `Find AI models with live OpenRouter prices and benchmark evidence in Claude Code, Codex, and OpenCode.`
- Topics: `model-finder`, `claude-code`, `codex`, `opencode`, `openrouter`, `agent-skills`, `model-selection`, `benchmarks`, `artificial-analysis`.
- License: MIT.
- Release tag/title: `v0.1.0` / `Model Finder v0.1.0`.

The local launch changes use the renamed repository URL consistently. The remote rename, description and topics are confirmed. **Do not announce the release commands until the launch source and release tag are confirmed.** The repository remains private until its owner chooses to make it public.

## Release checks

```bash
npm ci --ignore-scripts
npm test
python -m unittest discover -s tests -v
python scripts/validate.py
python scripts/package.py
python scripts/launch_check.py --live
```

The last command uses an actual local npm tarball through npx, with temporary homes/projects and no account credentials. It does not test GitHub clone/rename transport or completed OAuth consent. After the renamed repository contains the release source, repeat the documented GitHub npx command in a fresh project, then check the three clients' native skill discovery and consent UI.

Attach `dist/model-finder.zip` and an npm tarball from `npm pack --ignore-scripts` to the release. The release must point to the commit containing these launch changes, not the older pre-launch HEAD. Never tag an old commit merely to make a badge resolve.

## Verification record: 2026-11-01

- Re-read the official [OpenRouter MCP setup](https://openrouter.ai/blog/announcements/openrouter-mcp-server/) and [Artificial Analysis MCP setup](https://artificialanalysis.ai/data-api/docs/mcp). Their documented URLs remain `https://mcp.openrouter.ai/mcp` and `https://mcp.artificialanalysis.ai/mcp`.
- Re-read [Claude MCP](https://code.claude.com/docs/en/mcp), [Claude plugin manifests](https://code.claude.com/docs/en/plugins-reference), [Codex skills](https://learn.chatgpt.com/docs/build-skills), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), [OpenCode MCP](https://opencode.ai/docs/mcp-servers/) and [OpenCode skills](https://opencode.ai/docs/skills/).
- Checked local CLI versions: Claude Code `2.1.295`; Codex CLI `0.141.0`. Their `mcp login --help` commands accept the documented server-name syntax. Claude's `--no-browser` option prints a URL for manual consent. `claude plugin validate .` passes.
- The packed npx installer and installed offline helper passed separately for **Claude Code, Codex and OpenCode**, each in a fresh temporary home/project. OAuth remained pending for both configured research sources in all three cases. This tests adapter output and the packaged executable, not authenticated client sessions.
- Native readback also passed in fresh temporary projects: `claude mcp get openrouter` showed project scope, the correct URL and **Pending approval (run `claude` to approve)**. After marking only the temporary project trusted in its temporary Codex home, `codex mcp get openrouter` showed `enabled: true`, `transport: streamable_http` and the correct URL. Neither result establishes completed provider consent.
- After pushing launch source `9c609ad`, the documented **GitHub npx command** also passed separately for Claude Code, Codex and OpenCode in new temporary homes/projects, followed by each installed offline helper. The private repository clone used the owner's existing GitHub authentication; no research-provider credentials were supplied. This verifies the renamed GitHub source as well as the earlier local tarball route.
- [Hosted CI run 41306974876](https://github.com/Saad-Hassan25/model-finder/actions/runs/41306974876) passed all six Windows/macOS/Linux × Python 3.10/3.13 jobs for the launch source, including Node.js installer tests, Python tests, archive validation and ZIP construction. Local results: 49 Python tests; 25 Node tests passed, with the POSIX symlink test skipped on Windows.
- OpenCode was not installed locally. An isolated attempt to run npm's current `opencode-ai@1.19.5` failed because its Windows executable was incompatible with this host. The OpenCode OAuth commands were verified against official documentation, not a successful local CLI run. Complete that check on a compatible host before claiming end-to-end OpenCode verification.
- A direct unauthenticated GET to each MCP URL returned HTTP 403 in this environment. This does not establish a working authenticated MCP session; do not describe the response as an OAuth success or a provider outage.
- The account-free OpenRouter **catalog** fetch succeeded. See the dated [three-pick demo](demo-2026-11-01.md).
- After the owner authenticated GitHub CLI, confirmed identity/admin access, renamed the existing repository to `Saad-Hassan25/model-finder`, and set the description and topics listed above. GitHub repository ID remained `1432404481` and visibility remained **private**. Release creation is separate from this completed settings update.

If publication happens after this date, rerun the source/client checks and update the verification date from that run. Keep the dated example's original timestamp intact.

## Remote operations after authentication

These commands are for the repository owner or an authenticated maintainer. They do not change repository visibility. Do not run the tag/release steps until the launch source has been reviewed, committed and pushed under the repository's contribution instructions.

```bash
gh repo edit Saad-Hassan25/model-finder --description "Find AI models with live OpenRouter prices and benchmark evidence in Claude Code, Codex, and OpenCode." --add-topic model-finder --add-topic claude-code --add-topic codex --add-topic opencode --add-topic openrouter --add-topic agent-skills --add-topic model-selection --add-topic benchmarks --add-topic artificial-analysis
```

Create an annotated `v0.1.0` tag on the verified release commit, push that tag, then create the release from it:

```bash
gh release create v0.1.0 dist/model-finder.zip dist/model-finder-0.1.0.tgz --repo Saad-Hassan25/model-finder --verify-tag --title "Model Finder v0.1.0" --notes-file docs/release-notes-0.1.0.md
```

The README version badge targets `https://github.com/Saad-Hassan25/model-finder/releases/tag/v0.1.0`. Verify that link and its source commit after creating the release; a badge alone is not proof of publication or CI success.
