"""Binance Futures: funding rate + open interest. API công khai, không cần key."""
from datetime import datetime, timedelta, timezone

import db
from collectors import base

SOURCE = "binance"
API = "https://fapi.binance.com"


def run(conn):
    ts = db.now_iso()
    rows = []
    for sym, metric in [("BTCUSDT", "funding_btc"), ("ETHUSDT", "funding_eth")]:
        p = base.get_json(f"{API}/fapi/v1/premiumIndex", params={"symbol": sym})
        # lastFundingRate là tỷ lệ thập phân mỗi 8h -> đổi sang %/8h
        rows.append((ts, metric, float(p["lastFundingRate"]) * 100))

    oi = base.get_json(
        f"{API}/futures/data/openInterestHist",
        params={"symbol": "BTCUSDT", "period": "1h", "limit": 1},
    )
    if oi:
        rows.append((ts, "oi_btc_usd", float(oi[-1]["sumOpenInterestValue"])))
    return base.save(conn, SOURCE, rows)


def backfill(conn, days=90):
    rows = []
    # Funding lịch sử: 3 kỳ/ngày, limit 1000 ≈ 333 ngày
    for sym, metric in [("BTCUSDT", "funding_btc"), ("ETHUSDT", "funding_eth")]:
        hist = base.get_json(
            f"{API}/fapi/v1/fundingRate", params={"symbol": sym, "limit": 1000}
        )
        cutoff = datetime.now(timezone.utc) - timedelta(days=days)
        for item in hist:
            dt = datetime.fromtimestamp(item["fundingTime"] / 1000, tz=timezone.utc)
            if dt >= cutoff:
                rows.append((db.iso(dt), metric, float(item["fundingRate"]) * 100))
    # OI lịch sử: Binance chỉ giữ 30 ngày
    oi = base.get_json(
        f"{API}/futures/data/openInterestHist",
        params={"symbol": "BTCUSDT", "period": "1d", "limit": 30},
    )
    for item in oi:
        dt = datetime.fromtimestamp(item["timestamp"] / 1000, tz=timezone.utc)
        rows.append((db.iso(dt), "oi_btc_usd", float(item["sumOpenInterestValue"])))
    return base.save(conn, SOURCE, rows)
