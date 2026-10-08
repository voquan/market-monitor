"""CoinGecko: giá BTC/ETH, dominance, tổng vốn hóa. Free, không cần key."""
from datetime import datetime, timezone

import db
from collectors import base

SOURCE = "coingecko"
API = "https://api.coingecko.com/api/v3"


STABLECOINS = ["tether", "usd-coin"]  # ~90% cung stablecoin toàn thị trường


def run(conn):
    ts = db.now_iso()
    g = base.get_json(f"{API}/global")["data"]
    prices = base.get_json(
        f"{API}/simple/price",
        params={"ids": "bitcoin,ethereum", "vs_currencies": "usd"},
    )
    stables = base.get_json(
        f"{API}/coins/markets",
        params={"vs_currency": "usd", "ids": ",".join(STABLECOINS)},
    )
    rows = [
        (ts, "price_btc", prices["bitcoin"]["usd"]),
        (ts, "price_eth", prices["ethereum"]["usd"]),
        (ts, "btc_dominance", g["market_cap_percentage"]["btc"]),
        (ts, "usdt_dominance", g["market_cap_percentage"].get("usdt")),
        (ts, "total_mcap", g["total_market_cap"]["usd"]),
        (ts, "stablecoin_mcap", sum(c["market_cap"] for c in stables)),
        (ts, "eth_btc", prices["ethereum"]["usd"] / prices["bitcoin"]["usd"]),
    ]
    return base.save(conn, SOURCE, rows)


def _chart(coin, field, days):
    data = base.get_json(
        f"{API}/coins/{coin}/market_chart",
        params={"vs_currency": "usd", "days": days, "interval": "daily"},
    )
    out = {}
    for ms, v in data[field]:
        dt = datetime.fromtimestamp(ms / 1000, tz=timezone.utc)
        out[db.iso(dt)] = v
    return out


def backfill(conn, days=365):
    """Lịch sử 365 ngày (mức tối đa của free tier) — đủ để tính MA200.

    Dominance/tổng mcap lịch sử là API trả phí — bỏ qua, tự tích lũy dần.
    """
    total = 0
    for coin, metric in [("bitcoin", "price_btc"), ("ethereum", "price_eth")]:
        rows = [(ts, metric, v) for ts, v in _chart(coin, "prices", days).items()]
        saved, _ = base.save(conn, SOURCE, rows)
        total += saved
    # Cung stablecoin = tổng market cap USDT + USDC theo ngày;
    # chỉ lấy ngày có đủ cả hai để tổng không bị hụt giả tạo
    charts = [_chart(coin, "market_caps", days) for coin in STABLECOINS]
    common = set.intersection(*(set(c) for c in charts))
    rows = [(ts, "stablecoin_mcap", sum(c[ts] for c in charts)) for ts in common]
    saved, _ = base.save(conn, SOURCE, rows)
    total += saved
    # ETH/BTC ratio: suy từ giá đã lưu trong DB, ngày nào có đủ cả hai
    btc = {p["d"]: p["v"] for p in db.daily_series(conn, "price_btc", days=days)}
    ratio_rows = [
        (p["d"] + "T00:00:00Z", "eth_btc", p["v"] / btc[p["d"]])
        for p in db.daily_series(conn, "price_eth", days=days)
        if p["d"] in btc and btc[p["d"]]
    ]
    saved, _ = base.save(conn, SOURCE, ratio_rows)
    return total + saved, 0
