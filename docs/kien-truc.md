# Market Monitor — Phác thảo kiến trúc

*Ngày: 28/09/2026 · Trạng thái: bản nháp đầu tiên, phục vụ giai đoạn 1–2 của [mo-ta-y-tuong.md](mo-ta-y-tuong.md)*

## Nguyên tắc thiết kế

1. **Đơn giản trước, mở rộng sau** — đây là công cụ cá nhân dùng hàng ngày, không phải sản phẩm SaaS ngay từ đầu. Mọi lựa chọn ưu tiên "chạy được, ít bảo trì".
2. **Tách phần thu thập khỏi phần hiển thị** — collector chạy độc lập theo lịch, dashboard chỉ đọc dữ liệu đã lưu. Dashboard không bao giờ gọi trực tiếp API bên ngoài (tránh rate limit, tránh phụ thuộc lúc mở trang).
3. **Dữ liệu lịch sử là tài sản** — lưu mọi snapshot từ ngày đầu. Regime analysis (giai đoạn 3) chỉ khả thi nếu có lịch sử của chính mình, vì nhiều free tier không cho truy vấn dữ liệu quá khứ.

## Tổng quan hệ thống

```
┌────────────────────────────────────────────────────────┐
│  COLLECTORS (chạy theo lịch — cron / GitHub Actions)   │
│  fred.py · coingecko.py · coinglass.py · feargreed.py  │
│  binance.py · etf_flows.py · fedwatch.py               │
└──────────────────────┬─────────────────────────────────┘
                       ▼
              ┌─────────────────┐
              │  SQLite (data/)  │   bảng: metrics, briefs, alerts
              └───┬─────────┬───┘
                  ▼         ▼
     ┌────────────────┐  ┌──────────────────────────┐
     │  DASHBOARD      │  │  AI LAYER (giai đoạn 2)  │
     │  Next.js        │  │  snapshot → Claude API   │
     │  đọc SQLite     │  │  → daily brief + alerts  │
     └────────────────┘  │  → Telegram bot           │
                          └──────────────────────────┘
```

## 1. Tầng thu thập (collectors)

Mỗi nguồn là một script Python độc lập, cùng chung một interface: fetch → chuẩn hóa → ghi vào bảng `metrics`. Một script hỏng không kéo sập các script khác.

| Collector | Chỉ số | Tần suất | Ghi chú |
|---|---|---|---|
| `fred.py` | DXY, 10Y yield, Fed funds, M2, CPI | 1 lần/ngày | API key miễn phí, rất ổn định |
| `coingecko.py` | BTC/USDT dominance, total mcap, giá BTC/ETH | mỗi giờ | Free tier 30 calls/phút — quá đủ |
| `feargreed.py` | Fear & Greed Index | 1 lần/ngày | Alternative.me, không cần key |
| `binance.py` | Funding rate, open interest | mỗi giờ | API công khai, không cần key |
| `coinglass.py` | Bản đồ thanh lý, OI tổng hợp | mỗi giờ | Free tier hạn chế; có thể thay bằng Binance-only lúc đầu |
| `etf_flows.py` | ETF flows BTC + ETH | 1 lần/ngày | Farside — scrape qua cloudscraper (Cloudflare), **điểm mong manh nhất**, được phép fail có thông báo |
| `coinmetrics.py` | MVRV BTC (định giá chu kỳ) | 1 lần/ngày | CoinMetrics community API, miễn phí, lịch sử từ 2017 |
| `fedwatch.py` | Xác suất lãi suất FOMC | — | **Chưa làm** — CME render bằng JS, cần headless browser (backlog) |

*Bổ sung 09/2026: `coingecko.py` thu thêm cung stablecoin (USDT+USDC); `fred.py` tính thêm Fed net liquidity (WALCL − RRP − TGA, chú ý đơn vị từng series); `app.py` tính MA200 cho giá từ lịch sử trong DB. Căn cứ chọn chỉ số: [khung-danh-gia.md](khung-danh-gia.md).*

**Lịch chạy — hai lựa chọn:**

- **Phương án A (khuyến nghị bắt đầu): GitHub Actions cron** — repo private, chạy miễn phí, commit dữ liệu vào repo hoặc ghi lên SQLite/Turso. Không cần máy bật 24/7, có log sẵn.
- **Phương án B: cron/launchd trên máy cá nhân** — đơn giản nhất nhưng lệ thuộc máy đang bật; phù hợp nếu có Mac mini/server ở nhà.

## 2. Tầng lưu trữ

**SQLite** — một file duy nhất, không cần vận hành database server. Schema tối giản:

```sql
CREATE TABLE metrics (
  ts          TEXT NOT NULL,      -- ISO 8601 UTC
  source      TEXT NOT NULL,      -- 'fred', 'coingecko'...
  metric      TEXT NOT NULL,      -- 'btc_dominance', 'dxy'...
  value       REAL,
  meta        TEXT,               -- JSON phụ (đơn vị, raw payload nếu cần)
  PRIMARY KEY (ts, source, metric)
);

CREATE TABLE briefs (               -- giai đoạn 2
  date        TEXT PRIMARY KEY,
  content     TEXT NOT NULL,        -- markdown do AI viết
  snapshot    TEXT NOT NULL         -- JSON dữ liệu đầu vào (để audit lại)
);

CREATE TABLE alerts (               -- giai đoạn 2
  ts          TEXT NOT NULL,
  rule        TEXT NOT NULL,        -- 'funding_overheat', 'usdt_dom_spike'...
  message     TEXT NOT NULL,
  acknowledged INTEGER DEFAULT 0
);
```

