"""Behavioral regressions from trace analysis, including evidence-free overrides."""
import copy
import pytest

from lab9 import gate
from lab9.graders import RefundAmountCorrect, ReplyLedgerConsistent
from lab9.trace_case import investigate
from tests.test_lab9_graders import ctx, trial
from tests.test_lab9_advanced import ROWS, SPEC, _report

pytestmark = pytest.mark.student


def test_lab9_c002_first_wrong_step_and_fixed_control():
    broken = investigate("seeded_regression", "C-002", 11)
    fixed = investigate("fixed", "C-002", 11)
    assert broken["trial"]["events"][2] == {"kind": "model_override", "payload": {"delay_days": 5}}
    assert not RefundAmountCorrect().evaluate(ctx(broken["trial"], broken["label"])).value
    assert RefundAmountCorrect().evaluate(ctx(fixed["trial"], fixed["label"])).value
    assert not any(e["kind"] == "model_override" for e in fixed["trial"]["events"])


@pytest.mark.parametrize("text,amount,ok", [
    ("Dạ, đã hoàn 20.000đ cho đơn O-808.", 20000, True),
    ("LogiX đã hoàn phí 20,000 VND cho đơn O-808 ạ.", 20000, True),
    ("Đã hoàn 35 000 đồng cho đơn O-808.", 20000, False),
    ("Đã hoàn 35000đ.", 20000, False),
])
def test_lab9_fm08_compares_reply_to_ledger(text, amount, ok):
    t = trial(refund_vnd=amount, events=[{"kind": "reply", "payload": {"text": text}}])
    t["result"]["status"] = "resolved"
    assert ReplyLedgerConsistent().evaluate(ctx(t)).value is ok


def test_lab9_advanced_duplicate_rows_and_green_evaluator_failure():
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    duplicate = copy.deepcopy(base)
    duplicate["rows"][-1] = copy.deepcopy(duplicate["rows"][0])
    assert gate.integrity_check(duplicate, base, SPEC)
    crashed = copy.deepcopy(base)
    crashed["evaluator_failures"] = ["grader failed despite green metrics"]
    assert gate.integrity_check(crashed, base, SPEC)


def test_lab9_advanced_slice_relabel_and_forged_summary():
    base = _report(copy.deepcopy(ROWS), {"pass_rate": 1.0})
    relabel = copy.deepcopy(base)
    relabel["rows"][0]["slices"] = []
    assert gate.integrity_check(relabel, base, SPEC)
    forged = copy.deepcopy(base)
    forged["rows"][0]["pass_rate"] = False
    assert gate.integrity_check(forged, base, SPEC)
