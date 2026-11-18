"""Generate inspectable anchor traces and calibration evidence without editing reports."""
from __future__ import annotations

import json
import tempfile
from pathlib import Path

from lab8.shapes import SHAPES
from lab8.console import utf8_stdio
from lab9.judge import calibrate
from lab9.trace_case import investigate
from lab9.variant_agent import make_shape
from lab9.eval import load_spec, load_world, make_task

ANCHORS = {
    "FM-01": ("C-001", {"no_override", "leaky_trace"}),
    "FM-02": ("C-007", {"no_override", "ignore_denied"}),
    "FM-03": ("C-002", {"ticket_trust"}),
    "FM-04": ("C-014", {"no_override", "sum_parts"}),
    "FM-05": ("C-014", {"no_override", "pre_deducted"}),
    "FM-06": ("C-006", {"no_override", "stale_clause"}),
    "FM-07": ("C-001", {"no_override", "sibling_refund"}),
    "FM-08": ("C-008", {"no_override", "misreport"}),
    "FM-09": ("C-005", {"no_override"}),
}


def main() -> None:
    utf8_stdio()
    out = Path("reports")
    out.mkdir(exist_ok=True)
    anchors = {}
    for fm, (claim, bugs) in ANCHORS.items():
        name = f"anchor_{fm.lower()}"
        SHAPES[name] = make_shape(name, bugs)
        anchors[fm] = investigate(name, claim, 11)
        t = anchors[fm]["trial"]
        print(f"{fm} {claim}@11: {t['lab8_pass']} {t['lab8_reason']}")
        for index, event in enumerate(t['events'], 1):
            print(f"  {index} {event['kind']} {json.dumps(event['payload'], ensure_ascii=False)[:160]}")
    (out / "anchor_evidence.json").write_text(json.dumps(anchors, ensure_ascii=False, indent=2), encoding="utf-8")
    spec = load_spec(Path("config/metric_spec_v2.yaml"))
    world, claims = load_world(spec)
    labels = json.loads(Path(spec["labels"]).read_text(encoding="utf-8"))
    with tempfile.TemporaryDirectory(prefix="lab9-v2-evidence-", ignore_cleanup_errors=True) as tmp:
        task = make_task("fixed", world, claims, labels, Path(tmp))
        v2 = {claim: {"trial": task({"claim_id": claim, "seed": 11}), "label": labels[claim]}
              for claim in ("C-110", "C-113", "C-114")}
    (out / "v2_scope_evidence.json").write_text(json.dumps(v2, ensure_ascii=False, indent=2), encoding="utf-8")
    judges = {kind: calibrate(Path(f"data/eval/judge_{kind}_public.csv")) for kind in ("tone", "helpful")}
    (out / "judge_calibration.json").write_text(json.dumps(judges, ensure_ascii=False, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main()