Khi nào cần nâng cấp: chỉ khi muốn truy cập từ nhiều thiết bị mà không muốn sync file → chuyển sang **Turso** (SQLite hosted, free tier rộng) hoặc Postgres trên Supabase. Schema giữ nguyên.

## 3. Tầng dashboard

*Đã triển khai (09/2026): giai đoạn chạy local dùng **FastAPI + 1 trang HTML tĩnh** (static/index.html, sparkline SVG tự vẽ, không build step) — một ngôn ngữ duy nhất cho cả collectors lẫn dashboard, không cần node_modules. Khi lên online có thể giữ nguyên hoặc port sang Next.js; JSON API (`/api/summary`) đã tách sẵn nên chỉ là chuyện thay giao diện.*

Phương án ban đầu cho bản online: **Next.js + Tailwind + Recharts/Tremor**, đọc SQLite trực tiếp qua server components. Deploy Vercel (free) hoặc chạy local.

Layout một màn hình, 4 khối theo thứ tự ưu tiên đọc:

```
┌─────────────────────────────────────────────────────┐
│ ① HEADER STRIP — trạng thái tổng: giá BTC, biến động │
│   24h, Fear&Greed, và AI regime tag (gđ 2)           │
├──────────────────────────┬──────────────────────────┤
│ ② VĨ MÔ                  │ ③ CẤU TRÚC THỊ TRƯỜNG     │
│   DXY · 10Y · Fed funds  │   BTC.D · USDT.D · mcap  │
│   M2 · lịch FOMC          │   sparkline 90 ngày       │
├──────────────────────────┼──────────────────────────┤
│ ④ PHÁI SINH & DÒNG TIỀN  │ ⑤ DAILY BRIEF (gđ 2)      │
│   funding · OI · ETF flow │   tóm tắt AI + alerts     │
└──────────────────────────┴──────────────────────────┘
```

Nguyên tắc UX (vùng này là sở trường, ghi lại vài quyết định nền):

- Mỗi chỉ số hiển thị **giá trị hiện tại + xu hướng 7/30/90 ngày** (sparkline), không chỉ con số tĩnh — bối cảnh quan trọng hơn giá trị tuyệt đối.
- Mã màu theo **ngưỡng ý nghĩa** (vd. funding > 0.05%/8h = nóng), không theo tăng/giảm đơn thuần.
- Không realtime từng giây — dashboard này phục vụ quyết định trung–dài hạn, refresh theo giờ là đủ và giúp *giảm* thôi thúc nhìn giá liên tục.

## 4. Tầng AI (giai đoạn 2)

*Đã triển khai 28/09/2026 với một nâng cấp so với phác thảo: snapshot gửi cho AI mang signal/note đã tính sẵn bằng rule (signals.py) thay vì số thô, và tầng provider tách riêng (providers.py) — mặc định Claude Code headless (chi phí biên $0), swap được sang Gemini free hoặc Claude API qua env. Chi tiết rule: rules.md §8–9.*

Một script `daily_brief.py` chạy sau đợt collect buổi sáng:

1. Query SQLite → dựng **snapshot JSON**: giá trị hiện tại + delta 1d/7d/30d của mọi chỉ số.
2. Gửi snapshot cho **Claude API** (Sonnet là đủ, ~1–2k token/ngày → dưới $2/tháng) với prompt cố định: tóm tắt trạng thái, nêu thay đổi đáng kể, gắn regime tag, liệt kê rủi ro ngược chiều. Prompt cấm dự đoán giá.
3. Ghi kết quả vào bảng `briefs`, hiển thị trên dashboard.
4. **Alerts** chạy bằng rule thuần (không cần AI): ngưỡng cứng trên funding, USDT.D, ETF flows... Khi kích hoạt → gửi **Telegram bot** (miễn phí, 15 phút setup). AI chỉ viết phần giải thích ngữ cảnh đính kèm.

Tách bạch quan trọng: **phát hiện bất thường bằng rule, diễn giải bằng AI.** Rule không bao giờ "ảo giác"; AI không bao giờ là nguồn kích hoạt cảnh báo.

## 5. Chi phí & rủi ro vận hành

**Chi phí:** $0 hạ tầng (GitHub Actions + Vercel + Turso free tier) + ~$2/tháng Claude API. Nâng cấp duy nhất đáng cân nhắc về sau: Coinglass paid (~$29/tháng) nếu cần liquidation map chi tiết.

**Rủi ro chính:**

| Rủi ro | Đối sách |
|---|---|
| Scraper (Farside, FedWatch) vỡ khi site đổi HTML | Mỗi collector tự kiểm tra sanity (giá trị null/quá lệch) và bắn Telegram khi fail — thà biết dữ liệu thiếu còn hơn nhìn dữ liệu cũ mà tưởng mới |
| Free tier API đổi điều khoản | Interface collector đã chuẩn hóa, thay nguồn chỉ sửa 1 file |
| Bỏ bê sau vài tuần (rủi ro thật nhất của side-project) | Giai đoạn 1 giới hạn đúng 7 collectors + 1 trang; Telegram brief hàng sáng kéo mình quay lại dashboard |

## Thứ tự triển khai giai đoạn 1

1. Repo + schema SQLite + collector đầu tiên (`coingecko.py` — dễ nhất, không cần key)
2. Thêm `fred.py`, `feargreed.py`, `binance.py` (nhóm ổn định, không scrape)
3. Dashboard Next.js đọc 4 nguồn trên — **đến đây đã dùng được hàng ngày**
4. Thêm 3 collector còn lại (nhóm scrape) + sanity check + Telegram khi fail
5. Chạy ổn 2–3 tuần → bắt đầu giai đoạn 2 (daily brief)
