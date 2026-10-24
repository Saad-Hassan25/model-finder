# Selection rules

## Eligibility before quality

Separate hard requirements from preferences. Unknown required fields fail eligibility until verified. An empty supported-parameter list does not prove tools or schema support. JSON mode (`response_format`) and JSON Schema support (`structured_outputs`) are different advertised capabilities; endpoint support still needs confirmation.

Input plus requested output must fit the effective context. Check provider context and max completion limits, not only model-level maxima. A token estimate is only an estimate: reserve headroom for system prompts, retrieved content, tool definitions, tool results, and reasoning as appropriate. The helper checks its supplied input/output counts, but cannot infer this extra workload.

Privacy, residency, uptime, speed, licensing, and deployment restrictions often require additional endpoint/provider evidence. The helper's eligibility means its implemented catalog constraints passed; it does not establish all these properties.

## Cost

OpenRouter catalog `pricing.prompt` and `pricing.completion` are USD **per token**. Convert to dollars per million by multiplying by 1,000,000. Missing, negative sentinel, or malformed prices are unknown, never free. Exact zero is a valid zero price.

```text
request_usd = input_tokens × prompt_usd_per_token
            + output_tokens × completion_usd_per_token
monthly_usd = request_usd × requests_per_month
```

This is a token-only estimate. Nonzero `pricing.request`, image/audio/video charges, search/tool fees, cache behavior, billable reasoning output, endpoint-specific prices, long-context tiers, and retries can change the bill. A catalog minimum may not correspond to a single provider supporting every required feature. Inspect the finalist routes and recompute when needed.

For best value, compare incremental quality and cost. A candidate is dominated if another has no higher cost and no lower comparable quality, with at least one strict improvement. Dominance is valid only across otherwise eligible candidates and the chosen comparable metric. It says nothing about unmeasured reliability or speed.

## Benchmark identity

Use a single metric/version with comparable configurations for numeric ranking. Keep coding, intelligence, latency, and task pass-rate results separate. For cross-source joins, inspect the source model identifier, exact revision, thinking budget, variant, and methodology. The helper accepts an explicit evidence file keyed by exact OpenRouter ID; a human/agent must verify those mappings. It does not fuzzy-join names or certify evidence authenticity.

The helper's `value` objective returns the Pareto frontier ordered by cost. It deliberately does not choose a universal best-value winner. For `quality`, only measured candidates rank; unmeasured candidates are counted as excluded for missing evidence. For `cheapest`, unmeasured candidates can appear and are labeled unverified; a specified `--min-score` excludes unknown scores and reports a benchmark floor passed, not production readiness.

## Lightweight evaluation proposal

Use a small representative set (for example 10–30 cases) with the same prompts and output budgets for each finalist. Include typical cases, difficult cases, and expected tool/schema behavior. Score task correctness, schema validity, tool-call correctness, refusals where relevant, retries, end-to-end latency, and actual billed cost. Set a spending cap and define what data may leave the environment. Only execute if the user has authorized that inference and data transmission.
