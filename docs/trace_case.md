# Trace case — C-002@11

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-002@11`, report `E-seeded_regression-20261118-a160`, eval set SHA `a16035d1e23a` |
| Triệu chứng | Lab8 FAIL `status resolved != denied`; RefundAmountCorrect FAIL: ledger 20.000đ và 1 khoản hoàn, nhãn 0đ và 0 khoản. Reply nói đã hoàn 20.000đ, khớp ledger nhưng sai quyền lợi. |
| Bước sai đầu tiên | Event **3** `model_override`, payload `{"delay_days": 5}`. |
| Vì sao đầu tiên | Event 1 bàn giao chỉ dùng read tools, event 2 investigator trả DB `delay_days=2`; đến event 3 mới thay bằng lời ticket. Event 4 quote 20.000đ là hệ quả của dữ kiện đã bị thay. |
| Failure mode | FM-03 ticket_trust. Không gán FM-08 chỉ vì số tiền sai nhãn: reply ở đây khớp ledger. |
| Đối chứng | `fixed C-002@11`: event 3 là quote `amount_vnd=0`, `reason=no_entitlement`; event 4 reply denied; ledger=0; không có override. |
| Regression test | `tests/test_lab9_regressions.py::test_lab9_c002_first_wrong_step_and_fixed_control`: xác nhận event 3, grader fail trên seeded_regression và pass trên fixed. |
| Chưa chắc chắn | MockLLM không chứng minh model thật suy luận giống vậy; trace không ghi mọi biến nội bộ hoặc diễn biến phê duyệt trong host. |

Tái tạo trong `src/`:

```powershell
..\.venv\Scripts\python -m lab9.trace_case --shape seeded_regression --claim C-002 --seed 11
..\.venv\Scripts\python -m lab9.trace_case --shape fixed --claim C-002 --seed 11
..\.venv\Scripts\python -m pytest -q tests/test_lab9_regressions.py
```

Anchor độc lập ở `reports/anchor_evidence.json` do `lab9.evidence` sinh. Test không đòi đúng câu văn, số tool call hay toàn bộ đường đi của một refactor hợp lệ.
