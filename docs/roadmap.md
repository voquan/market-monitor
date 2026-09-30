# Roadmap & nhật ký dự án

*File này trả lời: đã làm gì, đang làm gì, sắp làm gì, và đã điều chỉnh gì (kèm lý do).
Quy ước: xong việc → tick ở đây; quyết định đáng nhớ → thêm dòng vào Nhật ký quyết định.
Phase chưa bắt đầu để thô CÓ CHỦ ĐÍCH — chỉ chi tiết hóa khi bắt tay vào làm.*

**Mục tiêu tổng:** gom mọi yếu tố tác động thị trường crypto về một dashboard, AI đóng vai tổng hợp/cảnh báo (không dự đoán) — phục vụ quyết định đầu tư trung–dài hạn. Chi tiết: [mo-ta-y-tuong.md](mo-ta-y-tuong.md).

---

## Phase 1 — Dashboard thuần dữ liệu ✅ (hoàn thành 28/09/2026)

- [x] Schema SQLite + 4 collectors nền (CoinGecko, F&G, Binance, FRED)
- [x] Dashboard 1 trang: 4 khối, sparkline, delta, sáng/tối, bảng dữ liệu
- [x] Scraper ETF flows (Farside qua cloudscraper) + sanity check toàn hệ thống
- [x] Lớp ngữ cảnh UX: reading rule-based + nút ⓘ + so chéo chỉ số (lãi suất thực)
- [x] Bổ sung theo khung 4 câu hỏi: MVRV (CoinMetrics), MA200, Fed net liquidity, cung stablecoin, ETF ETH
- [x] Tile box riêng + hệ màu tín hiệu xanh/đỏ (= kết luận reading)
- [x] Backfill lịch sử: F&G 2018→, MVRV 2017→, giá 365d, funding 90d
- [x] Bộ docs: khung-danh-gia, rules (+changelog), kien-truc, CLAUDE.md 2 cấp

**Còn nợ vận hành (làm khi bắt đầu dùng hàng ngày):**
- [ ] Cấu hình cron thu thập tự động (mẫu trong README)
- [ ] Backup định kỳ `data/market.db`

## Phase 2 — Lớp AI tổng hợp 🟡 (code xong 28/09/2026, chờ kích hoạt)

*Thiết kế: [kien-truc.md](kien-truc.md) §4. Rule cảnh báo + prompt: [rules.md](rules.md) §8–9.*

- [x] `signals.py`: snapshot JSON với signal/note tính sẵn bằng rule (AI không suy từ số thô)
- [x] `providers.py`: tầng gọi model swap được — claude_cli (mặc định, $0) / claude_api / gemini
- [x] `daily_brief.py`: prompt cố định (cấm dự đoán) → bảng `briefs` → gửi Telegram; có --dry-run
- [x] `alerts.py`: 4 rule cứng + cooldown → bảng `alerts` → Telegram
- [x] Dashboard: /api/brief + render brief (regime chip, alerts) vào ô "Regime · AI brief"
- [x] Kích hoạt provider: **Gemini free tier** (user chọn thay vì cài Claude CLI) — brief thật đầu tiên chạy 28/09/2026, model pin `gemini-3.1-flash-lite` trong .env
- [ ] Thêm cron: brief 7h15 sáng + alerts mỗi giờ (mẫu trong README) — cùng lúc với cron thu thập
- [ ] (Tùy chọn) Tạo Telegram bot + điền token vào .env để nhận brief/cảnh báo trên điện thoại

## Phase 3 — Regime analysis 📦 (xa, để thô có chủ đích)

So sánh trạng thái hiện tại với các giai đoạn lịch sử tương đồng ("giống/khác gì", không phải "giá đi đâu"). Chỉ chi tiết hóa sau khi Phase 2 chạy ổn ≥1 tháng và lịch sử dominance tự tích lũy đủ ~6 tháng.

## Vận hành / hạ tầng (track song song, làm khi có nhu cầu)

- [x] Đẩy code lên GitHub: https://github.com/voquan/market-monitor (30/09/2026; .env và data/ không lên repo)
- [ ] GitHub Actions cron cho collectors + brief (cần thêm secrets FRED_API_KEY, GEMINI_API_KEY vào repo settings)
- [ ] Nơi chứa dữ liệu khi chạy online: Turso, hoặc commit db vào repo private ([kien-truc.md](kien-truc.md) §1)
- [ ] Nơi xem dashboard online (Vercel/Fly, hoặc static export + GitHub Pages)
- Backlog chỉ số mới: xem [khung-danh-gia.md](khung-danh-gia.md) (FedWatch, exchange netflow, ETH/BTC...)

---

## Nhật ký quyết định

*Chỉ ghi quyết định có lý do đáng nhớ — thứ mà AI/người đến sau có thể muốn "sửa lại" nếu không biết bối cảnh. Đổi ngưỡng hiển thị ghi ở [rules.md](rules.md) changelog, không ghi ở đây.*

| Ngày | Quyết định | Lý do |
|---|---|---|
| 28/09 | AI đóng vai tổng hợp/cảnh báo, **không dự đoán giá** | Nguyên tắc nền của cả dự án — 4 chu kỳ BTC không đủ mẫu thống kê; công cụ dự đoán sai nguy hiểm hơn không có. Xem mo-ta-y-tuong |
| 28/09 | Local dùng FastAPI + HTML tĩnh thay vì Next.js như phác thảo ban đầu | Một ngôn ngữ, không build step; JSON API đã tách nên port giao diện sau này rẻ |
| 28/09 | Farside scrape qua cloudscraper, collector được phép fail có thông báo | Farside chặn Cloudflare (403 với requests); chấp nhận mong manh vì là nguồn ETF flows miễn phí duy nhất |
| 28/09 | Sanity range đặt ở collector, loại giá trị thay vì lưu | Đã bắt được lỗi thật ngay ngày đầu: nhầm đơn vị WTREGEN → net_liquidity âm $580k tỷ. "Thà thiếu còn hơn sai" |
| 28/09 | Diễn giải bằng rule cứng viết sẵn, không phải AI | Rule không ảo giác; AI giai đoạn 2 sẽ đứng TRÊN các reading đã chuẩn hóa, không thay chúng |
| 28/09 | Màu tín hiệu = kết luận reading, trung tính là mặc định | Màu không bao giờ nói khác chữ; đa số trung tính thì tile có màu mới nổi bật (rules.md §7) |
| 28/09 | ETF flows không hiển thị delta ngày | Delta của đại lượng dòng chảy là nhiễu bậc hai; dùng tổng 7 phiên |
| 28/09 | Quy trình doc-trước-code-sau cho mọi rule | Để 6 tháng sau còn biết vì sao funding 0.05 là "nóng"; code phản chiếu docs/rules.md |
| 28/09 | Provider brief mặc định = Claude Code headless (claude_cli), tách tầng providers.py | Free thực tế (subscription sẵn có), chất lượng cao nhất; đổi provider = đổi env. Máy chạy cron phải đăng nhập Claude Code |
| 28/09 | Snapshot cho AI mang signal/note tính sẵn (signals.py), không đưa số thô | Model nhỏ/free đủ dùng, giảm rủi ro bịa số; đánh đổi: ngưỡng tồn tại ở 2 bản code (JS + Python) cùng phản chiếu rules.md |
| 28/09 | Brief chạy Gemini `gemini-3.1-flash-lite` (pin trong .env), không dùng alias `-latest` | User chưa muốn cài Claude CLI; các model flash thường 503 "high demand" với request dài trên free tier, flash-lite ổn định; key dạng `AQ.*` chỉ nhận qua header `x-goog-api-key` |
