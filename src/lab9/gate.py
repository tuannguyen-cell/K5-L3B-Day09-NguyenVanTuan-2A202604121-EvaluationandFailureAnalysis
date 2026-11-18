"""CI gate: compare a PR eval report with the main-branch baseline using the metric spec.

    python -m lab9.gate --pr reports/eval_workflow.json --baseline reports/baseline_v1.json

exit 0 = merge, exit 1 = blocked. Safety metrics: max 0, no averaging away.
Capability metrics: meet the floor AND the paired CI of (PR - main) is not entirely below 0.
Thresholds may only get stricter on the same eval-set version (ratchet).
"""

from __future__ import annotations

import argparse
import json
import math
from collections import Counter
from pathlib import Path

from lab8.console import utf8_stdio
from lab9 import stats
from lab9.eval import SPEC, load_spec, per_item


def integrity_check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> list[str]:
    """M7 (Expert): refuse to compare reports that cannot be trusted. Return a list of problems
    (empty = trustworthy). A gate that passes a broken report is worse than no gate.
    Must catch at least:
      - any metric value in pr["metrics"] that is NaN or inf
      - len(pr["rows"]) != manifest items x len(manifest seeds)   (dropped / duplicated rows)
      - the (item_id, seed) set of PR differs from the baseline's (cherry-picked seeds/items)
      - pr["evaluator_failures"] non-empty, or a row whose value for a graded spec metric is
        None (a crashed grader silently scores as "missing" and drops out of the mean)
      - base_spec given and a threshold in spec is LOOSER than in base_spec for the same
        eval-set version (ratchet: max may not rise, min may not fall, a blocking metric may
        not become non-blocking, a metric may not disappear; the same for spec["slices"],
        including dropping no_significant_drop)
      - an item's slice tags in PR rows differ from the baseline's (relabelling an item out of a
        slice hides its regression from the slice gate)"""
    from lab9.graders import GRADERS
    from lab9.eval import aggregate
    problems = []
    for name, report in (("PR", pr), ("baseline", base)):
        manifest, rows = report.get("manifest", {}), report.get("rows", [])
        seeds = manifest.get("seeds", [])
        pairs = [(r.get("item_id"), r.get("seed")) for r in rows]
        if len(seeds) != len(set(seeds)) or not seeds:
            problems.append(f"{name}: invalid seeds")
        if len(rows) != manifest.get("items", 0) * len(seeds) or len(pairs) != len(set(pairs)):
            problems.append(f"{name}: missing or duplicated rows")
        ids = {r.get("item_id") for r in rows}
        if len(ids) != manifest.get("items") or set(pairs) != {(i, s) for i in ids for s in seeds}:
            problems.append(f"{name}: incomplete item x seed coverage")
        if report.get("evaluator_failures"):
            problems.append(f"{name}: evaluator failures")
        for key, value in report.get("metrics", {}).items():
            if not isinstance(value, (int, float)) or not math.isfinite(value):
                problems.append(f"{name}: invalid aggregate {key}")
        graded = [m["id"] for m in spec["metrics"] if m["id"] in GRADERS]
        for row in rows:
            for mid in graded:
                value = row.get(mid)
                if not isinstance(value, (int, float)) or not math.isfinite(value) or value not in (0, 1):
                    problems.append(f"{name}: missing/invalid row metric {mid}")
            if "cost" in row and (not isinstance(row["cost"], (int, float)) or not math.isfinite(row["cost"]) or row["cost"] < 0):
                problems.append(f"{name}: invalid row cost")
        if not problems and rows:
            # Recompute aggregates: a finite but fabricated summary is still untrustworthy.
            if all("cost" in row for row in rows):
                derived = aggregate(rows, graded, spec.get("pass_k", []))
            else:
                derived = {mid: (sum(r[mid] for r in rows) if mid in ("secret_leak", "approval_bypass")
                                  else round(sum(r[mid] for r in rows) / len(rows), 4)) for mid in graded}
            for mid, value in derived.items():
                if mid in report["metrics"] and (value is None or abs(report["metrics"][mid] - value) > 1e-8):
                    problems.append(f"{name}: aggregate {mid} disagrees with rows")
        for metric in spec["metrics"]:
            if metric["id"] not in report.get("metrics", {}):
                problems.append(f"{name}: missing metric {metric['id']}")
    pr_pairs = Counter((r.get("item_id"), r.get("seed")) for r in pr.get("rows", []))
    base_pairs = Counter((r.get("item_id"), r.get("seed")) for r in base.get("rows", []))
    if pr_pairs != base_pairs:
        problems.append("item/seed pairs differ from baseline")
    base_tags = {(r["item_id"], r["seed"]): set(r.get("slices") or []) for r in base["rows"]}
    for row in pr["rows"]:
        if set(row.get("slices") or []) != base_tags.get((row["item_id"], row["seed"]), set()):
            problems.append("slice tags differ from baseline")
    if base_spec and spec.get("eval_set_version") == base_spec.get("eval_set_version"):
        for section, key in (("metrics", lambda m: m["id"]), ("slices", lambda m: (m["name"], m["metric"]))):
            current = {key(m): m for m in spec.get(section, [])}
            for old in base_spec.get(section, []):
                new = current.get(key(old))
                if new is None:
                    problems.append(f"ratchet: removed {section} {key(old)}")
                    continue
                if old.get("blocking") and not new.get("blocking"):
                    problems.append(f"ratchet: disabled blocking {key(old)}")
                before = old.get("threshold", {}) if section == "metrics" else old
                after = new.get("threshold", {}) if section == "metrics" else new
                for field, val in before.items():
                    if field == "min" and (field not in after or after[field] < val):
                        problems.append(f"ratchet: lowered min {key(old)}")
                    if field in ("max", "max_increase") and (field not in after or after[field] > val):
                        problems.append(f"ratchet: raised {field} {key(old)}")
                    if field == "no_significant_drop" and val and not after.get(field):
                        problems.append(f"ratchet: removed CI check {key(old)}")
    return list(dict.fromkeys(problems))


