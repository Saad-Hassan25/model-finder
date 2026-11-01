# Model Finder

<p align="center">
  <img src="assets/brand/model-finder-banner.webp" alt="Five connected tiles with one highlighted as the selected model" width="960">
</p>

<p align="center">
  <strong>Find the right model for your next task.</strong><br>
  Find AI models with live OpenRouter prices and benchmark evidence in Claude Code, Codex, and OpenCode.
</p>

<p align="center">
  <a href="#try-it-without-an-account">No-account trial</a> ·
  <a href="#quick-start">Quick start</a> ·
  <a href="#ask">Examples</a> ·
  <a href="docs/setup.md">Documentation</a> ·
  <a href="CONTRIBUTING.md">Contributing</a>
</p>

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22d3ee?style=flat-square&amp;labelColor=111827" alt="License: MIT"></a>
  <a href="https://github.com/Saad-Hassan25/model-finder/releases/tag/v0.1.0"><img src="https://img.shields.io/badge/version-0.1.0-a78bfa?style=flat-square&amp;labelColor=111827" alt="Version: 0.1.0"></a>
  <a href="#optional-helper"><img src="https://img.shields.io/badge/helper-Python_3.10%2B-60a5fa?style=flat-square&amp;labelColor=111827" alt="Optional helper: Python 3.10+"></a>
  <a href="docs/setup.md#connect-research-data"><img src="https://img.shields.io/badge/data-MCP_%2B_REST-34d399?style=flat-square&amp;labelColor=111827" alt="Data access: MCP and REST"></a>
</p>

<p align="center">
  <a href="docs/setup.md#claude-code-plugin"><img src="https://img.shields.io/badge/Claude_Code-skill_%2B_plugin-f0ab78?style=flat-square&amp;labelColor=111827" alt="Claude Code: skill and plugin"></a>
  <a href="docs/setup.md#codex-plugin"><img src="https://img.shields.io/badge/Codex-skill_%2B_plugin-22d3ee?style=flat-square&amp;labelColor=111827" alt="Codex: skill and plugin"></a>
  <a href="docs/setup.md#opencode"><img src="https://img.shields.io/badge/OpenCode-Agent_Skill-a78bfa?style=flat-square&amp;labelColor=111827" alt="OpenCode: Agent Skill"></a>
</p>

---

**For Claude Code, Codex and OpenCode users choosing models on OpenRouter.** Model Finder provides research and recommendations. It is **not a runtime router or an automatic model-switcher, and it does not run paid evaluations**.

## Try it without an account

