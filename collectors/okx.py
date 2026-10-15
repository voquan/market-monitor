"""OKX Futures: funding rate + open interest. API công khai, không cần key.

Nguồn phái sinh từ 15/10/2026 — chọn bằng thực nghiệm (workflow probe từ
runner GitHub): Binance 451, Bybit 403, OKX/Kraken/Hyperliquid 200. OKX khớp
ngữ nghĩa nhất: funding chu kỳ 8h như Binance, OI có sẵn bằng USD.
Xem nhật ký quyết định trong docs/roadmap.md về vết gãy dữ liệu OI khi đổi sàn.
"""
from datetime import datetime, timedelta, timezone

import db
from collectors import base

SOURCE = "okx"
API = "https://www.okx.com"


def _get(path, params):
    data = base.get_json(f"{API}{path}", params=params)
    if data.get("code") != "0":
        raise RuntimeError(f"OKX code={data.get('code')}: {data.get('msg')}")
    return data["data"]


def run(conn):
    ts = db.now_iso()
    rows = []
    for inst, metric in [("BTC-USDT-SWAP", "funding_btc"), ("ETH-USDT-SWAP", "funding_eth")]:
        d = _get("/api/v5/public/funding-rate", {"instId": inst})[0]
        # fundingRate là tỷ lệ thập phân mỗi 8h -> đổi sang %/8h
        rows.append((ts, metric, float(d["fundingRate"]) * 100))
    oi = _get("/api/v5/public/open-interest", {"instType": "SWAP", "instId": "BTC-USDT-SWAP"})[0]
    rows.append((ts, "oi_btc_usd", float(oi["oiUsd"])))
    return base.save(conn, SOURCE, rows)


def backfill(conn, days=60):
    """Funding lịch sử (phân trang 100 kỳ/lần ~ 33 ngày). OI tự tích lũy forward."""
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    rows = []
    for inst, metric in [("BTC-USDT-SWAP", "funding_btc"), ("ETH-USDT-SWAP", "funding_eth")]:
        after = None
        for _ in range(4):  # tối đa 4 trang ~ 130 ngày, dư cho 60
            params = {"instId": inst, "limit": 100}
            if after:
                params["after"] = after
            page = _get("/api/v5/public/funding-rate-history", params)
            if not page:
                break
            for item in page:
                dt = datetime.fromtimestamp(int(item["fundingTime"]) / 1000, tz=timezone.utc)
                if dt >= cutoff:
                    rows.append((db.iso(dt), metric, float(item["fundingRate"]) * 100))
            after = page[-1]["fundingTime"]
            if datetime.fromtimestamp(int(after) / 1000, tz=timezone.utc) < cutoff:
                break
    return base.save(conn, SOURCE, rows)