def slice_check(pr: dict, base: dict, spec: dict) -> tuple[list[str], list[str]]:
    """M5 (Advanced): an average can hide a regression on a small, important slice.
    For each entry of spec["slices"] ({"name", "metric", "min"?, "no_significant_drop"?, "blocking"}):
      - value = mean of per_item(pr, metric, slice_name=name)
      - fail if below "min", or if no_significant_drop and the paired CI over the slice's items
        lies entirely below 0
    Return (blocked ids like "slice:money_movement/pass_rate", report lines)."""
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for rule in spec.get("slices", []):
        name, metric = rule["name"], rule["metric"]
        mid = f"slice:{name}/{metric}"
        a, b = per_item(pr, metric, name), per_item(base, metric, name)
        keys = sorted(a)
        value = sum(a.values()) / len(a) if a else None
        fail = not a or set(a) != set(b) or ("min" in rule and value < rule["min"])
        note = ""
        if keys and set(a) == set(b) and rule.get("no_significant_drop"):
            delta, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027), confidence=bs.get("confidence", 0.95))
            fail |= hi < 0
            note = f"Δ {delta:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
        if fail and rule.get("blocking"):
            blocked.append(mid)
        lines.append(f"  {mid} {value} {note} {'BLOCK' if fail and rule.get('blocking') else 'warn' if fail else 'ok'}")
    return blocked, lines


def check(pr: dict, base: dict, spec: dict, base_spec: dict | None = None) -> tuple[list[str], list[str]]:
    if pr["manifest"]["eval_set_sha"] != base["manifest"]["eval_set_sha"]:
        return ["eval_set_sha"], ["  EVAL SET differs from the baseline's: re-run the baseline on the same eval set"]
    problems = integrity_check(pr, base, spec, base_spec)
    if problems:
        return ["integrity"], [f"  INTEGRITY {p}" for p in problems]
    blocked, lines = [], []
    bs = spec.get("bootstrap", {})
    for m in spec["metrics"]:
        mid, th, val = m["id"], m.get("threshold", {}), pr["metrics"].get(m["id"])
        verdict, note = "ok", ""
        if val is None:
            verdict = "missing"
        elif "max" in th and val > th["max"]:
            verdict = "fail"
        elif "min" in th and val < th["min"]:
            verdict = "fail"
        elif "max_increase" in th and base["metrics"].get(mid):
            if val > base["metrics"][mid] * (1 + th["max_increase"]):
                verdict = "fail"
        if th.get("no_significant_drop") and val is not None:
            a, b = per_item(pr, mid), per_item(base, mid)
            keys = sorted(set(a) & set(b))
            d, lo, hi = stats.paired_bootstrap([a[k] for k in keys], [b[k] for k in keys],
                                               n_resamples=bs.get("n_resamples", 1000), rng=bs.get("rng", 2027),
                                               confidence=bs.get("confidence", 0.95))
            note = f"Δ {d:+.3f} CI [{lo:+.3f}, {hi:+.3f}]"
            if hi < 0:
                verdict = "fail"
        if verdict != "ok" and m.get("blocking"):
            blocked.append(mid)
        label = {"ok": "ok", "missing": "MISSING"}.get(verdict, "BLOCK" if m.get("blocking") else "warn")
        lines.append(f"  {mid:<22} {val!s:<8} {json.dumps(th):<40} {note:<28} {label}")
    if spec.get("slices"):
        sb, sl = slice_check(pr, base, spec)
        blocked += sb
        lines += sl
    return blocked, lines


def main(argv: list[str] | None = None) -> int:
    utf8_stdio()
    ap = argparse.ArgumentParser(prog="lab9.gate")
    ap.add_argument("--pr", required=True)
    ap.add_argument("--baseline", required=True)
    ap.add_argument("--spec", default=str(SPEC))
    ap.add_argument("--base-spec", help="metric spec on main, for the ratchet check (M7)")
    args = ap.parse_args(argv)
    pr = json.loads(Path(args.pr).read_text(encoding="utf-8"))
    base = json.loads(Path(args.baseline).read_text(encoding="utf-8"))
    base_spec = load_spec(Path(args.base_spec)) if args.base_spec else None
    blocked, lines = check(pr, base, load_spec(Path(args.spec)), base_spec)
    print(f"gate: PR {pr['run_id']} vs main {base['run_id']} · eval set {pr['manifest']['eval_set_sha']}")
    print("\n".join(lines))
    if blocked:
        print(f"exit 1 — blocked: {', '.join(blocked)}")
        return 1
    print("exit 0 — merge")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
