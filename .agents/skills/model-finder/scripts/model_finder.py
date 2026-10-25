#!/usr/bin/env python3
"""GET-only model research and deterministic shortlisting. Python 3.10+, stdlib only."""

from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
import json
import os
from pathlib import Path
import re
import sys
from urllib.error import HTTPError, URLError
from urllib.parse import quote, urlencode, urlsplit
from urllib.request import HTTPRedirectHandler, Request, build_opener

VERSION = "0.1.0"
OPENROUTER = "https://openrouter.ai/api/v1/models"
OPENROUTER_BENCHMARKS = "https://openrouter.ai/api/v1/benchmarks"
ARTIFICIAL_ANALYSIS = "https://artificialanalysis.ai/api/v2/language/models"
MAX_BYTES = 32 * 1024 * 1024
MILLION = Decimal(1_000_000)


class FinderError(ValueError):
    """An actionable input or source error, safe to display without credentials."""


def utcnow():
    return datetime.now(timezone.utc)


def timestamp():
    return utcnow().isoformat(timespec="seconds")


def number(value):
    """Accept finite nonnegative numbers; do not reinterpret sentinels as free."""
    if value is None or isinstance(value, bool):
        return None
    try:
        result = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return result if result.is_finite() and result >= 0 else None


def decimal_arg(value):
    result = number(value)
    if result is None:
        raise argparse.ArgumentTypeError("must be a finite nonnegative number")
    return result


def count_arg(value):
    try:
        result = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be a nonnegative integer") from exc
    if result < 0:
        raise argparse.ArgumentTypeError("must be a nonnegative integer")
    return result


def positive_arg(value):
    result = count_arg(value)
    if result == 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return result


def integer(value):
    result = number(value)
    return int(result) if result is not None and result == result.to_integral_value() else None


def object_or_empty(value):
    return value if isinstance(value, dict) else {}


def strings(value):
    return [item for item in value if isinstance(item, str)] if isinstance(value, list) else []


def valid_id(value):
    return isinstance(value, str) and re.fullmatch(r"~?[A-Za-z0-9][A-Za-z0-9_.:-]*/[A-Za-z0-9][A-Za-z0-9_.:-]*", value) is not None


class NoRedirects(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        # Never forward an API key to a different destination, even after a redirect.
        raise FinderError("Source redirected. Check its current official API URL.")


def fetch_json(url, api_key=None, bearer_token=None):
    headers = {"Accept": "application/json", "User-Agent": f"model-finder/{VERSION}"}
    if api_key:
        headers["x-api-key"] = api_key
    if bearer_token:
        headers["Authorization"] = "Bearer " + bearer_token
    request = Request(url, headers=headers, method="GET")
    try:
        with build_opener(NoRedirects()).open(request, timeout=30) as response:
            raw = response.read(MAX_BYTES + 1)
    except HTTPError as exc:
        # Error bodies and URLs can include secrets; report only the status code.
        advice = {
            401: "Authentication required; check your key or use MCP OAuth.",
            403: "Access denied; check your plan and permissions.",
            404: "Endpoint unavailable; check current source documentation.",
            429: "Rate limit reached; retry later or use an existing snapshot.",
        }.get(exc.code, "Source request failed; retry later.")
        raise FinderError(f"HTTP {exc.code}: {advice}") from None
    except (URLError, TimeoutError, OSError, ValueError):
        raise FinderError("Network request failed; check connectivity or use --catalog offline.") from None
    if len(raw) > MAX_BYTES:
        raise FinderError("Source response exceeds the 32 MiB limit.")
    try:
        payload = json.loads(raw)
    except (ValueError, UnicodeError):
        raise FinderError("Source returned invalid JSON.") from None
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), (list, dict)):
        raise FinderError("Source response must contain a data array or object; API schema may have changed.")
    return {"schema_version": 1, "source_url": url, "retrieved_at": timestamp(), "response": payload}


