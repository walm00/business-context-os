#!/usr/bin/env python3
"""
P5 acceptance tests — task-driven cross-zone routing.

Asserts the bundle resolver contract:
- Loads a profile catalog from `_context.task-profiles.yml.tmpl` (or per-repo
  override) via `load_task_profiles`.
- Validates profiles against the documented schema via `validate_task_profiles`.
- Resolves a bundle for a given profile against a `context-index.json`
  corpus via `context_bundle.resolve_bundle()`.
- Returns the documented envelope: profile-id, generated-at, by-zone,
  by-family, freshness, source-of-truth-conflicts, missing-perspectives,
  traversal-hops, unsatisfied-zone-requirements, escalations.
- Source-of-truth conflicts: hits sharing ≥1 `exclusively_owns` key across
  different zones surface in `source-of-truth-conflicts`, with `chosen` set
  per the profile's `source-of-truth-ranking`.
- Coverage gaps: families with `min-count` unmet appear in
  `missing-perspectives`.
- Traversal: `builds-on` edges are walked to depth-cap; hops appear in
  `traversal-hops`.
- Determinism: same fixture → byte-identical bundle (modulo `generated-at`).
- D-10 strict: default mechanical run never escalates; `--resolve-conflicts`
  and `--verify-coverage` are explicit opt-in only.

Until `context_bundle.py` ships, this test fails. P5_011 drives it green.
"""

from __future__ import annotations

import json
import sys
import unittest
from pathlib import Path

SCRIPT_DIR = Path(__file__).resolve().parent
REPO_ROOT = SCRIPT_DIR.parents[1]
FIXTURE_ROOT = SCRIPT_DIR / "fixtures" / "context_bundle"
FIXTURE_PROFILES = FIXTURE_ROOT / "profiles.yml"

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))


def _import_bundle_module():
    import context_bundle  # noqa: F401

    return context_bundle


def _import_profiles_loader():
    import load_task_profiles  # noqa: F401

    return load_task_profiles


def _import_profiles_validator():
    import validate_task_profiles  # noqa: F401

    return validate_task_profiles


def _build_fixture_index() -> dict:
    from context_index import build_context_index

    return build_context_index(FIXTURE_ROOT)


def _load_fixture_profiles() -> list[dict]:
    ltp = _import_profiles_loader()
    return ltp.load_task_profiles(FIXTURE_PROFILES)


class TaskProfileLoaderTests(unittest.TestCase):
    def test_loader_returns_list_of_dicts(self):
        profiles = _load_fixture_profiles()
        self.assertIsInstance(profiles, list)
        self.assertGreater(len(profiles), 0)
        for p in profiles:
            self.assertIsInstance(p, dict)
            self.assertIn("id", p)

    def test_required_zones_normalised(self):
        profiles = _load_fixture_profiles()
        market = next(p for p in profiles if p["id"] == "market-report:write")
        zones = market.get("required-zones") or []
        self.assertGreater(len(zones), 0)
        # Each entry must expose .id and .required (boolean)
        for z in zones:
            self.assertIn("id", z)
            self.assertIn("required", z)
            self.assertIn(z["required"], (True, False))


class TaskProfileLoaderStrictTests(unittest.TestCase):
    """Audit gap: malformed values used to silently coerce to permissive defaults."""

    def test_typo_in_required_zone_flag_raises(self):
        from load_task_profiles import _parse_required_zones, TaskProfilesError

        with self.assertRaises(TaskProfilesError) as cm:
            _parse_required_zones("[active=treu]", profile_id="probe")
        self.assertIn("treu", str(cm.exception))

    def test_typo_in_freshness_threshold_raises(self):
        from load_task_profiles import _parse_freshness_thresholds, TaskProfilesError

        with self.assertRaises(TaskProfilesError):
            _parse_freshness_thresholds("[active=thirty]", profile_id="probe")

    def test_typo_in_coverage_min_count_raises(self):
        from load_task_profiles import _parse_coverage_assertions, TaskProfilesError

        with self.assertRaises(TaskProfilesError):
            _parse_coverage_assertions("[competitor-data=one]", profile_id="probe")

    def test_typo_in_traversal_depth_cap_raises(self):
        from load_task_profiles import _parse_traversal_hints, TaskProfilesError

        with self.assertRaises(TaskProfilesError):
            _parse_traversal_hints("[from-edge=builds-on, depth-cap=lots]", profile_id="probe")

    def test_negative_freshness_threshold_raises(self):
        from load_task_profiles import _parse_freshness_thresholds, TaskProfilesError

        with self.assertRaises(TaskProfilesError):
            _parse_freshness_thresholds("[active=-5]", profile_id="probe")

    def test_valid_values_still_parse(self):
        """Strictness must NOT reject legitimate values."""
        from load_task_profiles import (
            _parse_required_zones,
            _parse_freshness_thresholds,
            _parse_coverage_assertions,
            _parse_traversal_hints,
        )

        zones = _parse_required_zones("[active=true, wiki=False]", profile_id="probe")
        self.assertEqual(zones[0]["required"], True)
        self.assertEqual(zones[1]["required"], False)

        thresh = _parse_freshness_thresholds("[active=30, wiki=never]", profile_id="probe")
        self.assertEqual(thresh, {"active": 30, "wiki": None})

        cov = _parse_coverage_assertions("[fam=2]", profile_id="probe")
        self.assertEqual(cov, {"fam": 2})

        hints = _parse_traversal_hints("[from-edge=builds-on, depth-cap=2]", profile_id="probe")
        self.assertEqual(hints, [{"from-edge": "builds-on", "depth-cap": 2}])


