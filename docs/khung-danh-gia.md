# Khung đánh giá xu thế — thế nào là "đủ thông tin"?

*Cập nhật: 28/09/2026. Đây là tài liệu chuẩn để trả lời câu hỏi "bộ chỉ số hiện tại có đủ không" — mọi đề xuất thêm/bớt chỉ số đối chiếu với khung này.*

## Bốn câu hỏi cốt lõi

Một khung đánh giá xu thế trung–dài hạn phải trả lời được đủ 4 câu hỏi. Chỉ số nào không phục vụ câu hỏi nào trong 4 câu này thì **không đưa lên dashboard**:

| # | Câu hỏi | Chỉ số đang trả lời | Trạng thái |
|---|---------|---------------------|------------|
| 1 | **Đắt hay rẻ?** (định giá chu kỳ) | MVRV BTC (CoinMetrics, từ 2017) | ✅ Đủ |
| 2 | **Xu hướng lên hay xuống?** (trend) | Giá BTC/ETH so MA200; vị trí trong range 90d | ✅ Đủ |
| 3 | **Tiền đang vào hay ra?** (dòng tiền) | Fed net liquidity, M2, cung stablecoin, ETF flows BTC+ETH, DXY | ✅ Đủ |
| 4 | **Đám đông đang ở đâu?** (tâm lý/vị thế) | Fear & Greed (từ 2018), funding, OI, BTC.D, USDT.D | ✅ Đủ |

Các chỉ số còn lại (Fed funds, 10Y, CPI) là **bối cảnh chính sách** — chúng giải thích *vì sao* câu 3 đang diễn ra như vậy.

## Nguyên tắc đọc: bằng chứng hội tụ

Không chỉ số nào tự nó đủ để kết luận. Đánh giá xu thế = đọc **sự hội tụ** của 4 câu trả lời:

- 4 câu cùng chiều → tín hiệu mạnh (hiếm khi xảy ra, thường ở đầu/cuối chu kỳ).
- Mâu thuẫn nhau (vd. định giá cao + tiền vẫn vào) → thị trường đang chuyển pha, đứng ngoài quan sát là một vị thế hợp lệ.
- **Không bao giờ** hành động chỉ vì một chỉ số chạm ngưỡng.

## Giới hạn đã biết (chấp nhận, không cần sửa bằng số liệu)

1. **Sự kiện chính trị/pháp lý/thiên nga đen** — không tồn tại dạng chỉ số. Là việc của lớp AI giai đoạn 2 (đọc tin tức).
2. **Lịch sử dominance & tổng vốn hóa** — free tier không cho quá khứ, tự tích lũy từ 09/2026. Sau ~6 tháng mới so sánh được dài hạn.
3. **MVRV là chỉ số chậm** — định vị pha chu kỳ (quý/năm), không dùng cho timing tuần.

## Backlog — chỉ thêm khi có nhu cầu thật khi sử dụng

| Chỉ số | Trả lời câu | Nguồn | Lý do chưa làm |
|---|---|---|---|
| Xác suất lãi suất FOMC (FedWatch) | 3 | CME (JS render) | Cần headless browser — công sức cao |
| Exchange netflow BTC | 4 | CryptoQuant/Glassnode | Free tier quá hạn chế |
| Tỷ giá ETH/BTC | 4 | Đã có sẵn số liệu | Tính được từ price_eth/price_btc, chờ nhu cầu |
| M2 toàn cầu (Mỹ+TQ+EU+Nhật) | 3 | Nhiều nguồn, kỳ công | Net liquidity Mỹ đã là proxy tốt |

## Tiêu chí thêm một chỉ số mới

Cả 4 điều kiện phải thỏa:

1. Trả lời trực tiếp một trong 4 câu hỏi cốt lõi.
2. Nguồn miễn phí hoặc rẻ, ổn định (ưu tiên API chính thức hơn scrape).
3. Có ngưỡng/cách đọc rõ ràng để viết được rule diễn giải (xem [rules.md](rules.md)).
4. Không trùng thông tin với chỉ số đã có (vd. không thêm RSI khi đã có vị trí so MA200).

Và một tiêu chí bớt: chỉ số nào **không bao giờ được đọc** sau 1–2 tháng sử dụng thì đưa ra khỏi màn hình chính.
