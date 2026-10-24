import contextlib
import copy
from decimal import Decimal
import importlib.util
import io
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from urllib.error import HTTPError, URLError
from urllib.parse import parse_qs, urlsplit

ROOT = Path(__file__).resolve().parents[1]
HELPER = ROOT / "skills/model-finder/scripts/model_finder.py"


def load_module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


finder = load_module("model_finder", HELPER)


class ShortlistTests(unittest.TestCase):
    def setUp(self):
        self.catalog = json.loads((ROOT / "examples/catalog.example.json").read_text())
        self.evidence = json.loads((ROOT / "examples/benchmarks.example.json").read_text())

    def rank(self, *arguments, evidence=False):
        args = finder.parser().parse_args(["shortlist", "--catalog", "unused", *arguments])
        return finder.shortlist(self.catalog, args, self.evidence if evidence else None)

    def test_openrouter_per_token_prices_and_monthly_arithmetic(self):
        result = self.rank("--input-tokens", "3000", "--output-tokens", "500", "--requests-per-month", "100000")
        first = result["candidates"][0]
        self.assertEqual(first["input_usd_per_million"], Decimal("0.1"))
        self.assertEqual(first["output_usd_per_million"], Decimal("0.4"))
        self.assertEqual(first["estimated_request_usd"], Decimal("0.0005"))
        self.assertEqual(first["estimated_monthly_usd"], Decimal("50"))
        self.assertFalse(first["endpoint_verified"])

    def test_unknown_negative_nonfinite_prices_are_not_free(self):
        for bad in (None, "-1", "NaN", "Infinity", "invalid", True):
            with self.subTest(bad=bad):
                self.catalog["response"]["data"][0]["pricing"]["prompt"] = bad
                result = self.rank()
                self.assertNotIn("example/budget", [m["id"] for m in result["candidates"]])
                self.assertEqual(result["excluded_by_reason"]["unknown_token_price"], 1)

    def test_real_zero_price_is_kept_and_can_be_excluded(self):
        self.catalog["response"]["data"][0]["pricing"] = {"prompt": "0", "completion": "0"}
        self.assertEqual(self.rank()["candidates"][0]["estimated_request_usd"], 0)
        self.assertNotIn("example/budget", [m["id"] for m in self.rank("--exclude-free")["candidates"]])

    def test_tools_and_schema_are_both_required(self):
        self.catalog["response"]["data"][0]["supported_parameters"] = ["tools", "response_format"]
        result = self.rank("--require", "tools", "--require", "structured_outputs")
        self.assertNotIn("example/budget", [m["id"] for m in result["candidates"]])
        self.assertEqual(result["excluded_by_reason"]["required_parameters"], 1)

    def test_context_includes_output_and_effective_provider_limit(self):
        model = self.catalog["response"]["data"][0]
        model["context_length"] = 200000
        model["top_provider"]["context_length"] = 3000
        result = self.rank("--input-tokens", "2800", "--output-tokens", "500")
        self.assertEqual(result["excluded_by_reason"]["context"], 1)
        self.assertNotIn(model["id"], [m["id"] for m in result["candidates"]])

    def test_output_cap_and_unknown_limit_fail(self):
        for cap in (100, None):
            self.catalog["response"]["data"][0]["top_provider"]["max_completion_tokens"] = cap
            result = self.rank()
            self.assertNotIn("example/budget", [m["id"] for m in result["candidates"]])

    def test_budget_boundary_is_exact(self):
        result = self.rank("--max-monthly-cost", "0.4")
        self.assertEqual([m["id"] for m in result["candidates"]], ["example/budget"])
        self.assertEqual(self.rank("--max-monthly-cost", "0.399999")["candidates"], [])

    def test_input_and_output_price_caps_use_per_million_units(self):
        result = self.rank("--max-input-price", "0.1", "--max-output-price", "0.4")
        self.assertEqual([m["id"] for m in result["candidates"]], ["example/budget"])

    def test_modalities_are_hard_filters(self):
        result = self.rank("--input-modality", "text", "--input-modality", "image")
        self.assertEqual({m["id"] for m in result["candidates"]}, {"example/balanced", "example/premium"})
        self.assertEqual(self.rank("--output-modality", "audio")["candidates"], [])

    def test_no_evidence_means_unknown_not_zero(self):
        first = self.rank()["candidates"][0]
        self.assertIsNone(first["benchmark_score"])
        self.assertIsNone(first["pareto_efficient"])
        self.assertEqual(first["evidence_status"], "task_viability_unverified")

    def test_quality_and_value_require_evidence(self):
        for objective in ("quality", "value"):
            with self.assertRaises(finder.FinderError):
                self.rank("--objective", objective)

    def test_quality_sort_and_floor(self):
        result = self.rank("--objective", "quality", evidence=True)
        self.assertEqual(result["candidates"][0]["id"], "example/premium")
        result = self.rank("--min-score", "80", evidence=True)
        self.assertEqual(result["candidates"][0]["id"], "example/balanced")
        self.assertEqual(result["candidates"][0]["evidence_status"], "benchmark_floor_passed")

    def test_value_returns_frontier_without_dominated_model(self):
        result = self.rank("--objective", "value", evidence=True)
        self.assertEqual([m["id"] for m in result["candidates"]], ["example/budget", "example/balanced", "example/premium"])
        self.assertEqual(result["counts"]["eligible"], 4)
        self.assertEqual(result["counts"]["ranked"], 3)

    def test_equal_price_quality_peers_are_not_strictly_dominated(self):
        self.catalog["response"]["data"][3]["pricing"] = copy.deepcopy(self.catalog["response"]["data"][1]["pricing"])
        self.evidence["models"][3]["score"] = 85
        result = self.rank("--objective", "value", evidence=True)
        self.assertIn("example/dominated", [m["id"] for m in result["candidates"]])

    def test_lower_is_better_quality_and_frontier(self):
        self.evidence["direction"] = "lower"
        self.evidence["models"][0]["score"] = 2
        self.evidence["models"][1]["score"] = 1
        self.evidence["models"][2]["score"] = 3
        self.evidence["models"][3]["score"] = 4
        self.assertEqual(self.rank("--objective", "quality", evidence=True)["candidates"][0]["id"], "example/balanced")
        self.assertEqual([m["id"] for m in self.rank("--objective", "value", evidence=True)["candidates"]], ["example/budget", "example/balanced"])
        with self.assertRaises(finder.FinderError):
            self.rank("--min-score", "1", evidence=True)

    def test_no_fuzzy_identity_matching(self):
        self.evidence["models"][0]["openrouter_id"] = "other/budget"
        result = self.rank("--objective", "quality", evidence=True)
        self.assertNotIn("example/budget", [m["id"] for m in result["candidates"]])
        self.assertEqual(result["excluded_by_reason"]["missing_benchmark"], 1)
        self.assertTrue(any("no fuzzy matching" in warning for warning in result["warnings"]))

    def test_missing_benchmark_is_excluded_by_quality_floor(self):
        self.evidence["models"].pop(0)
        result = self.rank("--min-score", "0", evidence=True)
        self.assertNotIn("example/budget", [m["id"] for m in result["candidates"]])

    def test_newest_uses_catalog_date_and_rejects_unknown(self):
        self.assertEqual(self.rank("--objective", "newest")["candidates"][0]["id"], "example/dominated")
        self.catalog["response"]["data"][3]["created"] = None
        result = self.rank("--objective", "newest")
        self.assertEqual(result["excluded_by_reason"]["unknown_catalog_date"], 1)

    def test_dynamic_aliases_are_preserved_labeled_and_optionally_excluded(self):
        self.catalog["response"]["data"][0]["id"] = "~example/budget-latest"
        result = self.rank()
        self.assertEqual(result["counts"]["malformed"], 0)
        self.assertTrue(result["candidates"][0]["dynamic_alias"])
        self.assertTrue(any("Dynamic aliases" in warning for warning in result["warnings"]))
        result = self.rank("--exclude-aliases")
        self.assertFalse(any(m["dynamic_alias"] for m in result["candidates"]))
        self.assertEqual(result["excluded_by_reason"]["dynamic_alias_excluded"], 1)

    def test_provenance_preserves_old_time_and_marks_missing(self):
        result = self.rank()
        self.assertEqual(result["catalog"]["retrieved_at"], self.catalog["retrieved_at"])
        self.assertTrue(any("older than 24 hours" in w for w in result["warnings"]))
        self.catalog = self.catalog["response"]
        self.assertTrue(any("time unknown" in w for w in self.rank()["warnings"]))

    def test_malformed_entries_are_counted_duplicate_ids_fail(self):
        self.catalog["response"]["data"].extend([None, {"id": "https://example.com/a"}])
        self.assertEqual(self.rank()["counts"]["malformed"], 2)
        self.catalog["response"]["data"].append(self.catalog["response"]["data"][0])
        with self.assertRaises(finder.FinderError):
            self.rank()

    def test_extra_fees_are_exposed_and_token_estimate_not_changed(self):
        self.catalog["response"]["data"][0]["pricing"]["request"] = "0.01"
        model = self.rank()["candidates"][0]
        self.assertEqual(model["additional_pricing"]["request"], "0.01")
        self.assertEqual(model["estimated_request_usd"], Decimal("0.0004"))

    def test_evidence_requires_comparable_metadata_and_unique_id(self):
        for key in ("metric", "version", "configuration", "source_url", "as_of", "direction"):
            evidence = copy.deepcopy(self.evidence)
            evidence.pop(key)
            with self.subTest(key=key), self.assertRaises(finder.FinderError):
                finder.benchmark_evidence(evidence)
        self.evidence["models"].append(self.evidence["models"][0])
        with self.assertRaises(finder.FinderError):
            finder.benchmark_evidence(self.evidence)


