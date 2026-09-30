# Rules — ngưỡng và cách diễn giải

*Tài liệu chuẩn của mọi rule cứng trong hệ thống. Code phải phản chiếu tài liệu này:*
- *Rule diễn giải + ngưỡng hiển thị → `static/index.html` (INFO, reading(), statusChip(), STALE_LIMIT, UP_GOOD)*
- *Sanity range khi thu thập → `collectors/base.py` (SANITY)*

*Khi đổi một ngưỡng: sửa doc này trước, ghi vào Changelog cuối file, rồi sửa code.*

## 1. Nguyên tắc chung

1. **Rule chỉ định vị, không dự đoán.** Mọi câu diễn giải nói "đang ở đâu so với cái gì", không bao giờ nói "sẽ đi đâu".
2. **Phát hiện bằng rule, diễn giải bằng chữ viết sẵn.** Không có suy luận động nào ở tầng này (AI chỉ xuất hiện ở giai đoạn 2, đứng trên các reading đã chuẩn hóa).
3. **Delta chỉ tô màu khi hướng có nghĩa tốt/xấu rõ ràng** với nhà đầu tư crypto (bảng UP_GOOD, mục 5). Đại lượng dòng chảy (ETF flow) không hiển thị delta — dùng tổng 7 phiên.

## 2. Ngưỡng trạng thái (status chip)

| Chỉ số | Ngưỡng | Trạng thái | Căn cứ |
|---|---|---|---|
| Funding (%/8h) | ≥ 0.10 | Quá nóng ⚠ | ~110%/năm phí đòn bẩy — lịch sử các cụm funding này hay kết thúc bằng long squeeze |
| | 0.05–0.10 | Nóng ⚠ | Gấp ~5 lần mức nền 0.01 |
| | < 0 | Âm | Short trả phí — hiếm, đáng chú ý |
| Fear & Greed | ≥ 75 | Extreme greed ⚠ | Ngưỡng chuẩn của Alternative.me |
| | ≤ 25 | Extreme fear ◆ | Vùng contrarian |

## 3. Ngưỡng diễn giải (reading)

| Chỉ số | Rule | Căn cứ |
|---|---|---|
| Giá BTC/ETH | So MA200: ±3% quanh MA = "sát đường phân định"; ngoài đó là xu hướng tăng/giảm dài hạn | MA200 là thước trend-following đơn giản, ít nhiễu nhất; ±3% tránh nhấp nháy khi giá bám MA |
| MVRV BTC | <1 vùng đáy · 1–2 trung tính · 2–3 ấm · >3 vùng đỉnh | Thống kê 2 chu kỳ 2017–2025: đáy 0.75–0.95, đỉnh 3.0–4.7 |
| DXY | Δ30d ±0.5 điểm phân định mạnh lên/yếu đi/đi ngang | Biến động nền của broad index ~0.3–0.5/tháng |
| 10Y | ≥4.5% ngặt · 3.5–4.5 trung bình · <3.5 thuận lợi; Δ30d ±0.15pp cho xu hướng | Vùng 4.5%+ là mức thắt chặt thực tế của chu kỳ 2022–2025 |
| Fed funds | Lãi suất thực = Fed funds − CPI YoY: ≥1pp thắt chặt · 0–1 thắt chặt nhẹ · <0 kích thích | Định nghĩa kinh điển về chính sách thực dương/âm |
| CPI | Khoảng cách tới mục tiêu 2% của Fed; ≤0.3pp coi là "sát mục tiêu" | Mục tiêu công khai của Fed |
| M2 / Net liquidity | Chỉ đọc hướng (Δ30d hoặc đầu-cuối chuỗi): mở rộng/thu hẹp | Mức tuyệt đối không có ngưỡng ý nghĩa; hướng mới là tín hiệu |
| Cung stablecoin | Δ30d ±1% phân định mở rộng/đi ngang/thu hẹp | Nhiễu nền của tổng cung ~0.5%/tháng |
| BTC dominance | ≥55% co cụm về BTC · 45–55 cân bằng · <45 lan sang alt; Δ7d ≤ −1pp = "giảm nhanh" | Mốc lịch sử các mùa alt 2021 (dominance thủng 45–50) |
| USDT dominance | Δ7d ±0.15pp phân định risk-off/risk-on/đi ngang | Biến động nền ~0.1pp/tuần |
| Open interest | Percentile trong 30 ngày; ≥80% kèm cảnh báo "nhiên liệu biến động" | OI cao + funding nóng = điều kiện cascade thanh lý |
| ETF flows | Tổng 7 phiên gần nhất, mua ròng/bán ròng | Chuỗi ngày có ý nghĩa hơn 1 ngày; 7 phiên ~ 1.5 tuần giao dịch |
| Vị trí range 90d | percentile ≥80 "vùng cao" · ≤20 "vùng thấp" · giữa | Quy ước ngũ phân vị |