def fetch_benchmarks(args):
    if (args.arena or args.category) and args.source != "design-arena":
        raise FinderError("--arena and --category require --source design-arena.")
    key = os.environ.get("OPENROUTER_API_KEY")
    if not key:
        raise FinderError("Set OPENROUTER_API_KEY to a regular OpenRouter key, or use the MCP benchmark tools.")
    params = {"source": args.source, "max_results": args.max_results}
    for field in ("task_type", "arena", "category"):
        value = getattr(args, field)
        if value is not None:
            params[field] = value
    result = fetch_json(OPENROUTER_BENCHMARKS + "?" + urlencode(params),
                        bearer_token=key)
    payload = result["response"]
    if not isinstance(payload.get("data"), list) or not isinstance(payload.get("meta"), dict):
        raise FinderError("Benchmark response must contain data and meta; check the current API schema.")
    return result


def load_json(path):
    try:
        with Path(path).open(encoding="utf-8-sig") as handle:
            return json.load(handle)
    except (OSError, ValueError, UnicodeError):
        raise FinderError("Cannot read JSON input; check the path, encoding, and JSON syntax.") from None


def provenance(snapshot):
    warnings = []
    retrieved = snapshot.get("retrieved_at")
    if not isinstance(retrieved, str):
        warnings.append("Catalog retrieval time unknown; refresh before recommending.")
    else:
        try:
            date = datetime.fromisoformat(retrieved.replace("Z", "+00:00"))
            if date.utcoffset() is None:
                raise ValueError
            age = (utcnow() - date).total_seconds()
            if age > 86400:
                warnings.append("Catalog is older than 24 hours; refresh prices and availability.")
            elif age < -300:
                warnings.append("Catalog retrieval time is in the future; verify provenance.")
        except (ValueError, OverflowError):
            warnings.append("Catalog retrieval time invalid; refresh before recommending.")
    return {"source_url": snapshot.get("source_url"), "retrieved_at": retrieved}, warnings


def normalize_catalog(snapshot):
    if not isinstance(snapshot, dict):
        raise FinderError("Catalog must be an OpenRouter JSON object or a helper snapshot.")
    payload = snapshot.get("response", snapshot)
    if not isinstance(payload, dict) or not isinstance(payload.get("data"), list):
        raise FinderError("Catalog must contain a data array (OpenRouter /models format).")
    models, invalid, seen = [], 0, set()
    for raw in payload["data"]:
        if not isinstance(raw, dict) or not valid_id(raw.get("id")):
            invalid += 1
            continue
        model_id = raw["id"]
        if model_id in seen:
            raise FinderError("Catalog contains duplicate model IDs; resolve before ranking.")
        seen.add(model_id)
        pricing = object_or_empty(raw.get("pricing"))
        architecture = object_or_empty(raw.get("architecture"))
        provider = object_or_empty(raw.get("top_provider"))
        contexts = [integer(raw.get("context_length")), integer(provider.get("context_length"))]
        contexts = [x for x in contexts if x is not None]
        models.append({
            "id": model_id,
            "name": raw.get("name") if isinstance(raw.get("name"), str) else model_id,
            "context_length": min(contexts) if contexts else None,
            "max_output_tokens": integer(provider.get("max_completion_tokens")),
            "created": integer(raw.get("created")),
            "input_modalities": strings(architecture.get("input_modalities")),
            "output_modalities": strings(architecture.get("output_modalities")),
            "supported_parameters": strings(raw.get("supported_parameters")),
            "prompt": number(pricing.get("prompt")),
            "completion": number(pricing.get("completion")),
            "extra_pricing": {k: v for k, v in pricing.items() if k not in ("prompt", "completion")},
        })
    return models, invalid


