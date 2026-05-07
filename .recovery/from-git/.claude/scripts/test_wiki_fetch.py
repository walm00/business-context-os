#!/usr/bin/env python3
"""
P3 acceptance tests — sub-agent isolation for big-body wiki work.

Covers four mechanical surfaces:
1. `wiki-fetch` agent definition exists with the documented input/output contract.
2. Wiring docs (`run.md`, `refresh.md`, `promote.md`, `create.md`) explicitly
   dispatch via the Task tool to `wiki-fetch` rather than inline-fetching the
   body in main.
3. `_wiki_fetch_contract.py` validates the canonical result shape and rejects
   malformed or oversized variants.
4. `_wiki_budget.py` returns the right serialize-or-parallel decision per the
   cumulative budget rule (parallel ≤ 80% of main-context limit; otherwise
   serial).

End-to-end "main context never holds full HTML" lives in conversation logs;
this Python harness asserts the wiring discipline and the result contract,
which together prevent the regression mechanically.

Until the four components ship, this test fails. P3_008 drives it green.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
FIXTURE_DIR = SCRIPT_DIR / "fixtures" / "wiki_fetch"
AGENT_PATH = REPO_ROOT / ".claude" / "agents" / "wiki-fetch" / "AGENT.md"
WIKI_SKILL_DIR = REPO_ROOT / ".claude" / "skills" / "bcos-wiki"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _import_contract_module():
    import _wiki_fetch_contract  # noqa: F401

    return _wiki_fetch_contract


def _import_budget_module():
    import _wiki_budget  # noqa: F401

    return _wiki_budget


class WikiFetchAgentDefinitionTests(unittest.TestCase):
    """The agent-definition file must exist and declare the documented contract."""

    def test_agent_md_exists(self):
        self.assertTrue(
            AGENT_PATH.is_file(),
            f"Sub-agent definition missing: {AGENT_PATH}",
        )

    def test_agent_md_declares_input_kinds(self):
        text = AGENT_PATH.read_text(encoding="utf-8")
        # Every documented input kind must appear in the agent contract.
        for kind in ("web", "github", "youtube", "pdf", "docx", "local"):
            self.assertIn(
                f"`{kind}`",
                text,
                f"Agent contract missing input kind {kind!r}",
            )

    def test_agent_md_declares_output_fields(self):
        text = AGENT_PATH.read_text(encoding="utf-8")
        for field in (
            "title",
            "h2-outline",
            "key-sentences",
            "suggested-page-type",
            "suggested-cluster",
            "raw-file-pointer",
            "citation-banner-fields",
        ):
            self.assertIn(field, text, f"Agent contract missing output field {field!r}")

    def test_agent_md_declares_4000_token_cap(self):
        text = AGENT_PATH.read_text(encoding="utf-8")
        self.assertIn(
            "4000",
            text,
            "Agent contract must declare the 4000-token result cap",
        )


class WikiFetchSkillDispatchWiringTests(unittest.TestCase):
    """run.md, refresh.md, promote.md, create.md must dispatch via Task → wiki-fetch."""

    def _load(self, name: str) -> str:
        path = WIKI_SKILL_DIR / name
        self.assertTrue(path.is_file(), f"missing dispatch doc: {path}")
        return path.read_text(encoding="utf-8")

    def test_run_md_dispatches_via_task_tool(self):
        text = self._load("run.md")
        self.assertIn(
            "wiki-fetch",
            text,
            "run.md must reference the wiki-fetch sub-agent",
        )
        self.assertIn(
            "Task",
            text,
            "run.md must reference the Task tool (sub-agent dispatch)",
        )

    def test_refresh_md_dispatches_via_task_tool(self):
        text = self._load("refresh.md")
        self.assertIn("wiki-fetch", text)
        self.assertIn("Task", text)

    def test_promote_md_dispatches_via_task_tool(self):
        text = self._load("promote.md")
        self.assertIn("wiki-fetch", text)
        self.assertIn("Task", text)

    def test_create_md_dispatches_via_task_tool(self):
        text = self._load("create.md")
        self.assertIn("wiki-fetch", text)
        self.assertIn("Task", text)

    def test_wiring_explicitly_forbids_inline_fetch(self):
        """run.md must explicitly say "do not fetch inline" or equivalent —
        the rule preserves the isolation contract even after wiring drift."""
        text = self._load("run.md")
        markers = ("do not fetch inline", "never inline", "no inline fetch", "main thread never")
        self.assertTrue(
            any(marker in text.lower() for marker in markers),
            "run.md must contain an explicit anti-inline-fetch rule",
        )


class WikiFetchContractValidatorTests(unittest.TestCase):
    """`_wiki_fetch_contract.validate_result` enforces the documented shape."""

    @classmethod
    def setUpClass(cls):
        cls.fixtures = json.loads(
            (FIXTURE_DIR / "expected-result.json").read_text(encoding="utf-8")
        )
        cls.cm = _import_contract_module()

    def test_validates_canonical_result(self):
        ok, errors = self.cm.validate_result(self.fixtures["valid_canonical"])
        self.assertTrue(ok, f"canonical result rejected: {errors!r}")
        self.assertEqual(errors, [])

    def test_validates_error_result(self):
        ok, errors = self.cm.validate_result(self.fixtures["valid_with_error"])
        self.assertTrue(ok, f"error-shaped result rejected: {errors!r}")

    def test_rejects_missing_required_field(self):
        ok, errors = self.cm.validate_result(
            self.fixtures["invalid_missing_required_field"]
        )
        self.assertFalse(ok, "missing field must be rejected")
        self.assertGreater(len(errors), 0)

    def test_rejects_object_h2_outline_entries(self):
        """The audit's targeted probe: dict items inside h2-outline must be rejected."""
        result = dict(self.fixtures["valid_canonical"])
        result["h2-outline"] = [{"not": "a string"}, "Authentication"]
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "list with non-string items must be rejected")
        self.assertTrue(any("h2-outline[0]" in e for e in errors), errors)

    def test_rejects_numeric_suggested_page_type(self):
        result = dict(self.fixtures["valid_canonical"])
        result["suggested-page-type"] = 42
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "numeric suggested-page-type must be rejected")
        self.assertTrue(any("suggested-page-type" in e for e in errors), errors)

    def test_rejects_list_suggested_cluster(self):
        result = dict(self.fixtures["valid_canonical"])
        result["suggested-cluster"] = ["Revenue", "Marketing"]
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "list suggested-cluster must be rejected")

    def test_rejects_dict_raw_file_pointer(self):
        result = dict(self.fixtures["valid_canonical"])
        result["raw-file-pointer"] = {"path": "_wiki/raw/web/foo.md"}
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "dict raw-file-pointer must be rejected")

    def test_rejects_citation_banner_missing_subfields(self):
        result = dict(self.fixtures["valid_canonical"])
        result["citation-banner-fields"] = {"source-url": "https://example.com"}
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "citation banner missing required subfields must be rejected")
        self.assertTrue(
            any("last-fetched" in e or "detail-level" in e or "provenance" in e for e in errors),
            errors,
        )

    def test_rejects_provenance_missing_kind(self):
        result = dict(self.fixtures["valid_canonical"])
        banner = dict(result["citation-banner-fields"])
        banner["provenance"] = {"fetched-at": "2026-05-04T12:00:00Z"}  # missing kind
        result["citation-banner-fields"] = banner
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok)
        self.assertTrue(any("provenance" in e and "kind" in e for e in errors), errors)

    def test_rejects_invalid_detail_level(self):
        result = dict(self.fixtures["valid_canonical"])
        banner = dict(result["citation-banner-fields"])
        banner["detail-level"] = "exhaustive"  # not in allowed set
        result["citation-banner-fields"] = banner
        ok, errors = self.cm.validate_result(result)
        self.assertFalse(ok, "invalid detail-level must be rejected")

    def test_rejects_oversized_result(self):
        # Inflate one sentence to ~5000 tokens worth of chars
        oversized = dict(self.fixtures["valid_canonical"])
        oversized["key-sentences"] = ["x " * 12000]  # ~24k chars ≈ 6k tokens
        ok, errors = self.cm.validate_result(oversized, max_tokens=4000)
        self.assertFalse(ok, "oversized result must be rejected (>4000 tokens)")

    def test_rejects_result_carrying_full_url_body(self):
        """Scale test: if a regression ever made wiki-fetch return the raw URL
        body inside its result, the validator must reject it.

        Builds a synthetic ~100k-token body in-memory (no committed fixture
        bytes) and attempts to embed it into a wiki-fetch result. The
        validator must reject this as oversized — the proof that the
        4000-token cap is real, not aspirational.
        """
        body = self._synthesize_url_body(approx_tokens=100_000)
        approx_tokens = len(body) // 4
        self.assertGreater(
            approx_tokens, 50_000,
            f"synthesized body too small to test the cap: ~{approx_tokens} tokens",
        )

        regressed_result = dict(self.fixtures["valid_canonical"])
        regressed_result["key-sentences"] = [body]  # the regression: full body in result
        ok, errors = self.cm.validate_result(regressed_result, max_tokens=4000)
        self.assertFalse(
            ok,
            "Validator must reject a wiki-fetch result that smuggles the full URL body",
        )
        self.assertTrue(
            any("token cap" in e for e in errors),
            f"errors must mention the token cap; got {errors!r}",
        )

    @staticmethod
    def _synthesize_url_body(*, approx_tokens: int) -> str:
        """Build a deterministic synthetic body sized to ~approx_tokens.

        Generated at test time, never written to disk. ~4 chars per token.
        """
        chunk = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. "
        # chunk is ~57 chars / ~14 tokens. Repeat enough times to hit the target.
        repeats = (approx_tokens // 14) + 1
        return ("# Synthetic body\n\n" + chunk * repeats)


class WikiFetchCumulativeBudgetTests(unittest.TestCase):
    """`_wiki_budget.decide_dispatch_strategy` returns parallel or serial."""

    @classmethod
    def setUpClass(cls):
        cls.cases = json.loads(
            (FIXTURE_DIR / "cumulative-budget-cases.json").read_text(encoding="utf-8")
        )["cases"]
        cls.bm = _import_budget_module()

    def test_each_fixture_case(self):
        for case in self.cases:
            decision = self.bm.decide_dispatch_strategy(
                n_invocations=case["n"],
                projected_tokens_per_result=case["projected_tokens_per_result"],
                max_main_context=case["max_main_context"],
            )
            self.assertEqual(
                decision.strategy,
                case["expected_decision"],
                f"case {case['name']!r}: expected {case['expected_decision']!r}, "
                f"got {decision.strategy!r} (cumulative={decision.cumulative_tokens})",
            )
            self.assertEqual(
                decision.cumulative_tokens,
                case["expected_cumulative"],
                f"case {case['name']!r}: cumulative tokens mismatch",
            )

    def test_decision_carries_threshold(self):
        decision = self.bm.decide_dispatch_strategy(
            n_invocations=2,
            projected_tokens_per_result=1000,
            max_main_context=10000,
        )
        self.assertGreater(decision.threshold_tokens, 0)
        self.assertLess(decision.threshold_tokens, decision.max_main_context)

    def test_serial_decision_carries_concrete_batch_plan(self):
        """The audit's gap: serial without batch size leaves operator guessing.

        For N=10 over-budget → the Decision must carry max_parallel_batch_size
        AND a concrete `batches` plan that respects it. Caller iterates;
        no manual chunking.
        """
        decision = self.bm.decide_dispatch_strategy(
            n_invocations=10,
            projected_tokens_per_result=20000,
            max_main_context=200_000,
        )
        self.assertEqual(decision.strategy, "serial")
        # threshold = 160000, batch_size = floor(160000/20000) = 8
        self.assertEqual(decision.max_parallel_batch_size, 8)
        # batches: (0..7), (8..9) — flatten must equal range(10)
        self.assertEqual(len(decision.batches), 2)
        flattened = [idx for batch in decision.batches for idx in batch]
        self.assertEqual(flattened, list(range(10)))
        # First batch must fit under threshold
        first = decision.batches[0]
        self.assertLessEqual(
            len(first) * decision.projected_tokens_per_result,
            decision.threshold_tokens,
        )

    def test_parallel_decision_returns_single_batch(self):
        decision = self.bm.decide_dispatch_strategy(
            n_invocations=3,
            projected_tokens_per_result=4000,
            max_main_context=200_000,
        )
        self.assertEqual(decision.strategy, "parallel")
        self.assertEqual(decision.batches, ((0, 1, 2),))

    def test_zero_invocations_returns_empty_batch_plan(self):
        decision = self.bm.decide_dispatch_strategy(
            n_invocations=0,
            projected_tokens_per_result=4000,
            max_main_context=200_000,
        )
        self.assertEqual(decision.batches, ())
        self.assertEqual(decision.cumulative_tokens, 0)


if __name__ == "__main__":
    unittest.main(verbosity=2)
