#!/usr/bin/env python3
"""
P4 acceptance tests — wiki stub repair.

Covers four cleanup areas:
1. `_wiki_yaml.py` — consolidated YAML parser. Must match the three legacy
   parsers (post_edit_frontmatter_check.extract_frontmatter,
   refresh_wiki_index.parse_frontmatter, the regex parser inside
   wiki_schema.py) on every key the fixtures declare.
2. `_wiki_http.py` — HEAD/ETag/Last-Modified helper. Must extract a stable
   `{etag, last-modified, content-length, status}` dict from a mock response,
   normalize weak ETags, handle missing headers gracefully, and round-trip
   through the source-summary refresh quick-check tier.
3. Schema migration recipe — `wiki_schema.py migrate 1.0 1.1` must transform
   `source-summary-pre.md` into `source-summary-post.md` byte-identically (modulo
   the new fields). The reverse migration must restore the original.
4. `duplication-vs-data-point` lint — either implements Jaccard detection
   (flagging real duplication on a fixture) OR is cleanly removed from the
   schema/lint registry. The decision lives in the plan-manifest user-approval
   trail; this test asserts the chosen path is consistent.

Until the four components ship, this test fails. P4_008 drives it green.
"""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
FIXTURE_DIR = SCRIPT_DIR / "fixtures" / "wiki_stubs"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _import_yaml_module():
    import _wiki_yaml  # noqa: F401

    return _wiki_yaml


def _import_http_module():
    import _wiki_http  # noqa: F401

    return _wiki_http


class WikiYamlConsolidatedParserTests(unittest.TestCase):
    """The new `_wiki_yaml.py` must match the legacy parsers on every shape."""

    @classmethod
    def setUpClass(cls):
        cls.fixture = FIXTURE_DIR / "yaml-edge-cases.md"
        cls.text = cls.fixture.read_text(encoding="utf-8")

    def test_module_exposes_parse_frontmatter(self):
        wy = _import_yaml_module()
        self.assertTrue(hasattr(wy, "parse_frontmatter"))

    def test_parses_scalar_quoted_and_inline_list(self):
        wy = _import_yaml_module()
        meta = wy.parse_frontmatter(self.text)
        self.assertIsNotNone(meta)
        self.assertEqual(meta["name"], "YAML Edge Cases")
        self.assertEqual(meta["quoted-string"], "value with: colon and #hash")
        self.assertEqual(meta["single-quoted"], "value with [brackets]")
        self.assertEqual(meta["inline-list"], ["a", "b", "c"])
        self.assertEqual(
            meta["inline-list-with-spaces"], ["alpha beta", "gamma delta"]
        )
        self.assertEqual(meta["tags"], ["yaml", "edge-case", "fixture"])

    def test_parses_multi_line_list(self):
        wy = _import_yaml_module()
        meta = wy.parse_frontmatter(self.text)
        self.assertEqual(
            meta["multi-line-list"],
            ["first item", "second item", "third item with: colon"],
        )
        self.assertEqual(
            meta["mixed-case-values"], ["Alpha", "Beta-Gamma", "2026-05-04"]
        )
        self.assertEqual(meta["references"], ["some-other-page", "another-page"])

    def test_empty_value_becomes_empty_list_or_none(self):
        wy = _import_yaml_module()
        meta = wy.parse_frontmatter(self.text)
        # `empty-value:` with no continuation: parser should produce something
        # falsy and not raise.
        value = meta.get("empty-value")
        self.assertIn(value, ("", [], None))

    def test_empty_scalar_followed_by_scalar_key_stays_empty_string(self):
        """The audit's targeted probe: parsing
            etag:
            last-modified:
            name: X
        must produce {'etag': '', 'last-modified': '', 'name': 'X'}, NOT
        {'etag': [], 'last-modified': [], 'name': 'X'}.

        This guards the source-summary HTTP-signal fields from being
        silently turned into empty lists by the pending-key flush.
        """
        wy = _import_yaml_module()
        text = "---\netag:\nlast-modified:\nname: X\n---\n"
        meta = wy.parse_frontmatter(text)
        self.assertIsNotNone(meta)
        self.assertEqual(
            meta.get("etag"), "",
            f"etag must remain empty string, got {meta.get('etag')!r}",
        )
        self.assertEqual(
            meta.get("last-modified"), "",
            f"last-modified must remain empty string, got {meta.get('last-modified')!r}",
        )
        self.assertEqual(meta.get("name"), "X")

    def test_emit_round_trip_preserves_known_fields(self):
        """Parse then emit then re-parse must be idempotent on the supported shapes."""
        wy = _import_yaml_module()
        if not hasattr(wy, "emit_frontmatter"):
            self.skipTest("emit_frontmatter not implemented yet")
        meta = wy.parse_frontmatter(self.text)
        emitted = wy.emit_frontmatter(meta)
        round_trip = wy.parse_frontmatter(f"---\n{emitted}\n---\n")
        self.assertEqual(meta["name"], round_trip["name"])
        self.assertEqual(meta["inline-list"], round_trip["inline-list"])
        self.assertEqual(meta["multi-line-list"], round_trip["multi-line-list"])

    def test_legacy_parser_equivalence_for_required_keys(self):
        """On the edge-case fixture, every legacy parser must agree with the new one
        on the keys the fixture declares (where the legacy parser supports them)."""
        wy = _import_yaml_module()
        new_meta = wy.parse_frontmatter(self.text)

        # Legacy parser 1: hook
        sys.path.insert(0, str(REPO_ROOT / ".claude" / "hooks"))
        try:
            import post_edit_frontmatter_check as hook  # type: ignore

            hook_meta = hook.extract_frontmatter(str(self.fixture))
        finally:
            sys.path.pop(0)

        self.assertIsNotNone(hook_meta)
        for key in ("name", "type", "page-type", "cluster", "version", "status"):
            self.assertEqual(
                new_meta.get(key),
                hook_meta.get(key),
                f"legacy hook parser disagreed on key {key!r}: "
                f"new={new_meta.get(key)!r} legacy={hook_meta.get(key)!r}",
            )
        # Both parsers must produce the same multi-line list shape
        self.assertEqual(new_meta.get("references"), hook_meta.get("references"))
        self.assertEqual(new_meta.get("multi-line-list"), hook_meta.get("multi-line-list"))

        # Legacy parser 2: refresh_wiki_index
        import refresh_wiki_index  # type: ignore

        refresh_meta = refresh_wiki_index.parse_frontmatter(self.fixture)
        self.assertIsNotNone(refresh_meta)
        self.assertEqual(new_meta.get("name"), refresh_meta.get("name"))
        self.assertEqual(new_meta.get("type"), refresh_meta.get("type"))


