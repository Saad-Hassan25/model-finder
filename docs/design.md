# Design

## A skill around existing data services

The original architecture is retained: a shared skill interprets the task and combines OpenRouter model/provider data, independent Artificial Analysis evidence, and web/browser fallbacks. It outputs an evidence-based recommendation. There is no duplicate MCP service, hosted backend, database, or maintained model leaderboard in this repository.

One `skills/model-finder` directory is the source of truth. Claude and Codex plugin manifests point at the repository layout. The installer copies the full directory for clients supporting Agent Skills. OpenCode uses its native skill mechanism, not a JavaScript plugin that intercepts requests.

## Deliberately separate responsibilities

The agent interprets the user's task, verifies identities and source relevance, checks provider policies, and explains tradeoffs. The optional standard-library Python script handles repeatable arithmetic and catalog constraints. It accepts explicit comparable benchmark evidence rather than silently guessing cross-provider model mappings.

OpenRouter's official benchmark and analytics skills inform two optional paths: source-specific benchmark snapshots in the GET-only helper, and authorized usage aggregates for replacement decisions. Upstream skills are linked rather than vendored or installed. Account analytics is outside the helper; it has a different credential scope and is not needed for general model discovery.

The helper supports text-token cost comparisons and advertised catalog capabilities across available modalities. It retains additional pricing fields and flags that they are excluded from its arithmetic. Media-specific billing, provider SLA/privacy enforcement, live latency ranking, and task evaluation require further evidence; they are not simulated by the CLI.

There is no automatic paid evaluation, runtime router, proxy, or host-model switch. If a user asks to integrate a selected model into an application, the agent uses normal coding tools within that request. Adding an actual runtime router later would require explicit rules for failure modes, retries, budgets, provider credentials, and data transmission.

## Freshness and provenance

Every helper fetch wraps the source response with its URL and retrieval timestamp. Offline shortlisting preserves that timestamp and adds a separate generation time. Old or missing timestamps produce warnings. No automatic cache masks a failed fetch. Synthetic fixtures use fictional IDs and are explicitly dated.

Model `created` is catalog addition time. An independent benchmark's evaluation date is separate. Source links, metric versions, thinking settings, and identity mapping are necessary context for a recommendation; a recently fetched old benchmark remains old evidence.

## Ranking semantics

Hard constraints precede ranking. Unknown required capabilities/prices/limits fail the corresponding constraint. Missing quality scores remain unknown. Decimal arithmetic preserves tiny token prices and exact budget boundaries. JSON serializes decimal values as strings for downstream code to parse explicitly.

Cheapest sorts by the supplied workload's token cost. Quality requires comparable evidence. Value returns the quality/cost Pareto frontier with no hidden weights or score/price ratio. Newest sorts catalog timestamps, clearly labeled. The helper never labels a candidate production-viable based solely on these calculations.

## Boundaries for external data

The helper performs only GET requests to fixed official research URLs, does not accept arbitrary destination URLs, and refuses redirects. It does not send user prompts or code. API errors omit response bodies and credentials. Public release packaging includes only an explicit allowlist and synthetic examples. Artificial Analysis and other provider data licenses remain separate from the MIT repository license.

## What is verified

Offline tests cover unit conversion, cost arithmetic, constraints, missing data, quality floors, Pareto dominance, explicit evidence mapping, source errors, CLI behavior, installer isolation, and archive contents. CI runs these on three operating systems. Native plugin manifests can also be checked with the installed client's validator. Authenticated MCP sessions and client UIs require user-owned credentials; structural/plugin validation does not prove those connections are authenticated.
