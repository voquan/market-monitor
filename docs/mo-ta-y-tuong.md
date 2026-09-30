# Market Monitor — Dashboard theo dõi thị trường crypto

*Ngày khởi tạo: 28/09/2026*

## Vấn đề

Đầu tư crypto đòi hỏi theo dõi rất nhiều yếu tố phân mảnh trên nhiều nguồn khác nhau:

- **Kinh tế vĩ mô**: DXY, lợi suất trái phiếu, lạm phát, chính sách tiền tệ của Fed
- **Chính trị / pháp lý**: quyết định của SEC, quy định các nước lớn, sự kiện địa chính trị
- **Dòng tiền toàn cầu**: ETF flows, thanh khoản toàn cầu (M2), khẩu vị rủi ro
- **Dữ liệu onchain & thị trường**: BTC dominance, USDT dominance, Fear & Greed, funding rate, bản đồ thanh lý, exchange netflow

Hiện tại phải mở 6–8 tab (TradingView, Coinglass, Alternative.me, FRED, CryptoQuant...) mới có bức tranh đầy đủ. Sự phân mảnh này dẫn đến ra quyết định theo cảm xúc thay vì theo tổng thể dữ liệu.

## Giải pháp

Một dashboard cá nhân gom tất cả chỉ số quan trọng về một màn hình, kết hợp lớp AI **tổng hợp và cảnh báo** (không phải dự đoán giá).

### Nguyên tắc cốt lõi về vai trò của AI

Không có mô hình nào dự đoán đáng tin xu hướng trung–dài hạn của crypto:

1. Thị trường bị chi phối bởi sự kiện không nằm trong dữ liệu lịch sử (tweet, sập sàn, quyết định pháp lý).
2. BTC mới có ~4 chu kỳ — không đủ mẫu thống kê để học quy luật.
3. Rủi ro hành vi: tin "AI của mình" quá mức → giữ lệnh lâu hơn, bỏ qua tín hiệu ngược. Công cụ dự đoán sai còn tệ hơn không có công cụ.

Thay vào đó, AI đảm nhận 4 vai trò trung thực và hữu ích hơn:

| Vai trò | Mô tả |
|---|---|
| **Daily brief** | Đọc toàn bộ chỉ số + tin tức, viết tóm tắt "thị trường đang ở trạng thái nào, gì thay đổi so với hôm qua" |
| **Regime detection** | "Các chỉ số hiện giống giai đoạn risk-on/risk-off nào trong quá khứ, khác biệt ở đâu" — không bao giờ là "giá sẽ đi đâu" |
| **Cảnh báo bất thường** | Funding rate quá nóng, USDT dominance tăng đột biến, ETF flows đảo chiều |
| **Devil's advocate** | Trước khi vào lệnh lớn, AI liệt kê các dữ kiện *ngược* với quan điểm của mình |

## Nguồn dữ liệu (đa số miễn phí)

| Nhóm | Chỉ số | Nguồn |
|---|---|---|
| Vĩ mô | DXY, lợi suất 10Y, Fed funds rate, M2, CPI | FRED API |
| Chính sách tiền tệ | Lịch FOMC, xác suất tăng/giảm lãi suất | CME FedWatch |
| Tâm lý | Fear & Greed Index | Alternative.me API |
| Cấu trúc thị trường | BTC dominance, USDT dominance, tổng vốn hóa | CoinGecko API |
| Phái sinh | Funding rate, open interest, bản đồ thanh lý | Coinglass (free tier), Binance API |
| Onchain | Exchange netflow, MVRV, stablecoin supply | CryptoQuant/Glassnode (free tier), Santiment |
| Dòng tiền tổ chức | ETF flows (IBIT, FBTC...) | Farside Investors |

## Lộ trình 3 giai đoạn

Mỗi giai đoạn tự nó đã có ích, không phụ thuộc giai đoạn sau:

1. **Dashboard thuần dữ liệu** (2–4 tuần ngoài giờ): gom chỉ số về một trang, cập nhật tự động. Dùng vài tuần để biết chỉ số nào *thực sự* cần nhìn.
2. **Lớp AI tổng hợp**: daily brief + cảnh báo bất thường, dùng Claude API đọc snapshot dữ liệu. Chi phí vài USD/tháng.
3. **Regime analysis**: chỉ làm khi đã dùng quen hai giai đoạn đầu.

## Giá trị chiến lược

Ngoài phục vụ đầu tư cá nhân, dự án có giá trị kép trong kế hoạch 5 năm (xem [ke-hoach-1M-USD-5-nam.md](../../../ke-hoach-1M-USD-5-nam.md)):

- **Portfolio/side-project** đúng chuyên môn fintech UX — nhiều dashboard trả phí (CryptoQuant, Glassnode) có UX tệ đáng ngạc nhiên.
- Tiềm năng trở thành **sản phẩm có thu** nếu làm tốt.

## Tài liệu liên quan

- [kien-truc.md](kien-truc.md) — phác thảo kiến trúc hệ thống
- [khung-danh-gia.md](khung-danh-gia.md) — khung 4 câu hỏi: thế nào là đủ thông tin
- [rules.md](rules.md) — toàn bộ ngưỡng và rule diễn giải
- [dau-tu-crypto.md](../../../dau-tu-crypto.md) — chiến lược đầu tư crypto tổng thể