class NetworkTests(unittest.TestCase):
    def test_requests_are_get_and_timestamped(self):
        class Response(io.BytesIO):
            pass

        with patch.object(finder, "build_opener") as build:
            build.return_value.open.return_value = Response(b'{"data": []}')
            snapshot = finder.fetch_json(finder.OPENROUTER)
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(snapshot["source_url"], finder.OPENROUTER)
            self.assertIn("retrieved_at", snapshot)

    def test_http_failures_do_not_disclose_key_or_body(self):
        for status in (401, 403, 404, 429, 500):
            with self.subTest(status=status), patch.object(finder, "build_opener") as build:
                build.return_value.open.side_effect = HTTPError("https://private/?key=SECRET", status, "SECRET", {}, io.BytesIO(b"SECRET"))
                with self.assertRaises(finder.FinderError) as error:
                    finder.fetch_json(finder.ARTIFICIAL_ANALYSIS, "SECRET")
                self.assertIn(str(status), str(error.exception))
                self.assertNotIn("SECRET", str(error.exception))

    def test_invalid_response_and_network_failure_are_actionable(self):
        for payload in (b"not-json", b"[]", b'{"error": "no data"}'):
            with patch.object(finder, "build_opener") as build:
                build.return_value.open.return_value = io.BytesIO(payload)
                with self.assertRaises(finder.FinderError):
                    finder.fetch_json(finder.OPENROUTER)
        with patch.object(finder, "build_opener") as build:
            build.return_value.open.side_effect = URLError("SECRET")
            with self.assertRaises(finder.FinderError) as error:
                finder.fetch_json(finder.OPENROUTER)
            self.assertNotIn("SECRET", str(error.exception))

    def test_redirects_are_refused(self):
        with self.assertRaises(finder.FinderError):
            finder.NoRedirects().redirect_request(None, None, 302, "", {}, "https://attacker.invalid")


