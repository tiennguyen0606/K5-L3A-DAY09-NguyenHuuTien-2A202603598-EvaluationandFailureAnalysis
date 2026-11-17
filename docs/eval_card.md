# Eval card — LogiX-VN refund agent

Card này đi kèm mỗi báo cáo và được dùng lại ở Day 10.

- **Run ID / eval set SHA:** baseline v1 `E-swarm-20261117-ef4e` / `ef4eafcec45b`; baseline v2 `E-swarm-20261117-02f1` / `02f15819a8a1`
- **Phiên bản:** code nhánh `starter/d09` · eval set v1/v2 · metric_spec 1.0 / 2.0 · seeds 11/22/33/44/55
- **Eval set:** v1 = 14 item × 5 seed (lab8_public); v2 = 28 item (+ adversarial pack); nhãn tách `labels_v*.json`
- **Metric & ngưỡng:** xem `config/metric_spec.yaml` và `metric_spec_v2.yaml` (FM-08 = `reply_matches_ledger`)
- **Kết quả baseline vs PR (v1):**
  - swarm pass_rate **0.9857**; fixed **1.0** (gate exit 0)
  - seeded_regression pass_rate **0.7143**, Δ **−0.271** CI **[−0.500, −0.057]** → gate exit 1 (`pass_rate` + graders)
- **Judge:** tone_ok κ=0.757, P=0.857, R=0.8 (PASS floors); helpful κ=0.375, R=0.3 → **loại** khỏi gate
- **Trace case:** `docs/trace_case.md` — C-007@11, bước sai = reply sau ignore_denied; regression test graders
- **Gate owner:** Eval owner trên PR `starter/d09` → `main`
- **Phạm vi pilot:** hoàn phí ship / bồi thường đã xác minh trên MockLLM, eval set công khai
- **Giới hạn / bằng chứng còn thiếu:** MockLLM, 14–28 item, judge replay; chưa đo user thật; bug 1/3 seed không ổn định với 5 seed
- **Khi nào tăng eval-set version:** thêm item từ trace case / adversarial mới → v3 + baseline mới

## v2 (M5–M7)
- **A/A** seeds 66,77,88,99,110: mọi metric Δ = **0** trên MockLLM → sàn `pass_hat_5` = **0.80** nằm ngoài nhiễu (nhiễu = 0). LLM thật sẽ có nhiễu > 0.
- **Slices:** `money_movement` min 0.90 (+ no_significant_drop) bắt `slice_regression` (overall vẫn ≥ 0.85, CI chạm 0); `adversarial` min 0.80; `denial` min 0.90.
- **Mutation scorecard:** 3/3 regression bị chặn, 0 false alarm (`fixed`, `honest_refactor` merge).
- **Traps:** cả 4 trap công khai → gate exit 1 (`INTEGRITY` / ratchet).
- **Giới hạn cỡ mẫu:** lỗi chỉ ở 1/3 seed không phát hiện ổn định với 5 seed; đừng hạ ngưỡng chỉ để “bắt” rare.