## 4. Ngưỡng "dữ liệu cũ" (STALE_LIMIT)

Theo nhịp công bố thật của nguồn — nhãn ⏱ chỉ xuất hiện khi collector *thực sự* trục trặc:

| Nhóm | Ngưỡng | Lý do |
|---|---|---|
| Nguồn theo giờ (giá, dominance, funding, OI, stablecoin) | 3h | Cron mỗi giờ + dư 2 lần thất bại |
| Nguồn theo ngày (F&G) | 72h | Cron mỗi ngày + dư |
| ETF flows | 120h | Chỉ có ngày giao dịch, nghỉ cuối tuần + lễ |
| DXY | 14 ngày | FRED công bố trễ ~1 tuần |
| 10Y, Fed funds | 6 ngày | FRED trễ 1–2 ngày + cuối tuần |
| Net liquidity | 12 ngày | WALCL là series tuần |
| MVRV | 4 ngày | CoinMetrics trễ 1–2 ngày |
| M2, CPI | 70 ngày | Số liệu tháng, công bố trễ ~6 tuần |

## 5. Hướng delta (UP_GOOD) — tăng là tốt hay xấu cho crypto?

| Tăng = tốt (xanh) | Tăng = xấu (đỏ) | Trung tính (không tô màu) |
|---|---|---|
| Giá BTC/ETH, tổng vốn hóa, M2, net liquidity, cung stablecoin, ETF flows | DXY, 10Y, Fed funds, CPI, USDT dominance | BTC dominance, F&G, funding, OI, MVRV |

Trung tính vì: hướng không có nghĩa tốt/xấu đơn trị (dominance tùy vị thế BTC hay alt; funding/OI/MVRV đọc theo zone, không theo hướng). Delta tròn về 0 khi hiển thị → luôn trung tính.

## 6. Sanity range khi thu thập (collectors/base.py)

Giá trị ngoài khoảng bị loại và cảnh báo — thà thiếu còn hơn lưu rác. Khoảng đặt RỘNG (bắt lỗi đơn vị/parse, không bắt biến động thật). Đã từng bắt được lỗi thật: net_liquidity âm ~$580k tỷ do nhầm đơn vị WTREGEN (triệu vs tỷ USD) — xem Changelog.

| Metric | Khoảng | Metric | Khoảng |
|---|---|---|---|
| price_btc | 1k – 5M | dxy | 70 – 160 |
| price_eth | 50 – 100k | us10y, fed_funds | 0 – 15 |
| btc_dominance | 10 – 90 | m2 | 1k – 100k (tỷ USD) |
| usdt_dominance | 0.5 – 25 | cpi_yoy | −5 – 25 |
| total_mcap | $100B – $100T | net_liquidity | 2k – 12k (tỷ USD) |
| fear_greed | 0 – 100 | mvrv_btc | 0.3 – 10 |
| funding | −1 – 1 (%/8h) | stablecoin_mcap | $50B – $1.5T |
| oi_btc_usd | $1B – $1T | etf_flow_btc/eth | ±5000 / ±3000 (triệu USD) |

## 7. Màu tín hiệu của tile (signalFor)

Mỗi tile mang một tín hiệu tổng: **xanh lá** (tích cực cho vị thế crypto), **đỏ** (tiêu cực), **trung tính** (xanh dương — giữ mặc định). Màu áp lên viền trái tile + sparkline.

Nguyên tắc:

1. **Màu phản chiếu kết luận của reading, không tô theo hướng tăng/giảm thô** — cùng ngưỡng với mục 3, không có ngưỡng riêng.
2. **Trung tính là mặc định, phải "kiếm được" màu** — đa số tile xanh dương thì mắt mới bắt được tile đỏ/xanh lá. Nếu cả dashboard đỏ rực hoặc xanh rực, hệ màu mất tác dụng.
3. **Không bao giờ màu-đơn-độc**: câu diễn giải luôn nói cùng kết luận bằng chữ.

