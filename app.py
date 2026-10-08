"""Dashboard server: đọc SQLite, serve JSON + trang tĩnh.

  uvicorn app:app --reload --port 8388
"""
import os
from datetime import datetime, timezone

from fastapi import FastAPI
from fastapi.responses import FileResponse, JSONResponse

import db

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
app = FastAPI(title="Market Monitor")

# metric -> (nhóm, nhãn, đơn vị) — thứ tự ở đây là thứ tự hiển thị trong nhóm
METRICS = {
    "price_btc":      ("header", "BTC",              "usd"),
    "fear_greed":     ("header", "Fear & Greed",     "index"),
    "dxy":            ("macro",  "DXY (broad)",      "index"),
    "us10y":          ("macro",  "Lợi suất 10Y",     "pct"),
    "fed_funds":      ("macro",  "Fed funds",        "pct"),
    "net_liquidity":  ("macro",  "Fed net liquidity","busd"),
    "m2":             ("macro",  "M2",               "busd"),
    "cpi_yoy":        ("macro",  "CPI YoY",          "pct"),
    "mvrv_btc":       ("market", "MVRV BTC",         "ratio"),
    "btc_dominance":  ("market", "BTC dominance",    "pct"),
    "usdt_dominance": ("market", "USDT dominance",   "pct"),
    "total_mcap":     ("market", "Tổng vốn hóa",     "usd_big"),
    "stablecoin_mcap":("market", "Cung stablecoin",  "usd_big"),
    "price_eth":      ("market", "ETH",              "usd"),
    "funding_btc":    ("flows",  "Funding BTC",      "pct8h"),
    "funding_eth":    ("flows",  "Funding ETH",      "pct8h"),
    "oi_btc_usd":     ("flows",  "Open interest BTC","usd_big"),
    "etf_flow_btc":   ("flows",  "ETF flow BTC",     "musd"),
    "etf_flow_eth":   ("flows",  "ETF flow ETH",     "musd"),
    "eth_btc":        ("rotation", "ETH/BTC",        "ratio"),
}

# Trung bình động dài hạn tính từ lịch sử trong DB, đính kèm vào metric giá
MA_WINDOWS = {"price_btc": 200, "price_eth": 200}


def moving_average(conn, metric, window):
    row = conn.execute(
        "SELECT AVG(v), COUNT(*) FROM (SELECT value AS v FROM ("
        "  SELECT substr(ts,1,10) AS d, value FROM metrics"
        "  WHERE metric=? AND value IS NOT NULL GROUP BY d HAVING ts=MAX(ts)"
        "  ORDER BY d DESC LIMIT ?))",
        (metric, window),
    ).fetchone()
    avg, n = row
    # thiếu dữ liệu thì MA méo — chấp nhận hụt tối đa 5% số ngày
    return avg if n >= window * 0.95 else None


@app.get("/api/summary")
def summary():
    conn = db.connect()
    out = {}
    for metric, (group, label, unit) in METRICS.items():
        ts, value = db.latest(conn, metric)
        deltas = {}
        if value is not None:
            for key, days in [("d1", 1), ("d7", 7), ("d30", 30)]:
                past = db.value_days_ago(conn, metric, days)
                deltas[key] = None if past is None else value - past
        out[metric] = {
            "group": group,
            "label": label,
            "unit": unit,
            "ts": ts,
            "value": value,
            "deltas": deltas,
            "series": db.daily_series(conn, metric, days=90),
        }
        if metric in MA_WINDOWS and value is not None:
            out[metric]["ma"] = moving_average(conn, metric, MA_WINDOWS[metric])
            out[metric]["ma_window"] = MA_WINDOWS[metric]
    conn.close()
    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": out,
    })


@app.get("/api/sectors")
def sectors_api():
    """Xoay vòng ngành (rules.md §10): mcap + Δ7d/Δ30d + excess so với tổng mcap."""
    import json as _json
    from collectors.sectors import SECTORS
    conn = db.connect()

    def pct_change(metric, days):
        _, cur = db.latest(conn, metric)
        past = db.value_days_ago(conn, metric, days)
        if cur is None or not past:
            return None
        return (cur / past - 1) * 100

    market_d7 = pct_change("total_mcap", 7)
    out = []
    for slug, label in SECTORS.items():
        metric = f"cat_{slug}"
        row = conn.execute(
            "SELECT ts, value, meta FROM metrics WHERE metric=? AND value IS NOT NULL "
            "ORDER BY ts DESC LIMIT 1", (metric,),
        ).fetchone()
        if row is None:
            continue
        meta = _json.loads(row["meta"]) if row["meta"] else {}
        d7 = pct_change(metric, 7)
        excess = (d7 - market_d7) if (d7 is not None and market_d7 is not None) else None
        out.append({
            "slug": slug,
            "label": meta.get("label", label),
            "ts": row["ts"],
            "mcap": row["value"],
            "change_24h": meta.get("change_24h"),
            "d7": d7,
            "d30": pct_change(metric, 30),
            "excess_d7": excess,
        })
    conn.close()
    # excess giảm dần; chưa đủ lịch sử thì xếp theo mcap
    out.sort(key=lambda s: (s["excess_d7"] is None, -(s["excess_d7"] or 0), -s["mcap"]))
    return JSONResponse({"market_d7": market_d7, "sectors": out})


@app.get("/api/brief")
def brief():
    from datetime import timedelta
    conn = db.connect()
    row = conn.execute(
        "SELECT date, content FROM briefs ORDER BY date DESC LIMIT 1"
    ).fetchone()
    since = db.iso(datetime.now(timezone.utc) - timedelta(hours=48))
    alerts = [
        {"ts": r["ts"], "message": r["message"]}
        for r in conn.execute(
            "SELECT ts, message FROM alerts WHERE ts>=? ORDER BY ts DESC LIMIT 5", (since,)
        )
    ]
    conn.close()
    return JSONResponse({
        "brief": {"date": row["date"], "content": row["content"]} if row else None,
        "alerts": alerts,
    })


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
