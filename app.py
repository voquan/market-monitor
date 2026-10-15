"""Dashboard server: đọc SQLite, serve JSON + trang tĩnh.

  uvicorn app:app --reload --port 8388
"""
import os
from datetime import datetime, timezone

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

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


# CDN cache: dữ liệu đổi theo giờ, cache 5 phút + serve-stale là quá đủ.
# Lý do tồn tại: Turso ở xa thì mỗi lần dựng summary vẫn tốn ~1s — cache đỡ hộ.
CACHE = {"Cache-Control": "s-maxage=300, stale-while-revalidate=600"}

MA_Q = ("SELECT AVG(v), COUNT(*) FROM (SELECT value AS v FROM ("
        "  SELECT substr(ts,1,10) AS d, value FROM metrics"
        "  WHERE metric=? AND value IS NOT NULL GROUP BY d HAVING ts=MAX(ts)"
        "  ORDER BY d DESC LIMIT ?))")


def moving_average(conn, metric, window):
    """Bản gọi đơn lẻ (signals.py dùng); summary() dùng MA_Q qua batch."""
    row = conn.execute(MA_Q, (metric, window)).fetchone()
    avg, n = (row[0], row[1]) if row else (None, 0)
    # thiếu dữ liệu thì MA méo — chấp nhận hụt tối đa 5% số ngày
    return avg if (avg is not None and n >= window * 0.95) else None


@app.get("/api/summary")
def summary():
    """Toàn bộ query của trang gom thành MỘT round trip tới Turso (db.run_batch)."""
    conn = db.connect()
    queries = []
    for metric in METRICS:
        queries.append(db.latest_q(metric))
        for days in (1, 7, 30):
            queries.append(db.days_ago_q(metric, days))
        queries.append(db.series_q(metric, 90))
        if metric in MA_WINDOWS:
            queries.append((MA_Q, (metric, MA_WINDOWS[metric])))
    results = iter(db.run_batch(conn, queries))
    conn.close()

    def one(rows):
        return rows[0] if rows else None

    out = {}
    for metric, (group, label, unit) in METRICS.items():
        latest = one(next(results))
        ts, value = (latest["ts"], latest["value"]) if latest else (None, None)
        deltas = {}
        for key in ("d1", "d7", "d30"):
            past = one(next(results))
            deltas[key] = (value - past["value"]) if (value is not None and past) else None
        series = [{"d": r["d"], "v": r["value"]} for r in next(results)]
        out[metric] = {
            "group": group, "label": label, "unit": unit,
            "ts": ts, "value": value,
            "deltas": deltas if value is not None else {},
            "series": series,
        }
        if metric in MA_WINDOWS:
            ma_row = one(next(results))
            avg, n = (ma_row[0], ma_row[1]) if ma_row else (None, 0)
            # thiếu dữ liệu thì MA méo — chấp nhận hụt tối đa 5% số ngày
            if value is not None and avg is not None and n >= MA_WINDOWS[metric] * 0.95:
                out[metric]["ma"] = avg
                out[metric]["ma_window"] = MA_WINDOWS[metric]
    return JSONResponse({
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": out,
    }, headers=CACHE)


@app.get("/api/sectors")
def sectors_api():
    """Xoay vòng ngành (rules.md §10): mcap + Δ7d/Δ30d + excess — 1 round trip."""
    import json as _json
    from collectors.sectors import SECTORS
    conn = db.connect()

    LATEST_META = ("SELECT ts, value, meta FROM metrics WHERE metric=? AND value IS NOT NULL "
                   "ORDER BY ts DESC LIMIT 1")
    metrics = ["total_mcap"] + [f"cat_{slug}" for slug in SECTORS]
    queries = []
    for m in metrics:
        queries.append((LATEST_META, (m,)))
        queries.append(db.days_ago_q(m, 7))
        queries.append(db.days_ago_q(m, 30))
        queries.append(db.series_q(m, 35))
    results = iter(db.run_batch(conn, queries))
    conn.close()

    def pct(cur, past_rows):
        past = past_rows[0]["value"] if past_rows else None
        return (cur / past - 1) * 100 if (cur is not None and past) else None

    def broken(series):
        """Gãy chuỗi do CoinGecko đổi thành phần category — rules.md §10."""
        vals = [r["value"] for r in series]
        return any(
            prev and abs(cur / prev - 1) > 0.20
            for prev, cur in zip(vals, vals[1:])
        )

    data = {}
    for m in metrics:
        row = next(results)
        row = row[0] if row else None
        cur = row["value"] if row else None
        d7, d30 = pct(cur, next(results)), pct(cur, next(results))
        series = next(results)
        is_broken = m != "total_mcap" and broken(series)
        if is_broken:
            d7 = d30 = None
        data[m] = {"row": row, "d7": d7, "d30": d30, "broken": is_broken}

    market_d7 = data["total_mcap"]["d7"]
    out = []
    for slug, label in SECTORS.items():
        d = data[f"cat_{slug}"]
        if d["row"] is None:
            continue
        meta = _json.loads(d["row"]["meta"]) if d["row"]["meta"] else {}
        excess = (d["d7"] - market_d7) if (d["d7"] is not None and market_d7 is not None) else None
        out.append({
            "slug": slug,
            "label": meta.get("label", label),
            "ts": d["row"]["ts"],
            "mcap": d["row"]["value"],
            "change_24h": meta.get("change_24h"),
            "d7": d["d7"],
            "d30": d["d30"],
            "excess_d7": excess,
            "broken": d["broken"],
        })
    # excess giảm dần; chưa đủ lịch sử thì xếp theo mcap
    out.sort(key=lambda s: (s["excess_d7"] is None, -(s["excess_d7"] or 0), -s["mcap"]))
    return JSONResponse({"market_d7": market_d7, "sectors": out}, headers=CACHE)


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
    }, headers=CACHE)


@app.get("/")
def index():
    return FileResponse(os.path.join(BASE_DIR, "static", "index.html"))