| Tín hiệu | Điều kiện (theo ngưỡng mục 3) |
|---|---|
| Giá BTC/ETH | good: ≥+3% trên MA200 · bad: ≤−3% dưới |
| Tổng vốn hóa | theo dấu Δ7d |
| F&G | bad: ≥75 (extreme greed) · good: ≤25 (contrarian) |
| DXY | bad: Δ30d>+0.5 · good: <−0.5 |
| 10Y | bad: Δ30d≥+0.15pp · good: ≤−0.15pp |
| Fed funds | bad: lãi suất thực ≥1pp · good: <0 |
| M2, Net liquidity | theo hướng mở rộng/thu hẹp |
| CPI | good: sát mục tiêu 2% · bad: đang tăng lại |
| USDT.D | bad: Δ7d≥+0.15pp · good: ≤−0.15pp |
| Cung stablecoin | good: mở rộng ≥1%/30d · bad: thu hẹp ≤−1% |
| MVRV | bad: ≥3 (vùng đỉnh) · good: <1 (vùng đáy) |
| Funding | bad: ≥0.05 (nóng); âm KHÔNG phải bad — chỉ thận trọng |
| OI | bad: percentile 30d ≥80 (nhiên liệu biến động); không có good |
| ETF flows | theo dấu tổng 7 phiên |
| BTC dominance | luôn trung tính (tốt/xấu tùy vị thế BTC hay alt) |

## 8. Rule cảnh báo (alerts.py)

Cảnh báo phát bằng rule cứng 100% — AI không bao giờ là nguồn kích hoạt. Mỗi rule có cooldown để không spam khi điều kiện kéo dài.

| Rule | Điều kiện | Cooldown | Căn cứ |
|---|---|---|---|
| funding_hot | funding BTC ≥ 0.05%/8h | 12h | Ngưỡng "nóng" mục 2; 12h = 1.5 kỳ funding |
| fng_extreme | F&G ≥ 75 hoặc ≤ 25 | 24h | Vùng cực đoan mục 2; tâm lý đổi theo ngày |
| usdt_spike | USDT.D tăng ≥ +0.3pp/24h | 24h | Gấp đôi ngưỡng risk-off tuần (0.15pp) nén trong 1 ngày |
| etf_flip | Tổng 7 phiên ETF BTC đổi dấu | 48h | Đảo chiều dòng tổ chức — sự kiện hiếm, đáng biết ngay |

## 9. Prompt daily brief (daily_brief.py)

Ràng buộc trong prompt phản chiếu nguyên tắc mục 1: cấm dự đoán giá, cấm khuyến nghị mua/bán, cấm số ngoài snapshot, chỉ định vị. AI nhận snapshot đã có signal/note tính sẵn (signals.py — cùng ngưỡng mục 3/§7), đầu ra ≤200 từ theo cấu trúc REGIME / Trạng thái / Đáng chú ý / Ngược chiều. Đổi ràng buộc prompt = sửa mục này trước, rồi sửa `INSTRUCTION` trong daily_brief.py.

## Changelog

- **2026-09-28** — Bản đầu tiên: chuyển toàn bộ rule từ code ra doc. Cùng ngày: sửa lỗi đơn vị WTREGEN (net_liquidity) do sanity check phát hiện; bỏ delta cho ETF flows (nhiễu bậc hai); nới STALE_LIMIT cho FRED/ETF theo nhịp công bố thật.
- **2026-09-28 (chiều)** — Thêm mục 7: màu tín hiệu tile (signalFor) theo góp ý UX — tile đóng box riêng, viền trái + sparkline mang màu xanh lá/đỏ theo kết luận reading, trung tính giữ xanh dương.
- **2026-09-28 (tối)** — Phase 2: thêm mục 8 (rule cảnh báo + cooldown) và mục 9 (ràng buộc prompt daily brief). Lưu ý: ngưỡng phân loại giờ sống ở HAI bản code (static/index.html cho UI, signals.py cho brief) — cả hai phản chiếu doc này, sửa ngưỡng phải sửa cả ba chỗ.