def benchmark_evidence(document):
    if not isinstance(document, dict):
        raise FinderError("Benchmark evidence must be an object.")
    for key in ("metric", "version", "configuration", "source_url", "as_of"):
        if not isinstance(document.get(key), str) or not document[key].strip():
            raise FinderError(f"Benchmark evidence requires a nonempty {key}.")
    if document.get("direction") not in ("higher", "lower"):
        raise FinderError("Benchmark direction must be higher or lower.")
    parsed_url = urlsplit(document["source_url"])
    if parsed_url.scheme != "https" or not parsed_url.netloc:
        raise FinderError("Benchmark source_url must be an HTTPS source link.")
    try:
        datetime.strptime(document["as_of"], "%Y-%m-%d")
    except ValueError:
        raise FinderError("Benchmark as_of must be a YYYY-MM-DD date.") from None
    entries = document.get("models")
    if not isinstance(entries, list):
        raise FinderError("Benchmark evidence requires a models array.")
    mapping = {}
    for entry in entries:
        if not isinstance(entry, dict) or not valid_id(entry.get("openrouter_id")):
            raise FinderError("Each benchmark entry requires an exact openrouter_id.")
        model_id, score = entry["openrouter_id"], number(entry.get("score"))
        if score is None:
            raise FinderError("Benchmark scores must be finite nonnegative numbers; omit unknown results.")
        if model_id in mapping:
            raise FinderError("Duplicate benchmark model ID; resolve variants/configurations explicitly.")
        mapping[model_id] = score
    metadata = {k: v for k, v in document.items() if k != "models"}
    return metadata, mapping