class TaskProfileValidatorTests(unittest.TestCase):
    def test_valid_profiles_pass(self):
        vtp = _import_profiles_validator()
        profiles = _load_fixture_profiles()
        ok, errors = vtp.validate_profiles(profiles)
        self.assertTrue(ok, f"valid fixture profiles rejected: {errors!r}")

    def test_validator_rejects_unknown_zone(self):
        vtp = _import_profiles_validator()
        bad = [{
            "id": "broken:profile",
            "description": "x",
            "required-zones": [{"id": "totally-fake-zone", "required": True}],
            "content-families": [],
            "source-of-truth-ranking": ["totally-fake-zone"],
            "freshness-thresholds": {},
            "traversal-hints": [],
            "coverage-assertions": [],
        }]
        ok, errors = vtp.validate_profiles(bad)
        self.assertFalse(ok)
        self.assertTrue(any("totally-fake-zone" in e for e in errors), errors)

    def test_validator_rejects_missing_id(self):
        vtp = _import_profiles_validator()
        bad = [{"description": "no id"}]
        ok, errors = vtp.validate_profiles(bad)
        self.assertFalse(ok)
        self.assertTrue(any("id" in e for e in errors), errors)


class BundleResolverPoolFilterTests(unittest.TestCase):
    """The audit's gap: optional zones used to dump every doc into the pool."""

    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_unrelated_planned_doc_excluded(self):
        """`_planned/unrelated-redesign.md` matches no market-report family —
        must NOT appear in the bundle even though `planned` is a declared zone."""
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        all_paths: set[str] = set()
        for hits in bundle["by-zone"].values():
            all_paths.update(h.get("path") for h in hits)
        self.assertNotIn(
            "docs/_planned/unrelated-redesign.md",
            all_paths,
            "doc that matches no family must be excluded from the bundle",
        )

    def test_matching_planned_doc_included(self):
        """`_planned/pricing-redesign.md` matches `pricing-data` (cluster=Revenue) —
        MUST still appear (it's the conflict candidate)."""
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        planned_paths = {h.get("path") for h in bundle["by-zone"].get("planned", [])}
        self.assertIn("docs/_planned/pricing-redesign.md", planned_paths)


class BundleResolverEnvelopeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_envelope_contains_required_keys(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        for key in (
            "profile-id",
            "generated-at",
            "by-zone",
            "by-family",
            "freshness",
            "source-of-truth-conflicts",
            "missing-perspectives",
            "traversal-hops",
            "unsatisfied-zone-requirements",
            "escalations",
        ):
            self.assertIn(key, bundle, f"bundle missing envelope key {key!r}")

    def test_by_zone_groups_hits_correctly(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        zones = bundle["by-zone"]
        self.assertIn("active", zones)
        active_paths = {h.get("path") for h in zones["active"]}
        self.assertIn("docs/pricing.md", active_paths)
        self.assertIn("docs/competitors.md", active_paths)


class BundleResolverConflictTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_conflict_detected_on_overlapping_exclusively_owns(self):
        """`pricing.md` (active) and `pricing-redesign.md` (planned) share
        `tier-names` + `pricing-page-copy` in EXCLUSIVELY_OWNS — that's a
        cross-zone CLEAR violation the resolver must flag."""
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        conflicts = bundle["source-of-truth-conflicts"]
        self.assertGreaterEqual(len(conflicts), 1, f"expected conflict; got {conflicts!r}")
        first = conflicts[0]
        self.assertIn("candidates", first)
        candidate_paths = {c["path"] for c in first["candidates"]}
        self.assertEqual(
            candidate_paths,
            {"docs/pricing.md", "docs/_planned/pricing-redesign.md"},
        )

    def test_conflict_resolution_picks_canonical_zone(self):
        """Profile ranks `active` above `planned`, so canonical wins."""
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        first = bundle["source-of-truth-conflicts"][0]
        self.assertEqual(first["resolution"], "docs/pricing.md")
        self.assertEqual(first["resolved-by"], "rank")


class BundleResolverFreshnessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_freshness_verdict_per_hit(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        verdicts = {f["path"]: f["verdict"] for f in bundle["freshness"]}
        # `competitors.md` was last-updated 2026-02-15; threshold for active
        # is 30 days. Anything past 30 days is past-threshold (assuming
        # today >= 2026-03-17).
        self.assertIn("docs/competitors.md", verdicts)
        self.assertEqual(
            verdicts["docs/competitors.md"], "past-threshold",
            f"competitors freshness must be past-threshold; got {verdicts['docs/competitors.md']!r}",
        )


class BundleResolverCoverageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_competitor_data_family_satisfied(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        families = bundle["by-family"]
        self.assertIn("competitor-data", families)
        self.assertGreater(len(families["competitor-data"]), 0)

    def test_missing_perspectives_only_when_min_count_unmet(self):
        # All three families in market-report:write have min-count 1, and the
        # fixture provides ≥1 hit for each. Missing-perspectives should be empty.
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        self.assertEqual(bundle["missing-perspectives"], [])


class BundleResolverTraversalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_builds_on_edge_walked_into_traversal_hops(self):
        """`stripe-integration` builds-on `pricing` — that hop must appear."""
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        hops = bundle["traversal-hops"]
        self.assertGreater(len(hops), 0, f"expected ≥1 traversal hop; got {hops!r}")
        targets = {(h["from"], h["edge"], h["to"]) for h in hops}
        # The exact `to` is `docs/pricing.md` per the corpus
        self.assertTrue(
            any(
                h["from"] == "docs/_wiki/pages/stripe-integration.md"
                and h["edge"] == "builds-on"
                and h["to"] == "docs/pricing.md"
                for h in hops
            ),
            f"expected stripe-integration -> builds-on -> pricing hop; got {hops!r}",
        )


class BundleResolverDeterminismTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_two_runs_identical_modulo_generated_at(self):
        a = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        b = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        a.pop("generated-at", None)
        b.pop("generated-at", None)
        self.assertEqual(json.dumps(a, sort_keys=True), json.dumps(b, sort_keys=True))


class BundleResolverEmptyRepoTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.profiles = _load_fixture_profiles()

    def test_empty_corpus_surfaces_unsatisfied_zone_requirements(self):
        empty = {
            "schema_version": 1,
            "generated_at": "2026-05-04T00:00:00Z",
            "repo_root": ".",
            "repo_name": "",
            "counts": {"total": 0, "with_frontmatter": 0, "missing_required": 0, "warnings": 0},
            "summaries": {"zones": {}},
            "docs": [],
            "edges": [],
            "lifecycle": {},
            "domains": {},
            "orphans": [],
        }
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=empty
        )
        self.assertEqual(bundle["by-zone"], {})
        self.assertGreater(
            len(bundle["unsatisfied-zone-requirements"]),
            0,
            "empty corpus must surface required zones as unsatisfied",
        )


class BundleResolverEscalationTests(unittest.TestCase):
    """D-10 strict: default mechanical; opt-in flags are the ONLY LLM triggers."""

    @classmethod
    def setUpClass(cls):
        cls.cb = _import_bundle_module()
        cls.index = _build_fixture_index()
        cls.profiles = _load_fixture_profiles()

    def test_default_run_does_not_escalate(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write", profiles=self.profiles, index=self.index
        )
        self.assertEqual(
            bundle["escalations"], [],
            "default run must not auto-escalate (D-10 strict)",
        )

    def test_resolve_conflicts_dry_run_records_opt_in(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write",
            profiles=self.profiles,
            index=self.index,
            resolve_conflicts=True,
            dry_run=True,
        )
        self.assertIn("resolve-conflicts-dry-run", bundle["escalations"])

    def test_verify_coverage_dry_run_records_opt_in(self):
        bundle = self.cb.resolve_bundle(
            "market-report:write",
            profiles=self.profiles,
            index=self.index,
            verify_coverage=True,
            dry_run=True,
        )
        self.assertIn("verify-coverage-dry-run", bundle["escalations"])

    def test_resolve_conflicts_without_dry_run_raises(self):
        from context_bundle import LLMEscalationNotImplementedError
        with self.assertRaises(LLMEscalationNotImplementedError):
            self.cb.resolve_bundle(
                "market-report:write",
                profiles=self.profiles,
                index=self.index,
                resolve_conflicts=True,
                dry_run=False,
            )


class BundleResolverCLITests(unittest.TestCase):
    """Smoke-test the CLI used by manifest verification."""

    def test_cli_runs_with_fixture_profile(self):
        import subprocess

        result = subprocess.run(
            [
                sys.executable,
                str(SCRIPT_DIR / "context_bundle.py"),
                "--profile",
                "market-report:write",
                "--profiles-path",
                str(FIXTURE_PROFILES),
                "--index-root",
                str(FIXTURE_ROOT),
                "--json",
            ],
            capture_output=True,
            text=True,
            cwd=str(REPO_ROOT),
        )
        self.assertEqual(
            result.returncode, 0,
            f"CLI failed: stdout={result.stdout!r} stderr={result.stderr!r}",
        )
        # Output must be parseable JSON with required keys
        data = json.loads(result.stdout)
        self.assertEqual(data["profile-id"], "market-report:write")


if __name__ == "__main__":
    unittest.main(verbosity=2)
