# Sources and freshness

Use these roles rather than substituting one provider's facts for another's:

| Question | Preferred evidence |
| --- | --- |
| Is the model on OpenRouter? Exact ID? | Live OpenRouter catalog and model detail |
| What does this workload cost on OpenRouter? | OpenRouter pricing, then finalist provider endpoints and tiers |
| Does one route satisfy tools, schema, context, privacy? | Provider endpoint details and relevant official provider documentation |
| How capable is the model? | Task-relevant independent evaluations, including Artificial Analysis |
| Is a new release promising? | Release notes plus live catalog; label unverified performance claims |
| Will it pass this application's cases? | A representative evaluation of that application |
| What workload is this account actually running? | Authorized account analytics or user-supplied aggregates; see [usage.md](usage.md) |

Official remote MCP endpoints:

- OpenRouter: `https://mcp.openrouter.ai/mcp` — OAuth. Discover tools dynamically. Research can use catalog, model, endpoint, and benchmark tools. `send-message` is inference and can be billable; do not use it merely to look up data.
- Artificial Analysis: `https://mcp.artificialanalysis.ai/mcp` — OAuth or API key. The REST equivalent uses `AA_API_KEY` in `x-api-key`. Plan coverage and quotas vary; report access gaps instead of implying unavailable evaluations were checked.

The helper provides GET-only REST fallbacks:

- `https://openrouter.ai/api/v1/models` — public catalog.
- `https://openrouter.ai/api/v1/models/{author}/{slug}/endpoints` — provider details.
- `https://openrouter.ai/api/v1/benchmarks` — source-specific benchmark evidence (regular OpenRouter key; [interpretation](benchmarks.md)).
- `https://artificialanalysis.ai/api/v2/language/models` — language-model benchmark data (key required; check current API documentation if a version changes).

Use live MCP first. Fetch fresh for each recommendation session, and reuse that session's timestamped snapshot for deterministic calculations. The helper marks saved catalogs older than 24 hours as stale; for volatile facts such as price and endpoints, refresh before a final recommendation even within that window. Offline fixtures are examples, never current evidence. An old retrieved time and a recent recommendation time are different facts.

If an API is inaccessible, use official pages or accessible independent public results and state the coverage limit. Browser automation is optional and comes last, for public pages unavailable through structured tools. Do not bypass sign-in or paid access.

Artificial Analysis data may have attribution, usage, and redistribution requirements separate from this repository's MIT code license. Link to Artificial Analysis and the actual metric; do not publish bulk snapshots or restricted evaluation data in a public repository. Review the current [data API terms and documentation](https://artificialanalysis.ai/data-api/docs).

Primary references:

- [OpenRouter MCP](https://openrouter.ai/blog/announcements/openrouter-mcp-server/)
- [OpenRouter models API](https://openrouter.ai/docs/api/api-reference/models/list-all-models-and-their-properties)
- [OpenRouter benchmark skill](https://openrouter.ai/skills/openrouter-benchmarks)
- [OpenRouter analytics skill](https://openrouter.ai/skills/openrouter-analytics)
- [Artificial Analysis models](https://artificialanalysis.ai/models)
- [Artificial Analysis data API](https://artificialanalysis.ai/data-api/docs)
- [Artificial Analysis MCP](https://artificialanalysis.ai/data-api/docs/mcp)