class BenchmarkFetchTests(unittest.TestCase):
    def options(self, *arguments):
        return finder.parser().parse_args(["benchmarks", *arguments])

    def test_bearer_get_preserves_dataset_metadata_and_keeps_key_out_of_output(self):
        payload = {"data": [{"model_permaslug": "example/revision", "coding_index": 80}],
                   "meta": {"citation": "Synthetic attribution", "source_url": "https://example.com/eval",
                            "as_of": "2026-01-01T00:00:00Z", "version": "demo-1"}}
        with patch.dict(finder.os.environ, {"OPENROUTER_API_KEY": "SECRET"}), patch.object(finder, "build_opener") as build:
            build.return_value.open.return_value = io.BytesIO(json.dumps(payload).encode())
            result = finder.fetch_benchmarks(self.options("--task-type", "coding", "--max-results", "7"))
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_method(), "GET")
            self.assertIsNone(request.data)
            self.assertEqual(request.get_header("Authorization"), "Bearer SECRET")
            self.assertIsNone(request.get_header("X-api-key"))
            self.assertEqual(parse_qs(urlsplit(request.full_url).query),
                             {"source": ["artificial-analysis"], "task_type": ["coding"], "max_results": ["7"]})
            self.assertEqual(result["response"], payload)
            self.assertNotIn("SECRET", json.dumps(result))

    def test_design_arena_filters_are_encoded(self):
        with patch.dict(finder.os.environ, {"OPENROUTER_API_KEY": "SECRET"}), patch.object(finder, "fetch_json") as fetch:
            fetch.return_value = {"response": {"data": [], "meta": {"citation": None}}}
            finder.fetch_benchmarks(self.options("--source", "design-arena", "--arena", "models", "--category", "svg&unexpected=true"))
            url = fetch.call_args.args[0]
            query = parse_qs(urlsplit(url).query)
            self.assertEqual(query["category"], ["svg&unexpected=true"])
            self.assertNotIn("unexpected", query)
            self.assertEqual(query["arena"], ["models"])

    def test_missing_key_does_not_make_a_request(self):
        with patch.dict(finder.os.environ, {}, clear=True), patch.object(finder, "fetch_json") as fetch, contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(finder.main(["benchmarks"]), 1)
            fetch.assert_not_called()
            self.assertIn("regular OpenRouter key", error.getvalue())

    def test_design_filters_on_aa_are_rejected_before_network(self):
        for arguments in (("--arena", "models"), ("--category", "svg")):
            with self.subTest(arguments=arguments), patch.object(finder, "fetch_json") as fetch, self.assertRaises(finder.FinderError):
                finder.fetch_benchmarks(self.options(*arguments))
            fetch.assert_not_called()

    def test_missing_meta_or_wrong_row_shape_fails_explicitly(self):
        for payload in ({"data": []}, {"data": {}, "meta": {}}):
            with self.subTest(payload=payload), patch.dict(finder.os.environ, {"OPENROUTER_API_KEY": "SECRET"}), patch.object(finder, "fetch_json") as fetch:
                fetch.return_value = {"response": payload}
                with self.assertRaises(finder.FinderError):
                    finder.fetch_benchmarks(self.options())

    def test_zero_result_limit_is_a_usage_error(self):
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
            self.options("--max-results", "0")
        self.assertEqual(error.exception.code, 2)

    def test_aa_header_remains_separate_from_openrouter_auth(self):
        with patch.object(finder, "build_opener") as build:
            build.return_value.open.return_value = io.BytesIO(b'{"data": []}')
            finder.fetch_json(finder.ARTIFICIAL_ANALYSIS, api_key="AA-SECRET")
            request = build.return_value.open.call_args.args[0]
            self.assertEqual(request.get_header("X-api-key"), "AA-SECRET")
            self.assertIsNone(request.get_header("Authorization"))


