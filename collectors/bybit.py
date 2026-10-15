"""Bybit Futures: funding rate + open interest. API công khai, không cần key.

Thay Binance từ 15/10/2026 vì Binance chặn IP datacenter Mỹ (HTTP 451) —
GitHub Actions không gọi được. Xem nhật ký quyết định trong docs/roadmap.md:
OI đổi sàn nên mức không so sánh được với lịch sử Binance trước đó.
"""
from datetime import datetime, timedelta, timezone

import db
from collectors import base

SOURCE = "bybit"
API = "https://api.bybit.com"


def _ticker(symbol):
    data = base.get_json(
        f"{API}/v5/market/tickers", params={"category": "linear", "symbol": symbol}
    )
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit retCode={data.get('retCode')}: {data.get('retMsg')}")
    return data["result"]["list"][0]


def run(conn):
    ts = db.now_iso()
    rows = []
    for sym, metric in [("BTCUSDT", "funding_btc"), ("ETHUSDT", "funding_eth")]:
        t = _ticker(sym)
        # fundingRate là tỷ lệ thập phân mỗi 8h -> đổi sang %/8h
        rows.append((ts, metric, float(t["fundingRate"]) * 100))
        if sym == "BTCUSDT":
            rows.append((ts, "oi_btc_usd", float(t["openInterestValue"])))
    return base.save(conn, SOURCE, rows)


def backfill(conn, days=60):
    """Funding lịch sử (Bybit cho tối đa 200 kỳ ~ 66 ngày). OI tự tích lũy forward."""
    rows = []
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    for sym, metric in [("BTCUSDT", "funding_btc"), ("ETHUSDT", "funding_eth")]:
        data = base.get_json(
            f"{API}/v5/market/funding/history",
            params={"category": "linear", "symbol": sym, "limit": 200},
        )
        if data.get("retCode") != 0:
            raise RuntimeError(f"Bybit retCode={data.get('retCode')}: {data.get('retMsg')}")
        for item in data["result"]["list"]:
            dt = datetime.fromtimestamp(int(item["fundingRateTimestamp"]) / 1000, tz=timezone.utc)
            if dt >= cutoff:
                rows.append((db.iso(dt), metric, float(item["fundingRate"]) * 100))
    return base.save(conn, SOURCE, rows)