class WikiHttpHeadCheckTests(unittest.TestCase):
    """`_wiki_http.head_check` plus the quick-check tier that consumes it."""

    @classmethod
    def setUpClass(cls):
        cls.head_fixture = json.loads(
            (FIXTURE_DIR / "head-response.json").read_text(encoding="utf-8")
        )

    def test_module_exposes_head_check_and_compare(self):
        wh = _import_http_module()
        self.assertTrue(hasattr(wh, "extract_head_signals"))
        self.assertTrue(hasattr(wh, "head_signals_unchanged"))

    def test_extracts_strong_etag_and_last_modified(self):
        wh = _import_http_module()
        signals = wh.extract_head_signals(self.head_fixture["headers"])
        self.assertEqual(signals["etag"], '"abc123-def456"')
        self.assertEqual(signals["last-modified"], "Mon, 04 May 2026 10:00:00 GMT")
        self.assertEqual(signals["content-length"], 12345)

    def test_normalizes_weak_etag_for_comparison(self):
        wh = _import_http_module()
        weak = wh.extract_head_signals(self.head_fixture["weak_etag_variant"])
        strong = wh.extract_head_signals(self.head_fixture["headers"])
        # Quick-check tier compares on canonical form; strong vs weak of the
        # same value should still register as "unchanged" when validators
        # otherwise match.
        self.assertTrue(
            wh.head_signals_unchanged(stored=strong, fresh=weak)
            or wh.head_signals_unchanged(stored=weak, fresh=strong),
            f"weak↔strong ETag of same value should match; got strong={strong!r} weak={weak!r}",
        )

    def test_handles_missing_headers_gracefully(self):
        wh = _import_http_module()
        signals = wh.extract_head_signals(self.head_fixture["missing_headers_variant"])
        self.assertIsNone(signals.get("etag"))
        self.assertIsNone(signals.get("last-modified"))
        # No crash; helper returns None for absent fields.

    def test_unchanged_compare_returns_true_for_identical_signals(self):
        wh = _import_http_module()
        a = wh.extract_head_signals(self.head_fixture["headers"])
        b = wh.extract_head_signals(self.head_fixture["headers"])
        self.assertTrue(wh.head_signals_unchanged(stored=a, fresh=b))

    def test_unchanged_compare_returns_false_when_etag_changes(self):
        wh = _import_http_module()
        a = wh.extract_head_signals(self.head_fixture["headers"])
        changed = dict(self.head_fixture["headers"])
        changed["ETag"] = '"different-etag-value"'
        b = wh.extract_head_signals(changed)
        self.assertFalse(wh.head_signals_unchanged(stored=a, fresh=b))

    def test_head_quick_check_does_not_consult_content_hash(self):
        """The audit's targeted probe: stored content-hash must not influence
        head_signals_unchanged. A body hash comes from the body, not from a
        HEAD response — it belongs to the full-tier validator.
        """
        wh = _import_http_module()
        stored = wh.extract_head_signals(self.head_fixture["headers"])
        stored["content-hash"] = "deadbeefcafe1234"
        fresh = wh.extract_head_signals(self.head_fixture["headers"])
        # Same matching ETag/Last-Modified → unchanged, regardless of any
        # content-hash key the caller may have stuffed into the dicts.
        self.assertTrue(wh.head_signals_unchanged(stored=stored, fresh=fresh))
        # Drift the content-hash to a different value — must NOT affect the
        # HEAD-tier verdict.
        stored2 = dict(stored)
        stored2["content-hash"] = "0000000000000000"
        self.assertTrue(wh.head_signals_unchanged(stored=stored2, fresh=fresh))

    def test_body_content_unchanged_compares_real_body(self):
        """The full-tier validator must hash the actual body and compare it
        to the stored content-hash. Returns False when either side is missing.
        """
        wh = _import_http_module()
        body = b"# Sample body\n\nSome content here.\n"
        stored = wh.compute_body_hash(body)
        self.assertTrue(wh.body_content_unchanged(stored_hash=stored, fresh_body=body))
        self.assertFalse(
            wh.body_content_unchanged(stored_hash=stored, fresh_body=b"different bytes")
        )
        self.assertFalse(wh.body_content_unchanged(stored_hash=None, fresh_body=body))
        self.assertFalse(wh.body_content_unchanged(stored_hash=stored, fresh_body=None))


