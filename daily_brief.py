#!/usr/bin/env python3
"""Daily brief: snapshot có signal sẵn -> AI tổng hợp -> bảng briefs (+ Telegram).

  python daily_brief.py             # tạo brief hôm nay (bỏ qua nếu đã có)
  python daily_brief.py --force     # tạo lại, ghi đè brief hôm nay
  python daily_brief.py --dry-run   # in prompt + snapshot, KHÔNG gọi model
  python daily_brief.py --provider gemini   # override BRIEF_PROVIDER

Chạy sau đợt collect buổi sáng (xem README phần cron).
"""
import json
import sys
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db
import providers
import signals
from alerts import send_telegram

INSTRUCTION = """Bạn là nhà phân tích thị trường crypto, viết brief buổi sáng bằng tiếng Việt cho một nhà đầu tư cá nhân trung–dài hạn.

Đầu vào (stdin/bên dưới): snapshot JSON các chỉ số, mỗi chỉ số đã có sẵn `signal` (good/bad/neutral cho vị thế crypto) và `note` (phân loại theo rule). Hãy TỔNG HỢP từ các facts này, không tự suy diễn thêm từ số thô.

RÀNG BUỘC CỨNG:
- CẤM dự đoán giá hay xu hướng ("sẽ tăng/giảm/đạt X").
- CẤM khuyến nghị mua/bán.
- CẤM đưa ra con số không có trong snapshot.
- Chỉ ĐỊNH VỊ: đang ở đâu, cái gì thay đổi, cái gì mâu thuẫn với cái gì.

ĐỊNH DẠNG ĐẦU RA (đúng cấu trúc này, tổng ≤ 200 từ):
REGIME: <một trong: risk-on | risk-off | chuyển pha | trung tính>

**Trạng thái**: 2–3 câu theo khung 4 câu hỏi (định giá / xu hướng / dòng tiền / tâm lý).

**Đáng chú ý**: 2–3 gạch đầu dòng về thay đổi lớn nhất so với 7–30 ngày trước.

**Ngược chiều**: 1–2 gạch đầu dòng về dữ kiện đang mâu thuẫn với bức tranh chung (devil's advocate)."""


def main():
    force = "--force" in sys.argv
    dry = "--dry-run" in sys.argv
    provider = None
    if "--provider" in sys.argv:
        provider = sys.argv[sys.argv.index("--provider") + 1]

    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    conn = db.connect()
    if not force and conn.execute("SELECT 1 FROM briefs WHERE date=?", (today,)).fetchone():
        print(f"Brief {today} đã có — dùng --force để tạo lại.")
        return

    snapshot = signals.build_snapshot()
    payload = json.dumps(snapshot, ensure_ascii=False, indent=1)

    if dry:
        print(INSTRUCTION)
        print("\n----- SNAPSHOT -----\n")
        print(payload)
        return

    content = providers.generate(INSTRUCTION, payload, provider)
    conn.execute(
        "INSERT OR REPLACE INTO briefs (date, content, snapshot) VALUES (?,?,?)",
        (today, content, payload),
    )
    conn.commit()
    conn.close()
    print(f"[o] Brief {today}:\n\n{content}")

    sent = send_telegram(f"📋 Market brief {today}\n\n{content}")
    if sent:
        print("\n[o] Đã gửi Telegram")


if __name__ == "__main__":
    main()
