"""Interface chung cho mọi collector: fetch -> sanity check -> ghi metrics."""
import json

import requests

import db

UA = {"User-Agent": "Mozilla/5.0 (market-monitor personal dashboard)"}
TIMEOUT = 20

# Sanity range cho từng metric — giá trị ngoài khoảng bị loại và cảnh báo,
# thà thiếu dữ liệu còn hơn lưu dữ liệu rác (xem kien-truc.md §5).
SANITY = {
    "price_btc": (1_000, 5_000_000),
    "price_eth": (50, 100_000),
    "btc_dominance": (10, 90),
    "usdt_dominance": (0.5, 25),
    "total_mcap": (1e11, 1e14),
    "fear_greed": (0, 100),
    "funding_btc": (-1, 1),          # %/8h
    "funding_eth": (-1, 1),
    "oi_btc_usd": (1e9, 1e12),
    "dxy": (70, 160),
    "us10y": (0, 15),                # %
    "fed_funds": (0, 15),
    "m2": (1e3, 1e5),                # tỷ USD (FRED trả billions)
    "cpi_yoy": (-5, 25),             # %
    "etf_flow_btc": (-5_000, 5_000), # triệu USD/ngày
    "etf_flow_eth": (-3_000, 3_000),
    "mvrv_btc": (0.3, 10),
    "stablecoin_mcap": (5e10, 1.5e12),
    "net_liquidity": (2_000, 12_000), # tỷ USD
    "eth_btc": (0.005, 0.2),          # ratio ETH/BTC
}

# Sector mcap (cat_<slug>, rules.md §10) — slug động nên check theo prefix
PREFIX_SANITY = {"cat_": (1e8, 5e12)}


def _range(metric):
    if metric in SANITY:
        return SANITY[metric]
    for prefix, rng in PREFIX_SANITY.items():
        if metric.startswith(prefix):
            return rng
    return (None, None)


def get_json(url, params=None, headers=None):
    h = dict(UA)
    if headers:
        h.update(headers)
    r = requests.get(url, params=params, headers=h, timeout=TIMEOUT)
    r.raise_for_status()
    return r.json()


def get_text(url, params=None):
    r = requests.get(url, params=params, headers=UA, timeout=TIMEOUT)
    r.raise_for_status()
    return r.text


def save(conn, source, rows):
    """rows: list các (ts, metric, value) hoặc (ts, metric, value, meta_dict).

    Trả về (saved, rejected) — rejected là số giá trị trượt sanity check.
    """
    saved, rejected = 0, 0
    for row in rows:
        ts, metric, value = row[0], row[1], row[2]
        meta = json.dumps(row[3]) if len(row) > 3 and row[3] else None
        lo, hi = _range(metric)
        if value is None or (lo is not None and not (lo <= value <= hi)):
            print(f"  [!] {source}.{metric}={value} ngoài sanity range, bỏ qua")
            rejected += 1
            continue
        db.upsert_metric(conn, ts, source, metric, float(value), meta)
        saved += 1
    conn.commit()
    return saved, rejected
