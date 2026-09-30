# Market Monitor — hướng dẫn cho AI session mới

Dashboard cá nhân theo dõi thị trường crypto (vĩ mô, định giá chu kỳ, dòng tiền, tâm lý) + lớp AI tổng hợp. Python + SQLite + FastAPI + 1 trang HTML tĩnh, chạy local.

## Đọc gì trước

1. `README.md` — bảng chỉ dẫn tài liệu, cách chạy, cấu trúc code
2. `docs/khung-danh-gia.md` — khung 4 câu hỏi: tiêu chí thêm/bớt chỉ số
3. `docs/rules.md` — mọi ngưỡng hiển thị/diễn giải + changelog

## Trạng thái

**Nguồn chuẩn về tiến độ + việc cần làm + nhật ký quyết định: `docs/roadmap.md`** — đọc file đó, đừng suy từ code. Tóm tắt 1 dòng (28/09/2026): Phase 1 + Phase 2 hoạt động — brief chạy Gemini free tier (model pin trong `.env`), còn thiếu cron (thu thập + brief + alerts đều đang chạy tay); local port 8388.

Khi hoàn thành việc gì: tick trong `docs/roadmap.md`; quyết định có lý do đáng nhớ → thêm vào Nhật ký quyết định trong đó; thay đổi lớn → cập nhật dòng tóm tắt ở trên.

## Quy ước bắt buộc

1. **Doc trước, code sau**: đổi ngưỡng/rule nào → sửa `docs/rules.md` + changelog TRƯỚC, rồi mới sửa code. Code phản chiếu doc, không ngược lại.
2. **Không dự đoán giá**: mọi rule/diễn giải chỉ định vị ("đang ở đâu so với cái gì"), không bao giờ "sẽ đi đâu". AI giai đoạn 2 cũng vậy.
3. **Màu = chữ**: màu tín hiệu (signalFor) phải trùng kết luận của câu diễn giải (reading). Không bao giờ màu-đơn-độc.
4. **Thà thiếu còn hơn sai**: collector fail phải kêu to (sanity check trong `collectors/base.py`), không im lặng dùng dữ liệu cũ.
5. **Thêm chỉ số mới** phải qua 4 tiêu chí trong `docs/khung-danh-gia.md`, chỉ số mới cần đủ bộ: SANITY (base.py) + METRICS (app.py) + INFO/reading/signalFor/STALE_LIMIT/UP_GOOD (index.html) + cập nhật `docs/rules.md`.

## Vận hành

- `data/market.db` là **tài sản** (lịch sử tự tích lũy, nhiều metric không lấy lại được từ free tier) — không xóa, không đụng khi refactor.
- Dashboard: mở http://localhost:8388 (hỗ trợ `?theme=light|dark` để test). Kiểm tra hiển thị bằng screenshot Chrome headless cả hai theme.
- Farside (etf_flows) đi qua cloudscraper — nguồn mong manh nhất, được phép fail có thông báo.