def shortlist(snapshot, args, evidence=None):
    models, invalid = normalize_catalog(snapshot)
    source, warnings = provenance(snapshot)
    metadata, scores = benchmark_evidence(evidence) if evidence is not None else (None, {})
    if args.objective in ("quality", "value") and metadata is None:
        raise FinderError("quality/value needs --benchmarks with verified identity mappings and a comparable metric.")
    if args.min_score is not None and metadata is None:
        raise FinderError("--min-score requires --benchmarks.")
    if args.min_score is not None and metadata["direction"] != "higher":
        raise FinderError("--min-score is only valid for higher-is-better metrics.")
    if metadata:
        unknown = sorted(set(scores) - {m["id"] for m in models})
        if unknown:
            warnings.append(f"{len(unknown)} benchmark IDs are absent from this catalog; no fuzzy matching applied.")
        benchmark_age = (utcnow().date() - datetime.strptime(metadata["as_of"], "%Y-%m-%d").date()).days
        if benchmark_age > 30:
            warnings.append("Benchmark evidence is older than 30 days; check coverage and methodology updates.")
        elif benchmark_age < 0:
            warnings.append("Benchmark date is in the future; verify provenance.")
    rejected, eligible = Counter(), []
    for model in models:
        reasons = []
        p, c = model["prompt"], model["completion"]
        if p is None or c is None:
            reasons.append("unknown_token_price")
        if args.exclude_free and p == 0 and c == 0:
            reasons.append("free_excluded")
        if args.exclude_aliases and model["id"].startswith("~"):
            reasons.append("dynamic_alias_excluded")
        needed_context = max(args.min_context, args.input_tokens + args.output_tokens)
        if needed_context and (model["context_length"] is None or model["context_length"] < needed_context):
            reasons.append("context")
        if args.output_tokens and model["max_output_tokens"] is not None and model["max_output_tokens"] < args.output_tokens:
            reasons.append("output_limit")
        if args.output_tokens and model["max_output_tokens"] is None:
            reasons.append("unknown_output_limit")
        if not set(args.require).issubset(model["supported_parameters"]):
            reasons.append("required_parameters")
        if not set(args.input_modality).issubset(model["input_modalities"]):
            reasons.append("input_modality")
        if args.output_modality not in model["output_modalities"]:
            reasons.append("output_modality")
        if args.max_input_price is not None and (p is None or p * MILLION > args.max_input_price):
            reasons.append("input_price_cap")
        if args.max_output_price is not None and (c is None or c * MILLION > args.max_output_price):
            reasons.append("output_price_cap")
        cost = p * args.input_tokens + c * args.output_tokens if p is not None and c is not None else None
        monthly = cost * args.requests_per_month if cost is not None else None
        if args.max_monthly_cost is not None and (monthly is None or monthly > args.max_monthly_cost):
            reasons.append("monthly_budget")
        score = scores.get(model["id"])
        if args.min_score is not None and (score is None or score < args.min_score):
            reasons.append("quality_floor")
        if args.objective in ("quality", "value") and score is None:
            reasons.append("missing_benchmark")
        if args.objective == "newest" and model["created"] is None:
            reasons.append("unknown_catalog_date")
        if reasons:
            rejected.update(set(reasons))
            continue
        eligible.append({
            "id": model["id"], "name": model["name"],
            "url": "https://openrouter.ai/" + quote(model["id"], safe="/:-._"),
            "input_usd_per_million": p * MILLION,
            "output_usd_per_million": c * MILLION,
            "estimated_request_usd": cost, "estimated_monthly_usd": monthly,
            "context_length": model["context_length"], "max_output_tokens": model["max_output_tokens"],
            "catalog_added_unix": model["created"],
            "supported_parameters": model["supported_parameters"],
            "benchmark_score": score,
            "evidence_status": "benchmark_floor_passed" if args.min_score is not None else (
                "benchmark_available_viability_unverified" if score is not None else "task_viability_unverified"),
            "additional_pricing": model["extra_pricing"],
            "endpoint_verified": False,
            "dynamic_alias": model["id"].startswith("~"),
        })
    direction = -1 if metadata and metadata["direction"] == "lower" else 1

    def quality(item):
        return direction * item["benchmark_score"]

    # Unknown evidence is not a zero score and is never compared numerically.
    measured = [m for m in eligible if m["benchmark_score"] is not None]
    for candidate in eligible:
        candidate["pareto_efficient"] = None if candidate["benchmark_score"] is None else not any(
            other["estimated_request_usd"] <= candidate["estimated_request_usd"]
            and quality(other) >= quality(candidate)
            and (other["estimated_request_usd"] < candidate["estimated_request_usd"] or quality(other) > quality(candidate))
            for other in measured
        )
    ranked = eligible
    if args.objective == "value":
        ranked = [m for m in eligible if m["pareto_efficient"]]
    if args.objective == "quality":
        ranked.sort(key=lambda m: (-quality(m), m["estimated_request_usd"], m["id"]))
    elif args.objective == "newest":
        ranked.sort(key=lambda m: (-m["catalog_added_unix"], m["estimated_request_usd"], m["id"]))
    else:
        ranked.sort(key=lambda m: (m["estimated_request_usd"], m["id"]))
    warnings.extend([
        "Catalog-level constraints only; verify a single provider route satisfies the full requirement set.",
        "Token-only estimate excludes reasoning beyond supplied output, caching, extra fees, retries, and pricing tiers.",
        "Benchmark evidence does not establish task viability; no inference was run.",
    ])
    if any(m["dynamic_alias"] for m in ranked[:args.limit]):
        warnings.append("Dynamic aliases can change their underlying model; resolve and pin an exact release before deployment.")
    if invalid:
        warnings.append(f"Skipped {invalid} malformed catalog entries.")
    return {
        "schema_version": 1, "generated_at": timestamp(), "catalog": source,
        "objective": args.objective,
        "ranking": "pareto_frontier_cost_ascending" if args.objective == "value" else args.objective,
        "workload": {"input_tokens": args.input_tokens, "output_tokens": args.output_tokens,
                     "requests_per_month": args.requests_per_month},
        "constraints": {k: getattr(args, k) for k in (
            "min_context", "require", "input_modality", "output_modality", "exclude_free", "exclude_aliases", "max_input_price",
            "max_output_price", "max_monthly_cost", "min_score")},
        "benchmark": metadata,
        "counts": {"catalog": len(models), "eligible": len(eligible), "ranked": len(ranked),
                   "returned": min(len(ranked), args.limit), "malformed": invalid},
        "excluded_by_reason": dict(sorted(rejected.items())),
        "warnings": warnings,
        "candidates": ranked[:args.limit],
    }


def json_default(value):
    if isinstance(value, Decimal):
        # Decimal strings preserve small prices exactly for downstream agents.
        return format(value, "f")
    raise TypeError(f"Not JSON serializable: {type(value).__name__}")


