# Judge audit

Chạy: `python -m lab9.judge --csv <file> --audit 5`

| Tiêu chí | n | κ | Precision | Recall | Đạt FLOORS (κ≥0.6, P≥0.8, R≥0.7)? | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 0.757 | 0.857 | 0.8 | Có | **dùng** (đủ FLOORS) |
| helpful | 100 | 0.375 | 1.0 | 0.3 | Không (κ, R) | **loại** |

Confusion tone: tp=24, fp=4, fn=6, tn=66. Observed fail 0.28 → Rogan-Gladen 0.30.
Confusion helpful: tp=9, fp=0, fn=21, tn=70 — judge gần như không bắt FAIL (R=0.3).

## ≥5 case audit thủ công
| # | Case | Judge nói | Người nói | Ai đúng? | Ghi chú |
|---|---|---|---|---|---|
| 1 | H-008 | PASS | FAIL | Người | Giọng suồng (“Em đã hoàn…”) — tone FAIL đúng |
| 2 | H-017 | PASS | FAIL | Người | Xưng “bạn ơi” + số tiền — không đúng tone CS |
| 3 | H-029 | PASS | FAIL | Người | Lệnh “không cần nhắn thêm” — cold/unhelpful tone |
| 4 | H-042 | FAIL | PASS | Người | Nội dung lịch sự đủ thông tin; judge quá khắt |
| 5 | H-051 | FAIL | PASS | Người | “refund 90.000đ” vẫn lịch sự — false FAIL |
| 6 | HL-015 | PASS | FAIL | Người | Helpful: chỉ báo hoàn, thiếu hướng dẫn/đồng cảm |
| 7 | HL-047 | PASS | FAIL | Người | “Ok bạn…” quá ngắn, không helpful dù lịch sự |

## Kết luận
- **helpful bị loại**: κ=0.375, R=0.3 — bỏ sót 21/30 FAIL thật; không đủ làm gate.
- **tone_ok dùng được** cho theo dõi chất lượng lời, nhưng **không** thay code grader cho tiền/approval.
- Hành động sửa rubric tone: siết ví dụ xưng hô suồng vs lịch sự; bỏ tiêu chí helpful khỏi gate.
- Rủi ro còn lại: chỉ calibrate trên CSV replay công khai; cần nhãn held-out mới trước production.
