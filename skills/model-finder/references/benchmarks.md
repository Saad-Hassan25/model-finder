# Benchmark evidence through OpenRouter

Use available MCP benchmark tools first. For REST access, the helper's `benchmarks` command queries `GET /api/v1/benchmarks` with a regular `OPENROUTER_API_KEY`. Keep returned `meta.citation`, `meta.source_url`, `meta.as_of`, and version attached; retrieval time is separate. Preserve null metadata as unknown. See the [official benchmark skill](https://openrouter.ai/skills/openrouter-benchmarks) and [API contract](https://openrouter.ai/docs/api/api-reference/benchmarks/list-benchmarks).

AA indices and Design Arena Elo have different scales. Compare each metric within its own source and relevant category. Visual/code preferences do not establish prose quality; identify indirect evidence.

Before recommending a benchmark leader, look up `model_permaslug` in the live catalog's `id` field. A match only to `canonical_slug` can identify a family, but does not establish an identical evaluated variant or a routable ID. Resolve the actual ID, configuration, and usable endpoints. Empty routes, zero uptime, access restrictions, and model warnings can outweigh an apparently healthy status field.

The helper saves raw evidence; it does not automatically merge rows into ranking inputs. Verify identities and comparable configurations before creating the explicit evidence file described in [helper.md](helper.md). Preserve source metadata there as extra fields when needed. Do not publish restricted datasets.
