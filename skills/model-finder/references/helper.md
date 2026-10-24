# Optional deterministic helper

The skill works through MCP without Python. The helper is a fallback and calculation aid: Python 3.10+, standard library only, GET requests only. Run it relative to this skill directory, or resolve its absolute path from the loaded skill. In this repository, prefix paths with `skills/model-finder/`.

```bash
python scripts/model_finder.py fetch --output .model-finder/catalog.json
python scripts/model_finder.py shortlist --catalog .model-finder/catalog.json --require tools --require structured_outputs --min-context 131072 --input-tokens 3000 --output-tokens 500 --requests-per-month 100000 --exclude-free --limit 5
python scripts/model_finder.py endpoints AUTHOR/MODEL --output .model-finder/endpoints.json
```

Replace `AUTHOR/MODEL` with a verified returned ID. Each network command fetches fresh data. `shortlist` is offline and preserves the snapshot's original retrieval time. Raw OpenRouter `{ "data": [...] }` JSON is accepted but has unknown provenance unless wrapped with `source_url` and `retrieved_at`.

Default illustrative workload: 2,000 input / 500 output tokens, 1,000 requests/month, text output. Override all three for real estimates. Add `--input-modality text` or `image` as needed (repeat for multiple inputs). `--require` accepts exact catalog parameter names; use `structured_outputs` for schema support, not merely `response_format`. A model must have a known sufficient output limit when output tokens are positive; missing required data fails that constraint.

Price caps `--max-input-price` and `--max-output-price` are **USD per million tokens**. `--max-monthly-cost` is USD for the supplied workload. `--exclude-free` excludes models with both token prices zero. `--exclude-aliases` excludes dynamic `~provider/model` aliases; otherwise they are preserved and labeled `dynamic_alias: true`. Resolve their targets before deployment. Empty results are a successful query with an empty candidate array and exclusion counts. Exclusion counts can overlap because one model may fail several constraints.

## Benchmark-assisted ranking

Fetch OpenRouter's source-specific benchmark data using `OPENROUTER_API_KEY` from the process environment (a regular key is sufficient):

```bash
python scripts/model_finder.py benchmarks --source artificial-analysis --task-type coding --max-results 20 --output .model-finder/benchmarks.json
python scripts/model_finder.py benchmarks --source design-arena --arena models --category uicomponent --output .model-finder/design.json
```

The default source is Artificial Analysis; `--arena` and `--category` are Design Arena filters. Raw rows and `response.meta` remain intact, including citation and dataset timestamp fields. The snapshot is not the normalized `--benchmarks` ranking input: read [benchmarks.md](benchmarks.md), verify IDs and configurations, then construct the evidence file below. Do not assume every benchmark row is a currently available model.

You can also fetch Artificial Analysis directly if you have its API access:

```bash
python scripts/model_finder.py fetch --source artificial-analysis --output .model-finder/aa.json
```

Set `AA_API_KEY` in the process environment, never on a command line or in a committed file. Fetching may consume source quotas. Authentication failures are explicit; the helper does not fall back to fabricated scores. Both benchmark sources produce **raw evidence**, not automatic name joins. Account analytics is a separate optional workflow with different credentials; the helper does not query it.

Create an explicit evidence file after verifying identities against the catalog. Use one comparable metric, version, and configuration per file:

```json
{
  "metric": "Exact metric name",
  "version": "Exact version or explicitly unknown",
  "configuration": "Comparable model variants and reasoning settings",
  "direction": "higher",
  "source_url": "https://artificialanalysis.ai/models",
  "as_of": "2026-10-24",
  "models": [
    { "openrouter_id": "example/replace-with-verified-id", "score": 85 }
  ]
}
```

The score and ID above illustrate the schema; they are not real data. Set the actual evidence date. Omit unmeasured rows. Mapping is explicit and must be verified; the helper validates structure, not whether someone fabricated evidence. Without a known comparable version/configuration, keep results qualitative instead of merging numbers.

```bash
python scripts/model_finder.py shortlist --catalog .model-finder/catalog.json --benchmarks .model-finder/evidence.json --objective quality
python scripts/model_finder.py shortlist --catalog .model-finder/catalog.json --benchmarks .model-finder/evidence.json --objective value
python scripts/model_finder.py shortlist --catalog .model-finder/catalog.json --benchmarks .model-finder/evidence.json --objective cheapest --min-score 80
```

- `cheapest`: ascending estimated workload cost; no implicit quality floor.
- `quality`: descending comparable quality (or ascending for `direction: lower`). Unmeasured candidates are excluded and counted.
- `value`: quality/cost Pareto frontier, cheapest first. Choose a tradeoff using the task and budget; the helper does not declare a universal winner.
- `newest`: descending catalog creation timestamp, not verified original release date.
- `--min-score`: a higher-is-better floor, excluding missing evidence. Passing it is not proof of application reliability.

Every output includes source time, workload, constraints, exclusion counts, evidence status, and warnings. Money and scores use decimal **strings** in JSON to preserve exact values. `endpoint_verified: false` means provider inspection is still needed. `pareto_efficient: null` means no comparable quality evidence, not a dominated model. Additional catalog pricing is retained separately; the helper calculates token-only costs and warns about unmodeled charges.

Use `--output PATH` for JSON files or omit it for stdout. Fetch/validation errors go to stderr and exit 1; usage errors exit 2. Saved files under `.model-finder/` are ignored by this repository. Never treat synthetic examples as live results.
