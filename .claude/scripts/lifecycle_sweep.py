#!/usr/bin/env python3
"""
lifecycle_sweep.py — classify active-zone docs against lifecycle-routing.yml
and surface (or apply) routing decisions.

Composes existing infrastructure:

  - context_index._zone_for        path → zone classification
  - _wiki_yaml.parse_frontmatter   yaml frontmatter parsing
  - digest_sidecar                 typed-event sidecar IO
  - record_resolution              resolutions.jsonl write path
  - lifecycle-routing.yml          declarative rule table

Sweep stages, per active doc:

  1. evaluate_frontmatter_triggers   — deterministic checks against lifecycle.* fields
  2. scan_body_signals               — regex on body lines (SENT, DECISION, etc.)
  3. reality_check                   — git log / sibling-doc / url-in-body cross-checks
  4. classify                        — first matching rule with passing reality check
                                       wins; output route_decision
  5. auto_route                      — surface-only by default; with burn-in flipped
                                       false, calls git mv / wiki promote / fold-into

Output: JSON line on stdout (dispatcher contract) + sidecar merge + diary
append + (when applied) resolutions.jsonl row per route.

CLI:
    python .claude/scripts/lifecycle_sweep.py
    python .claude/scripts/lifecycle_sweep.py --dry-run
    python .claude/scripts/lifecycle_sweep.py --apply       # overrides surface_only
    python .claude/scripts/lifecycle_sweep.py --rule outbound-sent  # single-rule run

Reference:
  docs/_planned/lifecycle-sweep/implementation-plan.md
  docs/_bcos-framework/architecture/lifecycle-routing.md
  .claude/skills/schedule-dispatcher/references/job-lifecycle-sweep.md (P4)
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Iterable

try:
    import yaml
except ImportError:
    print("PyYAML required (pip install pyyaml)", file=sys.stderr)
    sys.exit(2)

_HERE = Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from _wiki_yaml import parse_frontmatter as _flat_parse_frontmatter  # noqa: E402

JOB_ID = "lifecycle-sweep"

_FM_RE = re.compile(r"\A---\s*\n(.*?)\n---\s*\n?", re.DOTALL)


def parse_frontmatter(text_or_path) -> dict:
    """Frontmatter parser that understands nested maps (lifecycle.* uses one).

    Falls back to the flat _wiki_yaml parser for any frontmatter PyYAML
    refuses (rare; the flat parser is more permissive about ad-hoc syntax).
    """
    if isinstance(text_or_path, Path):
        try:
            text = text_or_path.read_text(encoding="utf-8")
        except OSError:
            return {}
    else:
        text = str(text_or_path)
    m = _FM_RE.match(text)
    if not m:
        return {}
    try:
        data = yaml.safe_load(m.group(1)) or {}
        return data if isinstance(data, dict) else {}
    except yaml.YAMLError:
        return _flat_parse_frontmatter(text) or {}
ROUTING_CONFIG_REL = ".claude/quality/lifecycle-routing.yml"


# ---------------------------------------------------------------------------
# Repo-root resolution
# ---------------------------------------------------------------------------

def repo_root() -> Path:
    override = os.environ.get("BCOS_REPO_ROOT", "").strip()
    if override:
        p = Path(override).expanduser().resolve()
        if p.is_dir():
            return p
    return _HERE.parents[1]


# ---------------------------------------------------------------------------
# Routing config loader
# ---------------------------------------------------------------------------

@dataclass
class RoutingConfig:
    schema_version: str
    surface_only: bool
    burn_in_weeks: int
    scan_zones: list[str]
    min_age_days: int
    ambiguous_finding_type: str
    orphan_finding_type: str
    rules: list[dict[str, Any]]

    @property
    def auto_route_enabled(self) -> bool:
        return not self.surface_only


def load_routing_config(root: Path | None = None) -> RoutingConfig:
    r = root or repo_root()
    path = r / ROUTING_CONFIG_REL
    with path.open(encoding="utf-8") as fh:
        data = yaml.safe_load(fh) or {}
    g = data.get("global") or {}
    return RoutingConfig(
        schema_version=str(data.get("schema-version", "1.0.0")),
        surface_only=bool(g.get("surface_only", True)),
        burn_in_weeks=int(g.get("burn_in_weeks", 2)),
        scan_zones=list(g.get("scan_zones") or ["active", "inbox", "planned"]),
        min_age_days=int(g.get("min_age_days", 7)),
        ambiguous_finding_type=str(g.get("ambiguous_finding_type", "lifecycle-route-ambiguous")),
        orphan_finding_type=str(g.get("orphan_finding_type", "lifecycle-orphan-active")),
        rules=list(data.get("rules") or []),
    )


# ---------------------------------------------------------------------------
# Doc walker (uses _zone_for for path → zone resolution)
# ---------------------------------------------------------------------------

def _zone_for_rel(rel: str) -> str:
    """Mirror of context_index._zone_for, narrowed to what we need."""
    # Keep the import lazy so this script runs even when context_index has
    # unrelated import-time failures.
    try:
        from context_index import _zone_for  # type: ignore[import-not-found]
        return _zone_for(rel)
    except Exception:  # noqa: BLE001
        if rel.startswith("docs/_inbox/"):
            return "inbox"
        if rel.startswith("docs/_planned/"):
            return "planned"
        if rel.startswith("docs/_archive/"):
            return "archive"
        if rel.startswith("docs/_wiki/"):
            return "wiki"
        if rel.startswith("docs/_bcos-framework/"):
            return "framework"
        return "active"


def iter_zone_docs(root: Path, zones: Iterable[str]) -> Iterable[Path]:
    """Yield every .md file whose zone-resolution falls in `zones`."""
    docs = root / "docs"
    if not docs.is_dir():
        return
    target = set(zones)
    for path in sorted(docs.rglob("*.md")):
        rel = str(path.relative_to(root)).replace("\\", "/")
        if path.name.startswith(".") or path.name == "_manifest.md":
            continue
        if _zone_for_rel(rel) in target:
            yield path


# ---------------------------------------------------------------------------
# P3_002 — Frontmatter trigger evaluator
# ---------------------------------------------------------------------------

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([dwmyDWMY])?\s*$")
_DAYS_PER_UNIT = {"d": 1, "w": 7, "m": 30, "y": 365}


def _parse_duration_days(s: str | None) -> int | None:
    """Parse '30d' / '6w' / '90' (bare days) → integer days."""
    if s is None:
        return None
    m = _DURATION_RE.match(str(s))
    if not m:
        return None
    n = int(m.group(1))
    unit = (m.group(2) or "d").lower()
    return n * _DAYS_PER_UNIT.get(unit, 1)


def _parse_iso(s: str | None) -> date | None:
    if not s:
        return None
    try:
        return date.fromisoformat(str(s).strip()[:10])
    except ValueError:
        return None


@dataclass
class FrontmatterSignals:
    archive_when: str | None = None
    fold_into: str | None = None
    expires_after_days: int | None = None
    route_to_wiki_after_days: int | None = None
    route_to_collection: str | None = None
    last_updated: date | None = None
    age_days: int | None = None

    def expires_now(self, today: date) -> bool:
        if self.expires_after_days is None or self.last_updated is None:
            return False
        return (today - self.last_updated).days >= self.expires_after_days

    def wiki_due_now(self, today: date) -> bool:
        if self.route_to_wiki_after_days is None or self.last_updated is None:
            return False
        return (today - self.last_updated).days >= self.route_to_wiki_after_days


def evaluate_frontmatter_triggers(fm: dict, today: date | None = None) -> FrontmatterSignals:
    today = today or date.today()
    lc = fm.get("lifecycle") or {}
    if not isinstance(lc, dict):
        lc = {}
    last_updated = _parse_iso(fm.get("last-updated") or fm.get("last_updated"))
    age_days = (today - last_updated).days if last_updated else None
    return FrontmatterSignals(
        archive_when=lc.get("archive_when"),
        fold_into=lc.get("fold_into"),
        expires_after_days=_parse_duration_days(lc.get("expires_after")),
        route_to_wiki_after_days=_parse_duration_days(lc.get("route_to_wiki_after_days")) or (
            int(lc["route_to_wiki_after_days"])
            if isinstance(lc.get("route_to_wiki_after_days"), int) else None
        ),
        route_to_collection=lc.get("route_to_collection"),
        last_updated=last_updated,
        age_days=age_days,
    )


# ---------------------------------------------------------------------------
# P3_003 — Body-signal scanner
# ---------------------------------------------------------------------------

@dataclass
class BodySignals:
    markers: dict[str, int]              # canonical marker → first line index
    has_external_url: bool
    staleness_markers: list[str]         # TODO/PENDING/DRAFT mentions


_CANONICAL_MARKERS = (
    "SENT", "OUTCOME", "DECISION", "RESOLVED", "PUBLISHED", "ABANDONED",
)
_STALENESS_MARKERS = ("TODO", "PENDING", "DRAFT", "FIXME")
_URL_RE = re.compile(r"https?://[^\s)\]]+", re.IGNORECASE)
_LINE_MARKER_RE = re.compile(r"^([A-Z]{4,12}):\s")


def scan_body_signals(text: str) -> BodySignals:
    """Walk the doc body once, extract markers/urls/staleness flags."""
    markers: dict[str, int] = {}
    staleness: list[str] = []
    has_url = False

    for i, raw in enumerate(text.splitlines()):
        m = _LINE_MARKER_RE.match(raw)
        if m and m.group(1) in _CANONICAL_MARKERS and m.group(1) not in markers:
            markers[m.group(1)] = i
        for s in _STALENESS_MARKERS:
            if s in raw and s not in staleness:
                staleness.append(s)
        if not has_url and _URL_RE.search(raw):
            has_url = True
    return BodySignals(markers=markers, has_external_url=has_url, staleness_markers=staleness)


def _strip_frontmatter(text: str) -> str:
    if not text.startswith("---\n"):
        return text
    end = text.find("\n---", 4)
    if end == -1:
        return text
    closing = end + len("\n---")
    if closing < len(text) and text[closing] == "\n":
        closing += 1
    return text[closing:]


# ---------------------------------------------------------------------------
# P3_004 — Reality cross-check
# ---------------------------------------------------------------------------

@dataclass
class RealityResult:
    check_id: str
    passed: bool
    detail: str = ""


def _git_log_mentions(path: Path, root: Path) -> bool:
    """True when git log shows ≥1 commit touching this path. Best-effort."""
    try:
        rel = str(path.relative_to(root)).replace("\\", "/")
        result = subprocess.run(
            ["git", "-C", str(root), "log", "--oneline", "-1", "--", rel],
            capture_output=True, text=True, timeout=5, check=False,
        )
        return bool(result.stdout.strip())
    except Exception:  # noqa: BLE001
        return False


def reality_check(
    check: dict,
    *,
    path: Path,
    root: Path,
    body: str,
    fm: dict,
    body_signals: BodySignals,
) -> RealityResult:
    """Run one reality-check spec against the doc state."""
    check_id = str(check.get("id", "?"))
    check_type = str(check.get("type", "?"))

    if check_type == "url-in-body":
        return RealityResult(check_id, body_signals.has_external_url,
                             "external URL present" if body_signals.has_external_url
                             else "no external URL in body")

    if check_type == "target-file-exists":
        lc = fm.get("lifecycle") or {}
        target = lc.get("fold_into") or lc.get("route_to_collection")
        if not target:
            return RealityResult(check_id, False, "no fold_into/route_to_collection declared")
        target_path = root / str(target)
        return RealityResult(check_id, target_path.is_file(),
                             f"target {target} {'exists' if target_path.is_file() else 'missing'}")

    if check_type == "git-log-mention":
        return RealityResult(check_id, _git_log_mentions(path, root),
                             "git log has commits touching this file"
                             if _git_log_mentions(path, root) else "no git history found")

    if check_type == "sibling-version-exists":
        # Look for a sibling file with -sent / -final / next-period suffix.
        stem = path.stem
        candidates = [
            path.with_name(f"{stem}-sent.md"),
            path.with_name(f"{stem}-final.md"),
            path.with_name(f"{stem}.sent.md"),
        ]
        found = next((c for c in candidates if c.is_file()), None)
        return RealityResult(check_id, found is not None,
                             f"sibling: {found}" if found else "no sibling-version file")

    if check_type == "next-period-doc-exists":
        # Snapshot detection: does a sibling with a later YYYY-MM-DD or YYYY-Q?
        # exist in the same directory?
        date_re = re.compile(r"(\d{4})[-_]?(\d{2})")
        m = date_re.search(path.stem)
        if not m:
            return RealityResult(check_id, False, "no date in filename")
        year, month = int(m.group(1)), int(m.group(2))
        for sibling in path.parent.glob("*.md"):
            if sibling == path:
                continue
            ms = date_re.search(sibling.stem)
            if not ms:
                continue
            sy, sm = int(ms.group(1)), int(ms.group(2))
            if (sy, sm) > (year, month):
                return RealityResult(check_id, True, f"newer snapshot: {sibling.name}")
        return RealityResult(check_id, False, "no newer-period snapshot found")

    if check_type == "manifest-row-exists":
        lc = fm.get("lifecycle") or {}
        target = lc.get("route_to_collection") or ""
        manifest = root / target / "_manifest.md" if target else None
        return RealityResult(check_id, bool(manifest and manifest.is_file()),
                             f"manifest {'exists' if manifest and manifest.is_file() else 'missing'}")

    if check_type == "skill-registry-check":
        # Stub: shipped audits should reference a real skill in
        # .claude/quality/ecosystem/state.json. Defer to v0.2; pass-through.
        return RealityResult(check_id, True, "skill-registry-check deferred (always passes v0.1)")

    return RealityResult(check_id, False, f"unknown check type: {check_type}")


# ---------------------------------------------------------------------------
# P3_005 — Classifier
# ---------------------------------------------------------------------------

@dataclass
class RouteDecision:
    verdict: str           # auto | preselect | ambiguous | leave_alone | flag
    rule_id: str | None
    destination_zone: str | None
    destination_bucket: str | None
    auto_fix_id: str | None
    confidence: float
    reasons: list[str] = field(default_factory=list)
    finding_type: str = "lifecycle-trigger-fired"


def _rule_matches(rule: dict, fm_signals: FrontmatterSignals,
                  body_signals: BodySignals, fm: dict, doc_zone: str) -> tuple[bool, list[str]]:
    """Quick pre-filter: zone + cluster-hint + name-pattern + lifecycle-trigger."""
    reasons: list[str] = []
    match = rule.get("match") or {}

    zones = match.get("zones") or []
    if zones and doc_zone not in zones:
        return False, ["zone-mismatch"]

    triggers = match.get("lifecycle-triggers") or []
    trigger_hit = False
    if triggers:
        for trig in triggers:
            if not isinstance(trig, dict):
                continue
            if "archive_when" in trig:
                allowed = trig["archive_when"] if isinstance(trig["archive_when"], list) else [trig["archive_when"]]
                if fm_signals.archive_when and fm_signals.archive_when in allowed:
                    trigger_hit = True
                    reasons.append(f"archive_when={fm_signals.archive_when}")
            if "expires_after" in trig and fm_signals.expires_after_days is not None:
                trigger_hit = True
                reasons.append(f"expires_after={fm_signals.expires_after_days}d")
            if "route_to_wiki_after_days" in trig and fm_signals.route_to_wiki_after_days is not None:
                trigger_hit = True
                reasons.append(f"route_to_wiki_after_days={fm_signals.route_to_wiki_after_days}d")
            if "fold_into" in trig and fm_signals.fold_into is not None:
                trigger_hit = True
                reasons.append(f"fold_into={fm_signals.fold_into}")
            if "route_to_collection" in trig and fm_signals.route_to_collection is not None:
                trigger_hit = True
                reasons.append(f"route_to_collection={fm_signals.route_to_collection}")
    else:
        # No lifecycle-triggers → name-pattern + cluster fallback for snapshot/idea-dead/etc.
        trigger_hit = True

    if not trigger_hit:
        return False, ["no-lifecycle-trigger"]

    cluster_hints = [str(c).lower() for c in (match.get("cluster-hints") or [])]
    if cluster_hints:
        cluster = str(fm.get("cluster", "")).lower()
        if cluster and cluster in cluster_hints:
            reasons.append(f"cluster-hint:{cluster}")

    name_patterns = match.get("name-patterns") or []
    if name_patterns:
        name = str(fm.get("name", ""))
        if any(re.search(p, name) for p in name_patterns):
            reasons.append("name-pattern-hit")

    return True, reasons


def _apply_body_markers(rule: dict, body_signals: BodySignals) -> tuple[float, bool]:
    """Apply rule.body-markers to a confidence score. Returns (boost, disqualified)."""
    boost = 0.0
    disqualified = False
    for spec in rule.get("body-markers") or []:
        pattern = spec.get("pattern", "")
        # Map regex pattern back to canonical marker (cheap heuristic).
        m = re.match(r"\^([A-Z]{4,12}):", pattern)
        marker = m.group(1) if m else None
        present = marker in body_signals.markers if marker else False

        # URL pattern (https?://) — non-canonical; compile and test instead.
        if not marker and pattern.startswith("https?"):
            present = body_signals.has_external_url

        role = spec.get("role", "boost")
        cb = float(spec.get("confidence-boost", 0.0))
        if role == "require" and not present:
            disqualified = True
        elif role == "require" and present and cb < 0:
            # require with negative boost = "if present, disqualify" (rule 2)
            disqualified = True
        elif present:
            boost += cb
    return boost, disqualified


def classify(
    *,
    path: Path,
    root: Path,
    fm: dict,
    body: str,
    config: RoutingConfig,
    today: date | None = None,
) -> RouteDecision:
    today = today or date.today()
    doc_zone = _zone_for_rel(str(path.relative_to(root)).replace("\\", "/"))

    # min_age_days — never route fresh docs
    fm_signals = evaluate_frontmatter_triggers(fm, today)
    if fm_signals.age_days is not None and fm_signals.age_days < config.min_age_days:
        return RouteDecision("leave_alone", None, None, None, None, 0.0,
                             reasons=[f"age={fm_signals.age_days}d < min_age_days={config.min_age_days}"])

    body_signals = scan_body_signals(body)

    for rule in config.rules:
        ok, base_reasons = _rule_matches(rule, fm_signals, body_signals, fm, doc_zone)
        if not ok:
            continue

        boost, disqualified = _apply_body_markers(rule, body_signals)
        if disqualified:
            continue

        confidence = 0.5 + boost
        reasons = list(base_reasons)
        reasons.extend(f"marker:{m}" for m in body_signals.markers)

        # Reality checks
        all_passed = True
        verdict = "auto" if rule.get("confidence-tier", 3) == 1 else (
            "preselect" if rule.get("confidence-tier", 3) == 2 else "flag"
        )
        for check in rule.get("reality-checks") or []:
            res = reality_check(check, path=path, root=root, body=body,
                                fm=fm, body_signals=body_signals)
            reasons.append(f"check:{res.check_id}={'pass' if res.passed else 'fail'}")
            if not res.passed:
                all_passed = False
                fail_action = check.get("fail-action", "ambiguous")
                if fail_action == "ambiguous":
                    return RouteDecision(
                        "ambiguous", rule.get("id"),
                        rule.get("destination", {}).get("zone"),
                        rule.get("destination", {}).get("bucket"),
                        rule.get("auto-fix-id"),
                        confidence, reasons,
                        finding_type=config.ambiguous_finding_type,
                    )
                if fail_action == "skip":
                    break  # try next rule
                # warn: continue at lower confidence
                confidence -= 0.2
        else:
            # All reality-checks passed (or were warn-only)
            destination = rule.get("destination") or {}
            return RouteDecision(
                verdict if all_passed else "preselect",
                rule.get("id"),
                destination.get("zone"),
                destination.get("bucket"),
                rule.get("auto-fix-id"),
                max(0.0, min(1.0, confidence)),
                reasons,
                finding_type=(
                    "lifecycle-body-marker-confirmed"
                    if body_signals.markers else "lifecycle-trigger-fired"
                ),
            )
        # If we broke from inner for-loop with skip, fall through to next rule.

    # No rule matched — orphan-active candidate?
    if (
        doc_zone == "active"
        and not fm_signals.archive_when
        and not fm_signals.fold_into
        and fm_signals.expires_after_days is None
        and fm_signals.route_to_wiki_after_days is None
        and fm_signals.age_days is not None
        and fm_signals.age_days >= config.min_age_days * 8  # heuristic: 56d default
    ):
        return RouteDecision(
            "flag", None, None, None, None, 0.3,
            reasons=[f"orphan-active age={fm_signals.age_days}d"],
            finding_type=config.orphan_finding_type,
        )

    return RouteDecision("leave_alone", None, None, None, None, 0.0,
                         reasons=["no-rule-matched"])


# ---------------------------------------------------------------------------
# P3_006 — Auto-route executor
# ---------------------------------------------------------------------------

def auto_route(decision: RouteDecision, *, path: Path, root: Path, surface_only: bool) -> dict:
    """Apply (or describe) the route decision.

    surface_only=True → never mutates the filesystem; returns a planned action
    description that callers surface as a finding/card.

    surface_only=False → invokes the appropriate move via subprocess. We never
    duplicate the move logic from bcos-wiki / context-ingest — we shell out so
    one source of truth wins per move type.
    """
    rel = str(path.relative_to(root)).replace("\\", "/")
    plan = {
        "rule_id": decision.rule_id,
        "destination_zone": decision.destination_zone,
        "destination_bucket": decision.destination_bucket,
        "auto_fix_id": decision.auto_fix_id,
        "applied": False,
        "applied_diff_summary": "",
        "surface_only": surface_only,
    }
    if surface_only or decision.verdict not in ("auto",):
        plan["applied_diff_summary"] = (
            f"Would route {rel} → {decision.destination_zone}/{decision.destination_bucket}"
            f" via {decision.auto_fix_id}"
        )
        return plan

    # Auto-route path (only when verdict==auto AND surface_only=False)
    fix_id = decision.auto_fix_id
    if fix_id == "lifecycle-route-archive":
        bucket = decision.destination_bucket or ""
        target = root / "docs" / "_archive" / bucket / path.name
        target.parent.mkdir(parents=True, exist_ok=True)
        try:
            subprocess.run(
                ["git", "-C", str(root), "mv", rel,
                 str(target.relative_to(root)).replace("\\", "/")],
                check=True, capture_output=True, text=True, timeout=10,
            )
            plan["applied"] = True
            plan["applied_diff_summary"] = f"git mv {rel} → docs/_archive/{bucket}/{path.name}"
        except subprocess.CalledProcessError as exc:
            plan["applied_diff_summary"] = f"git mv failed: {exc.stderr.strip()[:200]}"
    elif fix_id == "lifecycle-route-wiki":
        # Delegate to bcos-wiki promote — never replicate.
        plan["applied_diff_summary"] = (
            f"Delegate to bcos-wiki: /wiki promote {path.stem} (deferred — chat-driven)"
        )
    elif fix_id == "lifecycle-route-collection":
        plan["applied_diff_summary"] = (
            f"Delegate to context-ingest Path 5: route {rel} → "
            f"docs/_collections/{decision.destination_bucket} (deferred)"
        )
    elif fix_id == "lifecycle-fold-into":
        plan["applied_diff_summary"] = (
            f"Fold-into target: chat-driven (sweep flags; user confirms before edit)"
        )
    return plan


# ---------------------------------------------------------------------------
# P3_007 — Main entry
# ---------------------------------------------------------------------------

def _render_finding(decision: RouteDecision, path: Path, root: Path) -> dict:
    rel = str(path.relative_to(root)).replace("\\", "/")
    verdict = "amber" if decision.verdict in ("preselect", "ambiguous", "flag") else "green"
    suggested = []
    if decision.auto_fix_id:
        suggested.append(decision.auto_fix_id)
    return {
        "finding_type": decision.finding_type,
        "verdict": verdict,
        "emitted_by": JOB_ID,
        "finding_attrs": {
            "file": rel,
            "rule_id": decision.rule_id,
            "destination_zone": decision.destination_zone,
            "destination_bucket": decision.destination_bucket,
            "confidence": round(decision.confidence, 2),
            "reasons": decision.reasons,
        },
        "suggested_actions": suggested,
    }


def run_sweep(
    *,
    root: Path | None = None,
    apply: bool = False,
    only_rule: str | None = None,
    today: date | None = None,
) -> dict:
    """Walk active+inbox+planned zones, classify each doc, return aggregated result."""
    r = root or repo_root()
    config_path = r / ROUTING_CONFIG_REL
    if not config_path.is_file():
        msg = (
            f"Routing config missing at {ROUTING_CONFIG_REL}. "
            "Seed it from docs/_bcos-framework/architecture/lifecycle-routing.md "
            "or set lifecycle-sweep.enabled=false in .claude/quality/schedule-config.json."
        )
        finding = {
            "number": 1,
            "finding_type": "lifecycle-config-missing",
            "verdict": "amber",
            "emitted_by": JOB_ID,
            "finding_attrs": {"file": ROUTING_CONFIG_REL},
            "suggested_actions": ["seed-config", "disable-job"],
        }
        return {
            "verdict": "amber",
            "findings_count": 1,
            "auto_fixed": [],
            "actions_needed": [msg],
            "notes": "Skipped sweep: routing config missing.",
            "findings": [finding],
            "routed": [],
            "surface_only": True,
        }
    config = load_routing_config(r)
    if only_rule:
        config.rules = [rule for rule in config.rules if rule.get("id") == only_rule]
    surface_only = (not apply) or config.surface_only

    findings: list[dict] = []
    routed: list[dict] = []
    docs_scanned = 0

    for path in iter_zone_docs(r, config.scan_zones):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        fm = parse_frontmatter(text) or {}
        body = _strip_frontmatter(text)
        decision = classify(path=path, root=r, fm=fm, body=body, config=config, today=today)
        docs_scanned += 1
        if decision.verdict == "leave_alone":
            continue
        findings.append(_render_finding(decision, path, r))
        plan = auto_route(decision, path=path, root=r, surface_only=surface_only)
        if plan.get("applied"):
            routed.append({"file": str(path.relative_to(r)).replace("\\", "/"), **plan})

    # Verdict roll-up
    if not findings:
        verdict = "green"
    elif any(f["finding_type"] == config.ambiguous_finding_type for f in findings):
        verdict = "amber"
    else:
        verdict = "amber"

    return {
        "verdict": verdict,
        "findings_count": len(findings),
        "auto_fixed": [r["applied_diff_summary"] for r in routed if r.get("applied_diff_summary")],
        "actions_needed": [
            f"{f['finding_type']}: {f['finding_attrs']['file']}" for f in findings
        ],
        "notes": (
            f"Scanned {docs_scanned} docs across {','.join(config.scan_zones)}; "
            f"{len(findings)} routing finding(s); "
            f"{'surface-only' if surface_only else 'auto-route enabled'}."
        ),
        "findings": findings,
        "routed": routed,
        "surface_only": surface_only,
    }


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    apply = "--apply" in argv
    dry_run = "--dry-run" in argv
    only_rule = None
    if "--rule" in argv:
        i = argv.index("--rule")
        if i + 1 < len(argv):
            only_rule = argv[i + 1]

    r = repo_root()
    result = run_sweep(root=r, apply=apply, only_rule=only_rule)

    if dry_run:
        print(json.dumps({**result, "dry_run": True}, ensure_ascii=False, indent=2))
        return 0

    # Wire into digest_sidecar + diary (Phase 3.5).
    try:
        from digest_sidecar import (  # type: ignore[import-not-found]
            parse_sidecar, write_sidecar, ParsedSidecar, Finding, JobSummary, AutoFix,
        )
        sidecar_path = r / "docs" / "_inbox" / "daily-digest.json"
        existing = parse_sidecar(sidecar_path)
        if existing is None:
            existing = ParsedSidecar(
                schema_version="1.0.0",
                date=datetime.now(timezone.utc).date().isoformat(),
                overall_verdict="green",
                run_at=datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            )
        # Drop prior findings from this job (idempotent re-run).
        existing.findings = [f for f in existing.findings if f.emitted_by != JOB_ID]
        next_n = max((f.number for f in existing.findings), default=0) + 1
        for i, f in enumerate(result["findings"]):
            existing.findings.append(Finding(
                number=next_n + i,
                finding_type=f["finding_type"],
                verdict=f["verdict"],
                emitted_by=f["emitted_by"],
                finding_attrs=f["finding_attrs"],
                suggested_actions=f.get("suggested_actions", []),
            ))
        # Roll up overall verdict.
        rank = {"green": 0, "amber": 1, "red": 2, "error": 3}
        worst = max((rank.get(f.verdict, 0) for f in existing.findings), default=0)
        existing.overall_verdict = ["green", "amber", "red", "error"][worst]
        # Per-job summary.
        existing.jobs = [j for j in existing.jobs if j.job != JOB_ID]
        existing.jobs.append(JobSummary(
            job=JOB_ID, verdict=result["verdict"], finding_count=result["findings_count"],
        ))
        sidecar_path.parent.mkdir(parents=True, exist_ok=True)
        write_sidecar(sidecar_path, existing)
    except Exception as exc:  # noqa: BLE001
        print(f"[lifecycle-sweep] sidecar wire failed: {exc}", file=sys.stderr)

    # Diary append.
    try:
        diary_path = r / ".claude" / "hook_state" / "schedule-diary.jsonl"
        diary_path.parent.mkdir(parents=True, exist_ok=True)
        with diary_path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "ts": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
                "job": JOB_ID,
                "verdict": result["verdict"],
                "findings_count": result["findings_count"],
                "auto_fixed": result["auto_fixed"],
                "actions_needed": result["actions_needed"],
                "notes": result["notes"],
                "trigger": "scheduled-headless",
            }, ensure_ascii=False) + "\n")
    except Exception as exc:  # noqa: BLE001
        print(f"[lifecycle-sweep] diary append failed: {exc}", file=sys.stderr)

    # Per-route resolution log (only when actually applied).
    if result["routed"]:
        try:
            from record_resolution import ResolutionEvent, record  # type: ignore[import-not-found]
            for route in result["routed"]:
                record(ResolutionEvent(
                    finding_type="lifecycle-trigger-fired",
                    finding_attrs={"file": route["file"], "rule_id": route.get("rule_id")},
                    action_taken=route.get("auto_fix_id") or "lifecycle-route-archive",
                    action_target=route["file"],
                    outcome="applied",
                    trigger="scheduled-headless",
                    applied_diff_summary=route.get("applied_diff_summary", ""),
                ))
        except Exception as exc:  # noqa: BLE001
            print(f"[lifecycle-sweep] resolution log failed: {exc}", file=sys.stderr)

    summary = {k: result[k] for k in
               ("verdict", "findings_count", "auto_fixed", "actions_needed", "notes")}
    print(json.dumps(summary, ensure_ascii=False))
    return 0 if result["verdict"] != "error" else 1


if __name__ == "__main__":
    sys.exit(main())
