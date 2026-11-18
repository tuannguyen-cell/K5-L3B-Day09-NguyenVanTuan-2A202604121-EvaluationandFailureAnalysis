# Bài làm Day09 — Nguyễn Văn Tuấn · 2A202604121

Đã hoàn thiện code và tài liệu M0–M7 tại local. Đây không phải xác nhận đã push, mở PR, merge hoặc nộp LMS.

- [Eval card](eval_card.md): kết quả, run ID, CI, slice, A/A và giới hạn.
- [Taxonomy](failure_taxonomy.md), [trace case](trace_case.md), [judge audit](judge_audit.md), [PRD v1.1](PRD_v1.1.md).
- `src/reports/validation.log`: output thực và expected exit code của các lệnh kiểm tra.
- `src/reports/baseline_v1.json`, `baseline_v2.json`, `eval_fixed.json`, `eval_seeded_regression.json`, `eval_slice_regression.json`: sinh bằng harness.
- `src/reports/anchor_evidence.json`, `judge_calibration.json`, `v2_scope_evidence.json`: sinh bằng `lab9.evidence`.

Tái tạo trên PowerShell từ repo root:

```powershell
python -m venv .venv
.\.venv\Scripts\python -m pip install -r src/requirements.txt -r src/requirements-lab9.txt
cd src
..\.venv\Scripts\python -m lab9.evalset --build --check
..\.venv\Scripts\python -m lab9.evalset --v2 --build
..\.venv\Scripts\python -m lab9.verify_submission --full
```

Mã `src/lab8/` nguyên bản upstream `034c6c421c198dae67a9211d15e2587d5a378972`. Không dùng code nhóm Day08 đã sửa. `tests/__init__.py` tránh trùng package `tests` từ thư viện cài ngoài. Reports và trap thử nghiệm được whitelist trong `.gitignore`; `reports/traps/` chỉ chứa các report cố tình làm sai để thử gate.

Khi nộp: commit các file bài làm và report, mở PR trong fork `tuannguyen-cell/K5-L3B-Day9-NguyenVanTuan-2A202604121-EvaluationandFailureAnalysis`, đích `main` của chính fork; bật Actions, chờ hai job gate xanh, merge rồi dán link repo vào LMS theo hạn của ca.

Nội dung PR có thể dùng:

```text
Hoàn thiện Day09 M0–M7: taxonomy, judge calibration, trajectory graders,
paired bootstrap, slice gate, pass@k/pass^k và report integrity/ratchet.

Core: fixed exit 0; seeded_regression exit 1:
  pass_rate 0.7143, Δ -0.271, CI [-0.500, -0.057]
  exit 1 — blocked: refund_amount_correct, pass_rate, reply_ledger_consistent

M3 detection 100%, false alarms 0%; 33 test Day09 qua.

Advanced/Expert: mutation score 3/3, false alarms 0; A/A Δ=0;
slice_regression bị chặn bởi slice:money_movement/pass_rate;
4 public traps bị chặn (mỗi gate exit 1).

Xem src/reports/validation.log để đối chiếu output và exit code.
Không sửa lab8 hoặc report bằng tay. Giới hạn: MockLLM, public judge replay,
14/28 item, 5 seed; chưa chạy hidden grader hoặc pilot thật.
```