class WikiSchemaMigration1To11Tests(unittest.TestCase):
    """`wiki_schema.py migrate 1.0 1.1` must run a real, reversible migration."""

    def test_migrate_dry_run_succeeds_on_fixture(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            self._scaffold_wiki(tmp_root, FIXTURE_DIR / "source-summary-pre.md")
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "wiki_schema.py"),
                    "--root",
                    str(tmp_root),
                    "migrate",
                    "1.0",
                    "1.1",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"migrate 1.0→1.1 dry-run failed: stdout={result.stdout!r} stderr={result.stderr!r}",
            )

    def test_migrate_1_to_11_adds_etag_last_modified_content_hash(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = self._scaffold_wiki(
                tmp_root, FIXTURE_DIR / "source-summary-pre.md"
            )
            result = subprocess.run(
                [
                    sys.executable,
                    str(SCRIPT_DIR / "wiki_schema.py"),
                    "--root",
                    str(tmp_root),
                    "migrate",
                    "1.0",
                    "1.1",
                    "--apply",
                ],
                capture_output=True,
                text=True,
            )
            self.assertEqual(
                result.returncode,
                0,
                f"migrate --apply failed: {result.stderr}",
            )
            text = target.read_text(encoding="utf-8")
            self.assertIn("etag:", text, "etag field not added by migration")
            self.assertIn("last-modified:", text, "last-modified field not added by migration")
            self.assertIn("content-hash:", text, "content-hash field not added by migration")
            self.assertIn(
                "schema-version: 1.1", text, "schema-version not bumped to 1.1"
            )

    def test_migrate_round_trip_is_reversible(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_root = Path(tmp)
            target = self._scaffold_wiki(
                tmp_root, FIXTURE_DIR / "source-summary-pre.md"
            )
            original_text = target.read_text(encoding="utf-8")

            for from_v, to_v in (("1.0", "1.1"), ("1.1", "1.0")):
                result = subprocess.run(
                    [
                        sys.executable,
                        str(SCRIPT_DIR / "wiki_schema.py"),
                        "--root",
                        str(tmp_root),
                        "migrate",
                        from_v,
                        to_v,
                        "--apply",
                    ],
                    capture_output=True,
                    text=True,
                )
                self.assertEqual(
                    result.returncode,
                    0,
                    f"migrate {from_v}→{to_v} failed: {result.stderr}",
                )

            after_round_trip = target.read_text(encoding="utf-8")
            self.assertEqual(
                original_text,
                after_round_trip,
                "1.0→1.1→1.0 is not byte-identical to the pre-migration source",
            )

    @staticmethod
    def _scaffold_wiki(root: Path, page_src: Path) -> Path:
        """Build a minimal docs/_wiki/ tree under `root` for migration testing."""
        wiki = root / "docs" / "_wiki"
        (wiki / "source-summary").mkdir(parents=True, exist_ok=True)
        (wiki / ".config.yml").write_text(
            "wiki:\n  schema-version: 1.0\n", encoding="utf-8"
        )
        # Copy the schema template so `wiki_schema.py` has something to load.
        schema_src = REPO_ROOT / "docs" / "_bcos-framework" / "templates" / "_wiki.schema.yml.tmpl"
        if schema_src.is_file():
            (wiki / ".schema.yml").write_text(
                schema_src.read_text(encoding="utf-8"), encoding="utf-8"
            )
        target = wiki / "source-summary" / page_src.name
        shutil.copy(page_src, target)
        return target


class WikiDuplicationLintDecisionTests(unittest.TestCase):
    """Either implement Jaccard, or cleanly remove the lint id from the registry.

    The chosen path is recorded in the plan-manifest user-approval conditions
    (P4_007). This test refuses to allow a phantom: if `_wiki_lint.py` exists,
    Jaccard must be wired and exercised; if it doesn't, the schema/lint surface
    must not advertise the check.
    """

    def test_either_lint_module_exists_or_check_id_is_absent(self):
        lint_module = SCRIPT_DIR / "_wiki_lint.py"
        lint_doc = REPO_ROOT / ".claude" / "skills" / "bcos-wiki" / "lint.md"
        if lint_module.is_file():
            text = lint_module.read_text(encoding="utf-8")
            self.assertIn(
                "jaccard", text.lower(),
                "_wiki_lint.py exists but does not mention Jaccard — phantom impl",
            )
            return

        # Otherwise the lint id must be absent from lint.md and the schema template
        # to avoid documenting a check that does not run.
        if lint_doc.is_file():
            self.assertNotIn(
                "duplication-vs-data-point",
                lint_doc.read_text(encoding="utf-8"),
                "Lint id `duplication-vs-data-point` is documented but no impl exists. "
                "Either ship _wiki_lint.py with Jaccard, or remove the id from lint.md.",
            )

    def test_jaccard_helper_returns_known_value(self):
        import _wiki_lint

        self.assertEqual(_wiki_lint.jaccard({"a", "b", "c"}, {"a", "b"}), 2 / 3)
        self.assertEqual(_wiki_lint.jaccard(set(), set()), 0.0)
        self.assertEqual(_wiki_lint.jaccard({"a"}, {"b"}), 0.0)

    def test_paragraph_tokens_filters_stopwords_and_short_tokens(self):
        import _wiki_lint

        tokens = _wiki_lint.paragraph_tokens(
            "The pricing tier defines our subscription billing model"
        )
        # Stopwords like "the", "our" must be excluded; tokens are lowercased.
        self.assertNotIn("the", tokens)
        self.assertNotIn("our", tokens)
        self.assertIn("pricing", tokens)
        self.assertIn("subscription", tokens)
        self.assertIn("billing", tokens)

    def test_detect_duplication_flags_obvious_restatement(self):
        """When a wiki paragraph restates a data-point paragraph, Jaccard ≥ threshold."""
        import _wiki_lint

        target = (
            "# Pricing\n\nWe offer three subscription tiers (Starter, Pro, Enterprise) "
            "billed monthly through Stripe. Each tier unlocks specific feature sets "
            "and seat allowances; Enterprise includes SAML SSO and priority support.\n"
        )
        wiki_restatement = (
            "# Pricing How-to\n\nThree subscription tiers exist (Starter, Pro, Enterprise) "
            "billed monthly through Stripe. Each tier unlocks specific feature sets "
            "and seat allowances. Enterprise includes SAML SSO and priority support.\n"
        )
        findings = _wiki_lint.detect_duplication(wiki_restatement, target, threshold=0.5)
        self.assertGreaterEqual(
            len(findings), 1,
            "Jaccard must flag near-verbatim restatement",
        )
        self.assertGreaterEqual(findings[0].score, 0.5)

    def test_detect_duplication_does_not_flag_unrelated_content(self):
        """Different topics with no shared vocabulary must not produce findings."""
        import _wiki_lint

        target = "# Pricing\n\nSubscription tiers and billing through Stripe.\n"
        unrelated = (
            "# LinkedIn Tone\n\nVoice rules for LinkedIn posts: short sentences, "
            "active verbs, no jargon, no superlatives, audience-first framing.\n"
        )
        findings = _wiki_lint.detect_duplication(unrelated, target, threshold=0.5)
        self.assertEqual(findings, [], "unrelated content must not trigger Jaccard findings")


if __name__ == "__main__":
    unittest.main(verbosity=2)
