# Market Monitor

Dashboard cá nhân theo dõi thị trường crypto — vĩ mô, cấu trúc thị trường, định giá chu kỳ, phái sinh, dòng tiền.

**Tài liệu** (thư mục [docs/](docs/)):

| Tài liệu | Trả lời câu hỏi |
|---|---|
| [mo-ta-y-tuong.md](docs/mo-ta-y-tuong.md) | Vì sao có dự án này, vai trò của AI, lộ trình 3 giai đoạn |
| [kien-truc.md](docs/kien-truc.md) | Hệ thống được tổ chức thế nào, vì sao chọn như vậy |
| [khung-danh-gia.md](docs/khung-danh-gia.md) | Thế nào là "đủ thông tin"? Khung 4 câu hỏi + tiêu chí thêm/bớt chỉ số |
| [rules.md](docs/rules.md) | Mọi ngưỡng & rule diễn giải, căn cứ, changelog — **sửa rule thì sửa doc này trước** |
| [roadmap.md](docs/roadmap.md) | Đã làm gì, sắp làm gì, nhật ký quyết định — **nguồn chuẩn về tiến độ** |

## Cài đặt (1 lần)

```bash
cd tools/market_monitor
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# FRED key (miễn phí, cho nhóm chỉ số vĩ mô):
cp .env.example .env   # rồi điền FRED_API_KEY vào .env

# Nạp lịch sử 90 ngày (F&G nạp toàn bộ từ 2018):
python collect.py --backfill
```

Không có FRED key vẫn chạy được — nhóm vĩ mô sẽ hiện "chưa có dữ liệu".

## Dùng hàng ngày

```bash
source .venv/bin/activate
python collect.py                # thu thập dữ liệu mới
uvicorn app:app --port 8388      # mở dashboard: http://localhost:8388
```

Chạy từng nguồn: `python collect.py coingecko binance`. Thêm `-v` để xem traceback khi lỗi.

## Daily brief + cảnh báo (giai đoạn 2)

```bash
python daily_brief.py --dry-run   # xem prompt + snapshot, không gọi model
python daily_brief.py             # tạo brief hôm nay (hiện trên dashboard + Telegram)
python alerts.py                  # kiểm tra 4 rule cảnh báo (rules.md §8)
```

Provider chọn qua `BRIEF_PROVIDER` trong `.env` — **hiện đang dùng `gemini`** (free tier, model pin `gemini-3.1-flash-lite` vì flash thường 503 với request dài). Hai lựa chọn khác:

- `claude_cli` — dùng Claude Code subscription ($0), cần cài CLI 1 lần: `npm install -g @anthropic-ai/claude-code`
- `claude_api` — Claude API trả phí, cần `ANTHROPIC_API_KEY`

Telegram (tùy chọn): điền `TELEGRAM_BOT_TOKEN` + `TELEGRAM_CHAT_ID` theo hướng dẫn trong `.env.example` để nhận brief + cảnh báo trên điện thoại.

## Tự động thu thập (cron, macOS)

`crontab -e` rồi thêm (sửa đường dẫn cho đúng máy):

```cron
# Mỗi giờ: nguồn nhanh
0 * * * * cd /Volumes/Datas/Coding/inmag/tools/market_monitor && .venv/bin/python collect.py coingecko binance >> data/collect.log 2>&1
# 7h sáng hằng ngày: nguồn chậm
0 7 * * * cd /Volumes/Datas/Coding/inmag/tools/market_monitor && .venv/bin/python collect.py feargreed fred etf_flows coinmetrics >> data/collect.log 2>&1
# 7h15: daily brief (sau collect); 5 phút sau mỗi giờ: cảnh báo
15 7 * * * cd /Volumes/Datas/Coding/inmag/tools/market_monitor && .venv/bin/python daily_brief.py >> data/brief.log 2>&1
5 * * * * cd /Volumes/Datas/Coding/inmag/tools/market_monitor && .venv/bin/python alerts.py >> data/alerts.log 2>&1
```

`collect.py` exit code 1 khi có nguồn fail — kiểm tra `data/collect.log` nếu tile nào đó hiện "⏱ dữ liệu cũ".

## Cấu trúc

```
docs/           # toàn bộ tài liệu (xem bảng đầu README)
collectors/     # mỗi nguồn 1 file, độc lập, cùng interface run()/backfill()
  base.py       # fetch + sanity check (giá trị ngoài range bị loại, không lưu rác)
  coingecko.py  # giá BTC/ETH, dominance, tổng vốn hóa, cung stablecoin
  feargreed.py  # Fear & Greed (Alternative.me)
  binance.py    # funding rate, open interest
  fred.py       # DXY, 10Y, Fed funds, M2, CPI YoY, Fed net liquidity (cần FRED_API_KEY)
  etf_flows.py  # ETF flows BTC+ETH (scrape Farside — mong manh, được phép fail)
  coinmetrics.py # MVRV BTC (định giá chu kỳ on-chain, community API)
db.py           # SQLite: schema, deltas, chuỗi ngày cho sparkline
collect.py      # CLI điều phối collectors
signals.py      # snapshot có signal/note tính sẵn — đầu vào của daily brief
providers.py    # tầng gọi model (claude_cli / claude_api / gemini), swap qua env
daily_brief.py  # brief buổi sáng: snapshot -> AI -> bảng briefs -> Telegram
alerts.py       # 4 rule cảnh báo cứng (rules.md §8) -> bảng alerts -> Telegram
app.py          # FastAPI: /api/summary (kèm MA200), /api/brief + serve dashboard
static/index.html  # dashboard 1 trang (không cần build step); rule hiển thị theo docs/rules.md
data/market.db  # SQLite (gitignored) — TÀI SẢN, backup file này là đủ
```

## Ghi chú vận hành

- **Dữ liệu lịch sử là tài sản**: `data/market.db` chứa toàn bộ snapshot từ ngày đầu, cần cho regime analysis giai đoạn 3. Backup định kỳ (copy file là xong).
- **Nguồn scrape (etf_flows)**: khi Farside đổi HTML sẽ fail có thông báo — thà thiếu còn hơn hiển thị số cũ mà tưởng mới. Sửa hàm `_parse_all()` trong [collectors/etf_flows.py](collectors/etf_flows.py).
- **Chưa có** (xem backlog trong [docs/khung-danh-gia.md](docs/khung-danh-gia.md)): FedWatch, exchange netflow, Coinglass liquidation map.
- **Lên online sau này**: collectors chạy GitHub Actions cron + DB chuyển Turso, dashboard giữ nguyên HTML hoặc port sang Next.js — xem [docs/kien-truc.md](docs/kien-truc.md) §1.
