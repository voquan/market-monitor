"""FRED: DXY, lợi suất 10Y, Fed funds, M2, CPI YoY. Cần FRED_API_KEY (miễn phí).

Đăng ký key: https://fred.stlouisfed.org/docs/api/api_key.html
ts lưu theo ngày quan sát (observation date), không phải lúc chạy.
"""
import os
from datetime import datetime, timedelta, timezone

import db
from collectors import base

SOURCE = "fred"
API = "https://api.stlouisfed.org/fred/series/observations"

SERIES = {
    "DTWEXBGS": "dxy",       # Broad Dollar Index, daily
    "DGS10": "us10y",        # 10Y Treasury yield, daily
    "DFF": "fed_funds",      # Fed funds effective rate, daily
    "M2SL": "m2",            # M2, monthly (tỷ USD)
}
CPI_SERIES = "CPIAUCSL"      # CPI index, monthly -> tự tính YoY

# Net liquidity = tổng tài sản Fed - reverse repo - tài khoản Kho bạc (tỷ USD)
# Chỉ số thanh khoản bám sát BTC hơn M2 thô.
# Đơn vị gốc FRED khác nhau: WALCL & WTREGEN triệu USD, RRPONTSYD tỷ USD.
NETLIQ = {"WALCL": 1e-3, "RRPONTSYD": 1.0, "WTREGEN": 1e-3}  # hệ số quy về tỷ USD


def _obs(series_id, start, api_key):
    data = base.get_json(API, params={
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": start,
    })
    out = []
    for o in data["observations"]:
        if o["value"] != ".":
            out.append((o["date"], float(o["value"])))
    return out


def _collect(conn, start):
    api_key = os.environ.get("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("Thiếu FRED_API_KEY — xem README.md để đăng ký key miễn phí")

    rows = []
    for series_id, metric in SERIES.items():
        for date, value in _obs(series_id, start, api_key):
            rows.append((date + "T00:00:00Z", metric, value))

    # CPI YoY cần 13 tháng dữ liệu index để tính, bất kể start là gì
    cpi_start = (datetime.now(timezone.utc) - timedelta(days=430)).strftime("%Y-%m-%d")
    cpi_start = min(cpi_start, start)
    cpi = _obs(CPI_SERIES, cpi_start, api_key)
    by_month = {d[:7]: (d, v) for d, v in cpi}
    for month, (date, value) in by_month.items():
        y, m = int(month[:4]), int(month[5:])
        prev = by_month.get(f"{y - 1:04d}-{m:02d}")
        if prev and date >= start:
            yoy = (value / prev[1] - 1) * 100
            rows.append((date + "T00:00:00Z", "cpi_yoy", yoy))

    # Net liquidity: WALCL là series tuần — với mỗi mốc WALCL, trừ đi giá trị
    # RRP/TGA gần nhất trước hoặc bằng mốc đó (as-of join)
    netliq = {sid: sorted(_obs(sid, start, api_key)) for sid in NETLIQ}

    def asof(series, date):
        best = None
        for d, v in series:
            if d <= date:
                best = v
            else:
                break
        return best

    for date, walcl in netliq["WALCL"]:
        rrp = asof(netliq["RRPONTSYD"], date)
        tga = asof(netliq["WTREGEN"], date)
        if rrp is not None and tga is not None:
            value = (walcl * NETLIQ["WALCL"]
                     - rrp * NETLIQ["RRPONTSYD"]
                     - tga * NETLIQ["WTREGEN"])
            rows.append((date + "T00:00:00Z", "net_liquidity", value))
    return base.save(conn, SOURCE, rows)


def run(conn):
    # Lấy 45 ngày gần nhất để chỉ số tháng (M2/CPI) luôn có bản ghi mới
    start = (datetime.now(timezone.utc) - timedelta(days=45)).strftime("%Y-%m-%d")
    return _collect(conn, start)


def backfill(conn, days=400):
    start = (datetime.now(timezone.utc) - timedelta(days=days)).strftime("%Y-%m-%d")
    return _collect(conn, start)
