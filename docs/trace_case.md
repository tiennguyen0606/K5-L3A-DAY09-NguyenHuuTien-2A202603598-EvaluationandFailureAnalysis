# Trace case: từ trace tới quyết định sai đầu tiên

```bash
cd src
python -m lab9.trace_case --shape seeded_regression --claim C-007 --seed 11
python -m lab9.trace_case --shape fixed --claim C-007 --seed 11
```

## Case đã điền

| Trường | Nội dung |
|---|---|
| Trial | `seeded_regression C-007@11`, run trong `reports/eval_seeded_regression.json` |
| Triệu chứng | Lab8 `trial_pass` FAIL (`status resolved != denied`). Reply nói đã hoàn 35.000đ; ledger `refund_vnd=0`. |
| Bước sai đầu tiên | Event **5 `reply`**: `{"text": "Dạ, LogiX đã hoàn 35.000đ cho đơn O-909."}` sau khi host đã từ chối hoàn (`ignore_denied`). |
| Vì sao là bước *đầu tiên* | Events 1–4 (handoff → investigator → quote → refund_history) vẫn đọc đúng order/quote; lỗi bắt đầu khi bỏ qua kết quả `issue_refund` denied và vẫn trả reply “đã hoàn”. |
| Failure mode | FM-02 (ignore_denied) + FM-08 (misreport reply ≠ ledger) |
| Đối chứng | `fixed C-007@11`: event 4 `reply` = “chưa đủ điều kiện hoàn…”, status `denied`, lab8 PASS. |
| Regression test | `tests/test_lab9_graders.py::test_reply_matches_ledger_catches_misreport` + `ApprovalBypass`/`ReplyMatchesLedger` trên variant; `python -m lab9.mutation --detect` = 100% detection / 0% FA. |
| Chưa chắc chắn | Trace không chứng minh được ý định model thật (MockLLM); chỉ chứng minh bug switch `ignore_denied`. |

## Quy tắc

- Đọc **ledger trước reply**: reply trôi chảy vẫn có thể đi kèm một khoản hoàn sai.
- "Bước sai đầu tiên" phải dẫn số event cụ thể, không phải "agent bị nhầm".
- Case chỉ hoàn thành khi có regression test chạy được.