Download the [release ZIP](https://github.com/Saad-Hassan25/model-finder/releases/download/v0.1.0/model-finder.zip), extract it and open a terminal in that folder. With **Python 3.10+**, run:

```bash
python skills/model-finder/scripts/model_finder.py shortlist --catalog examples/catalog.example.json --benchmarks examples/benchmarks.example.json --objective value
```

**No Node.js, Git, API key, sign-in or network requests are needed for this offline run.** The output includes the price/quality frontier in this order:

```text
example/budget → example/balanced → example/premium
```

These are fictional models for demonstrating filtering and cost calculations; the more expensive, lower-scoring `example/dominated` is excluded. For real, dated output, see the [2026-11-01 price-only example](docs/demo-2026-11-01.md). When you want live research inside your coding client, continue to [Quick start](#quick-start).

Model releases move quickly. Model Finder helps you choose using **current OpenRouter prices, capabilities, provider routes, and independent benchmark evidence**. Describe your task and budget; get exact model IDs, estimated workload costs, and a recommendation with its tradeoffs explained.

| Your priority | What Model Finder checks |
| --- | --- |
| **Cheapest viable** | Price after required capabilities, context, and task evidence are considered |
| **Best value** | The quality gained for the extra workload cost |
| **Highest quality** | Relevant measured capability within your constraints |
| **Fastest** | Available endpoint latency and throughput evidence |
| **Recent releases** | New catalog additions, with benchmark coverage gaps called out |

Use it directly when choosing a model, or let your coding agent use it while building an application. The shared Agent Skill combines OpenRouter, Artificial Analysis, and relevant Design Arena evidence. MCP handles live research; an optional Python helper makes catalog filtering and cost calculations reproducible.

> A recommendation includes uncertainty. Missing benchmarks stay unknown, model IDs are verified, and advertised capabilities are checked against provider routes. Model Finder does not automatically switch its host agent's model or run paid inference.

## Quick start

Run this in your VS Code terminal or any terminal:

```bash
npx --yes github:Saad-Hassan25/model-finder
```

The installer asks **which clients** (Claude Code, Codex, OpenCode, or several), **this project or all projects**, and **which data sources** to connect. It installs the skill, merges MCP settings, and can launch browser sign-in. Start a new client session when it finishes.

**Requires Node.js 22+ and Git.** No manual download, clone, or Python setup. Run inside your project for a project installation, or choose all projects from any directory. Existing settings are preserved and backed up when changed.

### Let your agent install it

Give Claude Code, Codex, or OpenCode this prompt:

```text
Install Model Finder from https://github.com/Saad-Hassan25/model-finder
for this project. Follow INSTALL.md and report any sign-in I need to complete.
```

Agents have a non-interactive installer with explicit scope and JSON output. For example, Codex in the current project:

```bash
npx --yes github:Saad-Hassan25/model-finder --agent codex --scope project --yes --json
```

Use `--scope global` for all projects, `--agent claude-code` or `--agent opencode` for another client, and `--connections both` to include Artificial Analysis. See [INSTALL.md](INSTALL.md) for all flags, upgrades, and the agent installation contract.

### Other skill clients

If you use the Skills CLI, or want its wider client selection:

```bash
npx skills add Saad-Hassan25/model-finder --skill model-finder
```

This route installs the skill; use the [MCP connection guide](docs/setup.md#connect-research-data) for live data access. Native [Claude Code](docs/setup.md#claude-code-plugin) and [Codex](docs/setup.md#codex-plugin) plugins are also available. Choose one installation route per client.

### Ask

| Client | Start your request with |
| --- | --- |
| Claude Code | `/model-finder` |
| Codex | `$model-finder` |
| OpenCode | `Use the model-finder skill.` |

Then describe the workload:

```text
I’m building an agentic RAG system with tool calling and JSON Schema outputs.
Find the three best-value models on OpenRouter with at least 128K context.
Estimate cost for 3,000 input + 500 output tokens and 100,000 requests/month.
Compare independent benchmarks and include promising recent releases.
```

The native Claude plugin uses `/model-finder:model-finder`. Need help? See [setup and troubleshooting](docs/setup.md#check-the-setup).

### See it working

Here is a real **price-only** example, recorded on **2026-11-01 at 17:20 PKT**.

**Task:** find three low-cost models to try for extracting financial figures from text.

**Requirements:** text input, tool calling, JSON Schema output and at least 128K context. Batch jobs are allowed; free routes and changing model aliases are excluded.

**Cost assumption:** each chunk uses 10,000 input tokens and produces 1,500 output tokens. Process 1,000 chunks per month.

| Model | Input price per 1M tokens | Output price per 1M tokens | Estimated monthly cost |
| --- | ---: | ---: | ---: |
| [`openai/gpt-oss-120b`](https://openrouter.ai/openai/gpt-oss-120b) | $0.017 | $0.064 | **$0.266** |
| [`mistralai/mistral-nemo`](https://openrouter.ai/mistralai/mistral-nemo) | $0.029 | $0.030 | **$0.335** |
| [`openai/gpt-oss-20b:batch`](https://openrouter.ai/openai/gpt-oss-20b:batch) | $0.024 | $0.112 | **$0.408** |

**What this shows:** the helper found the cheapest catalog entries matching those filters and calculated their token costs. It did **not** test how accurately they extract financial figures or verify each provider route. The `:batch` pick is for queued jobs, not interactive chat.

Prices are from that dated run and can change. Estimates exclude extra reasoning, caching, fees, retries and pricing tiers. No models were called and no paid evaluation was run. [Full report, exact commands and installation test log](docs/demo-2026-11-01.md).

## A useful recommendation, with its limits

Expect a verdict and a short comparison of exact IDs, task-relevant evidence, input/output $ per million tokens, workload cost, context, and provider limitations. The skill distinguishes the cheapest advertised match from a model with established task fitness. It reports missing evidence and cites the sources it used.

"Best value" depends on the task. Comparable benchmark scores can identify the quality/cost Pareto frontier; the agent explains which tradeoff suits your requirements. A benchmark index alone does not prove JSON reliability, agent performance, or accuracy on your own data.

Research does not imply permission for paid test prompts or uploading private code. The skill uses existing authorization or obtains it before an evaluation. API data access can have its own quota and subscription costs.

## Optional helper

No dependencies beyond Python 3.10+. It can fetch the public OpenRouter catalog without an API key, filter exact capabilities, and estimate costs. Use it when MCP is unavailable or you want reproducible arithmetic.

```bash
python skills/model-finder/scripts/model_finder.py fetch --output .model-finder/catalog.json
python skills/model-finder/scripts/model_finder.py shortlist --catalog .model-finder/catalog.json --require tools --require structured_outputs --min-context 131072 --exclude-free --limit 5
```

With a regular `OPENROUTER_API_KEY` set in the environment, fetch benchmark evidence directly:

```bash
python skills/model-finder/scripts/model_finder.py benchmarks --source artificial-analysis --task-type coding --output .model-finder/benchmarks.json
```

This preserves source citations and dataset dates. Benchmark IDs still need verification against the live catalog before use. For replacement decisions based on existing traffic, the skill can also use authorized usage aggregates; see the optional [usage workflow](skills/model-finder/references/usage.md). Analytics access is separate from model discovery.

For a credential-free first run, use the [offline trial](#try-it-without-an-account). See the [helper reference](skills/model-finder/references/helper.md) for benchmark mappings, JSON output, all ranking modes, and cost assumptions.

## Repository

```text
skills/model-finder/       Shared Agent Skill, references, and standalone helper
.claude-plugin/           Claude plugin manifest and local marketplace
.codex-plugin/            Codex compatibility plugin manifest
.agents/plugins/          Native Codex marketplace entry
.mcp.json                 Official research MCP endpoints; no credentials
assets/brand/             Original logo and README banner
examples/                 OpenCode config and clearly synthetic test data
bin/                      Guided npx installer and MCP configuration
scripts/                  Validation, release packaging, legacy Python copy helper
INSTALL.md                Human and agent installation instructions
tests/                    Offline behavior and integration tests
docs/                     Setup and design decisions
.github/                  CI, issue templates, and pull request template
```

Everything needed to install and use the skill is self-contained. Source APIs and MCP servers supply live data when you use it.

Logo files and generation prompts are documented in [branding](docs/branding.md).

## Development

```bash
npm ci --ignore-scripts
npm test
python -m unittest discover -s tests -v
python scripts/validate.py
python scripts/package.py
```

CI runs the Node.js installer tests and Python checks on Windows, macOS, and Linux, then builds an installable ZIP. There are no live API calls in CI. Read [CONTRIBUTING.md](CONTRIBUTING.md) for changes and [docs/design.md](docs/design.md) for the architecture and current boundaries.

The ZIP builder uses an allowlist and excludes local notes, credentials, caches, and live data snapshots.

## Sources and license

Integration formats and documented endpoints were rechecked on **2026-11-01** against the official [OpenRouter MCP documentation](https://openrouter.ai/blog/announcements/openrouter-mcp-server/), [Artificial Analysis MCP documentation](https://artificialanalysis.ai/data-api/docs/mcp), [Claude plugin reference](https://code.claude.com/docs/en/plugins-reference), [Codex skill documentation](https://learn.chatgpt.com/docs/build-skills), [OpenAI plugin packaging](https://developers.openai.com/plugins/build/plugins), and [OpenCode skill documentation](https://opencode.ai/docs/skills/). This is a documentation/CLI check, not a claim of completed OAuth in every client. [Exact verification record and release checks](docs/release.md). Recheck on the actual publication day if it is later; preserve the dated demo's original run date.

MIT for the code and skill. Provider data, benchmarks, trademarks, and services retain their own terms. This is an independent project, not affiliated with those providers.
