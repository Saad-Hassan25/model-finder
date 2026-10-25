# Choosing replacements using existing usage

Use this path when asked to optimize model choices for existing traffic. The upstream [openrouter-analytics skill](https://openrouter.ai/skills/openrouter-analytics) handles account usage, requires a management key, and complements discovery. A regular benchmark key does not grant that access. Model Finder neither installs that skill nor requests management credentials for ordinary recommendations.

If analytics access is already available, discover its schema before querying. Match account, period, timezone, and task filters to the request. Prefer aggregates; do not retrieve stored prompts/completions merely to estimate workload. Use available request, spend, input/output token, cache, and timing metrics. Check truncation before treating returned rows as complete totals.

Separate measured historical spend from projected replacement cost. Use comparable workload segments and current eligible routes; report assumptions about cache reuse, reasoning, retries, and additional fees. Popularity and low historical spend are not evidence of task correctness. A slower provider or different task mix can confound apparent savings.

If access is unavailable, use user-supplied aggregates or labeled token assumptions and continue discovery. Keep private account data out of public examples and release archives.