class CLITests(unittest.TestCase):
    def test_offline_end_to_end_json_and_decimal_precision(self):
        result = subprocess.run([sys.executable, str(HELPER), "shortlist", "--catalog", str(ROOT / "examples/catalog.example.json"), "--benchmarks", str(ROOT / "examples/benchmarks.example.json"), "--objective", "value"], capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stderr)
        document = json.loads(result.stdout)
        self.assertEqual(document["counts"]["returned"], 3)
        self.assertEqual(Decimal(document["candidates"][0]["estimated_request_usd"]), Decimal("0.0004"))

    def test_output_path_does_not_mix_stdout_with_json(self):
        with tempfile.TemporaryDirectory() as temp:
            output = Path(temp) / "nested" / "result.json"
            with contextlib.redirect_stdout(io.StringIO()) as stdout:
                code = finder.main(["shortlist", "--catalog", str(ROOT / "examples/catalog.example.json"), "--output", str(output)])
            self.assertEqual(code, 0)
            self.assertEqual(stdout.getvalue(), "")
            self.assertEqual(json.loads(output.read_text())["counts"]["returned"], 4)

    def test_bad_numeric_options_are_usage_errors(self):
        for option, value in (("--input-tokens", "-1"), ("--limit", "0"), ("--requests-per-month", "0"), ("--max-monthly-cost", "NaN")):
            with self.subTest(option=option), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as error:
                finder.parser().parse_args(["shortlist", "--catalog", "unused", option, value])
            self.assertEqual(error.exception.code, 2)

    def test_aa_requires_key_without_network_or_credential_output(self):
        with patch.dict(finder.os.environ, {}, clear=True), patch.object(finder, "fetch_json") as fetch, contextlib.redirect_stderr(io.StringIO()) as error:
            self.assertEqual(finder.main(["fetch", "--source", "artificial-analysis"]), 1)
            fetch.assert_not_called()
            self.assertIn("AA_API_KEY", error.getvalue())

    def test_endpoint_argument_cannot_inject_url_or_query(self):
        for bad_id in ("https://attacker.invalid/a", "example/model?key=secret", "../model", "example/model/extra", "example/model\n"):
            with self.subTest(bad_id=bad_id), patch.object(finder, "fetch_json") as fetch, contextlib.redirect_stderr(io.StringIO()):
                self.assertEqual(finder.main(["endpoints", bad_id]), 1)
                fetch.assert_not_called()

    def test_empty_results_are_success_with_exclusion_evidence(self):
        with contextlib.redirect_stdout(io.StringIO()) as output:
            code = finder.main(["shortlist", "--catalog", str(ROOT / "examples/catalog.example.json"), "--min-context", "99999999"])
        self.assertEqual(code, 0)
        document = json.loads(output.getvalue())
        self.assertEqual(document["candidates"], [])
        self.assertEqual(document["excluded_by_reason"]["context"], 4)


if __name__ == "__main__":
    unittest.main()
