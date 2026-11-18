# Judge audit

Nguồn: hai CSV public, replay offline, positive class=FAIL. Bằng chứng máy đọc được sinh bởi `python -m lab9.evidence`: `src/reports/judge_calibration.json`.

| Tiêu chí | n | TP/FP/FN/TN | κ | Precision | Recall | Quyết định |
|---|---|---|---|---|---|---|
| tone_ok | 100 | 24/4/6/66 | 0.757 | 0.857 | 0.800 | Đạt κ≥0.6, P≥0.8, R≥0.7; dùng cho tone trong phạm vi replay |
| helpful | 100 | 9/0/21/70 | 0.375 | 1.000 | 0.300 | Loại khỏi gate: bỏ sót 21/30 lỗi |

Tone: tỷ lệ lỗi quan sát 0.28, sensitivity=0.8, specificity=66/70; Rogan–Gladen hiệu chỉnh thành 0.30. Helpful: quan sát 0.09, hiệu chỉnh 0.30 nhưng việc hiệu chỉnh tỷ lệ tổng không sửa được lỗi phân loại từng case. Không dùng helpful để quyết định merge.

| Case | Judge / Người | Ai đúng và bằng chứng | Sửa rubric |
|---|---|---|---|
| H-008 | PASS / FAIL | Người: “em”, “anh”, “nha” quá suồng sã theo chuẩn CS trong nhãn. | Nêu cách xưng hô anh/chị; thêm ví dụ thân thiện nhưng không đạt chuẩn. |
| H-017 | PASS / FAIL | Người: “bạn ơi”, “rồi nha” không hợp chuẩn khách hàng đang áp dụng. | Tách lịch sự khỏi thân thiện; kiểm tra cả cách gọi và đuôi câu. |
| H-029 | PASS / FAIL | Người: “không cần nhắn thêm” có tính ra lệnh; chữ “Dạ” không đủ. | Đánh giá toàn câu, yêu cầu cách đề nghị chờ không hạn chế khách phản hồi. |
| H-042 | FAIL / PASS | Người: trả lời ngắn, có số tiền và thời gian nhận, vẫn lịch sự. | Không bắt buộc xin lỗi trong mọi câu; tránh phạt vì độ dài. |
| H-051 | FAIL / PASS | Người: từ “refund” được CS cho phép theo note. | Whitelist thuật ngữ nghiệp vụ được duyệt, không phạt mọi từ tiếng Anh. |
| HL-015 | PASS / FAIL | Người: nói 55.000đ nhưng ledger 40.000đ. | Tách tone và factual correctness; dùng code so reply với ledger. |
| HL-016 | PASS / FAIL | Người: xin lỗi dài nhưng nói 55.000đ thay vì 35.000đ. | Nội dung lịch sự không bù được sai tiền; đưa negative example này vào rubric. |
| HL-020 | PASS / FAIL | Người: 90.000đ khác ledger 120.000đ. | Cung cấp dữ liệu chuẩn cho phần factual, giữ quyết định tiền ở code grader. |
| HL-028 | PASS / FAIL | Người: lặp xin lỗi nhưng 50.000đ khác ledger 35.000đ. | Chấm thông tin có ích, không thưởng độ dài hay lặp lời xin lỗi. |
| HL-035 | PASS / FAIL | Người: số tiền 50.000đ khác ledger 35.000đ. | Yêu cầu nhận diện mâu thuẫn số tiền trước khi đánh giá helpfulness. |

Các kết luận audit dựa trên reply và note/nhãn công khai, không phải một vòng gán nhãn người độc lập mới. Cần rubric sửa đổi, người gán nhãn mới và tập held-out trước khi dùng judge trong pilot thật. κ không xác định phải FAIL calibration. Chưa gọi LLM thật hoặc tuyên bố rubric mới đã cải thiện số đo.
