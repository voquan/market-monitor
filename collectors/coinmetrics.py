"""CoinMetrics community API: MVRV của BTC — chỉ số định giá chu kỳ on-chain.

MVRV = vốn hóa thị trường / vốn hóa thực hiện (giá vốn trung bình on-chain).
Miễn phí, không cần key. Docs: https://docs.coinmetrics.io/api/v4/
"""
from datetime import datetime, timedelta, timezone

import db
from collectors import base

SOURCE = "coinmetrics"
API = "https://community-api.coinmetrics.io/v4/timeseries/asset-metrics"


def _fetch(start_date):
    params = {
        "assets": "btc",
        "metrics": "CapMVRVCur",
        "frequency": "1d",
        "page_size": 1000,
        "start_time": start_date,
    }
    rows = []
    url, p = API, params
    while True:
        data = base.get_json(url, params=p)
        for item in data.get("data", []):
            date = item["time"][:10]
            rows.append((date + "T00:00:00Z", "mvrv_btc", float(item["CapMVRVCur"])))
        nxt = data.get("next_page_url")
        if not nxt or not data.get("data"):
            break
        url, p = nxt, None
    return rows


def run(conn):
    start = (datetime.now(timezone.utc) - timedelta(days=5)).strftime("%Y-%m-%d")
    return base.save(conn, SOURCE, _fetch(start))


def backfill(conn, days=None):
    # Từ 2017: phủ 2 chu kỳ gần nhất — đủ nền so sánh đỉnh/đáy MVRV
    return base.save(conn, SOURCE, _fetch("2017-01-01"))