def emit(result, output):
    rendered = json.dumps(result, indent=2, ensure_ascii=False, default=json_default, allow_nan=False) + "\n"
    if output:
        destination = Path(output)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_text(rendered, encoding="utf-8")
    else:
        print(rendered, end="")


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--version", action="version", version=VERSION)
    commands = root.add_subparsers(dest="command", required=True)
    fetch = commands.add_parser("fetch", help="Fetch a timestamped research-data snapshot (no inference).")
    fetch.add_argument("--source", choices=("openrouter", "artificial-analysis"), default="openrouter")
    fetch.add_argument("--output", type=Path)
    endpoints = commands.add_parser("endpoints", help="Fetch provider details for an exact OpenRouter ID.")
    endpoints.add_argument("model_id")
    endpoints.add_argument("--output", type=Path)
    benchmarks = commands.add_parser("benchmarks", help="Fetch source-specific OpenRouter benchmark evidence (key required).")
    benchmarks.add_argument("--source", choices=("artificial-analysis", "design-arena"), default="artificial-analysis")
    benchmarks.add_argument("--task-type", choices=("coding", "intelligence", "agentic"))
    benchmarks.add_argument("--arena", choices=("models", "builders", "agents"))
    benchmarks.add_argument("--category", help="Design Arena category, e.g. uicomponent, dataviz, or svg.")
    benchmarks.add_argument("--max-results", type=positive_arg, default=20)
    benchmarks.add_argument("--output", type=Path)
    rank = commands.add_parser("shortlist", help="Filter a saved catalog, calculate costs, and rank candidates.")
    rank.add_argument("--catalog", type=Path, required=True)
    rank.add_argument("--benchmarks", type=Path)
    rank.add_argument("--objective", choices=("cheapest", "quality", "value", "newest"), default="cheapest")
    rank.add_argument("--input-tokens", type=count_arg, default=2000)
    rank.add_argument("--output-tokens", type=count_arg, default=500)
    rank.add_argument("--requests-per-month", type=positive_arg, default=1000)
    rank.add_argument("--min-context", type=count_arg, default=0)
    rank.add_argument("--require", action="append", default=[], metavar="PARAMETER",
                      help="Repeat for tools, structured_outputs, reasoning, etc.")
    rank.add_argument("--input-modality", action="append", default=[], metavar="MODALITY")
    rank.add_argument("--output-modality", default="text")
    rank.add_argument("--max-input-price", type=decimal_arg, help="USD per million input tokens.")
    rank.add_argument("--max-output-price", type=decimal_arg, help="USD per million output tokens.")
    rank.add_argument("--max-monthly-cost", type=decimal_arg, help="USD at the specified workload.")
    rank.add_argument("--min-score", type=decimal_arg, help="Higher-is-better benchmark floor.")
    rank.add_argument("--exclude-free", action="store_true")
    rank.add_argument("--exclude-aliases", action="store_true", help="Exclude dynamic ~provider/model catalog aliases.")
    rank.add_argument("--limit", type=positive_arg, default=10)
    rank.add_argument("--output", type=Path)
    return root


def main(argv=None):
    args = parser().parse_args(argv)
    try:
        if args.command == "fetch":
            if args.source == "artificial-analysis":
                key = os.environ.get("AA_API_KEY")
                if not key:
                    raise FinderError("Set AA_API_KEY for the REST fallback, or use Artificial Analysis MCP OAuth.")
                result = fetch_json(ARTIFICIAL_ANALYSIS, api_key=key)
            else:
                result = fetch_json(OPENROUTER)
        elif args.command == "benchmarks":
            result = fetch_benchmarks(args)
        elif args.command == "endpoints":
            if not valid_id(args.model_id):
                raise FinderError("Use an exact author/model ID from the catalog, without URLs or query strings.")
            result = fetch_json(OPENROUTER + "/" + quote(args.model_id, safe="/:-._") + "/endpoints")
        else:
            result = shortlist(load_json(args.catalog), args, load_json(args.benchmarks) if args.benchmarks else None)
        emit(result, args.output)
    except (FinderError, OSError) as exc:
        print(f"model-finder: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
