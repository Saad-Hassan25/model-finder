# Recommendation format

Adapt the length to the request. Do not fill empty categories just to match a template.

```text
Verdict: [exact model ID] fits [objective] because [task-relevant evidence].
Assumptions: [input/output tokens], [volume], [required features], [budget].
Checked: [timestamp + timezone]. Catalog retrieved: [timestamp].

| OpenRouter ID | Task evidence | Input $/M | Output $/M | Cost/request | Context | Caveat |
| ...           | metric/version or unknown | ... | ... | ... | ... | ... |

Cheapest viable: [...] or "provisional; task viability not yet established".
Best value: [...] with the specific quality/cost tradeoff.
Highest quality: [...] within the constraints and comparable evidence.

Endpoint checks: [provider, capability combination, availability, privacy if required].
Uncertainty: [coverage gaps, new releases, benchmark/task mismatch].
Sources: [links alongside the corresponding evidence, with access dates].
Next step: [integration when requested, or a focused evaluation proposal].
```

For an agent implementing an application, include a concise JSON handoff if useful. For example, the shape below uses deliberately fictional values:

```json
{
  "objective": "cheapest",
  "selected_model_id": "example/model-a",
  "provider": null,
  "status": "provisional",
  "requirements": {"tools": true, "structured_outputs": true},
  "estimated_request_usd": null,
  "checked_at": null,
  "evidence_urls": [],
  "unresolved": ["Confirm provider route", "Evaluate task pass rate"]
}
```

Use real timestamps, verified IDs and evidence in an actual handoff. A null provider means routing has not been pinned, not that provider constraints have been satisfied. Keep helper JSON provenance and warnings attached when passing it to another agent.
