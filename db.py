"""SQLite storage cho Market Monitor.

Một file data/market.db duy nhất. Schema xem kien-truc.md.
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.environ.get("MM_DB_PATH", os.path.join(BASE_DIR, "data", "market.db"))

SCHEMA = """
CREATE TABLE IF NOT EXISTS metrics (
  ts      TEXT NOT NULL,
  source  TEXT NOT NULL,
  metric  TEXT NOT NULL,
  value   REAL,
  meta    TEXT,
  PRIMARY KEY (ts, source, metric)
);
CREATE INDEX IF NOT EXISTS idx_metrics_metric_ts ON metrics (metric, ts);

CREATE TABLE IF NOT EXISTS briefs (
  date     TEXT PRIMARY KEY,
  content  TEXT NOT NULL,
  snapshot TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS alerts (
  ts           TEXT NOT NULL,
  rule         TEXT NOT NULL,
  message      TEXT NOT NULL,
  acknowledged INTEGER DEFAULT 0
);
"""


def connect():
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


def iso(dt):
    return dt.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def now_iso():
    return iso(datetime.now(timezone.utc))


def upsert_metric(conn, ts, source, metric, value, meta=None):
    conn.execute(
        "INSERT OR REPLACE INTO metrics (ts, source, metric, value, meta) VALUES (?,?,?,?,?)",
        (ts, source, metric, value, meta),
    )


def latest(conn, metric):
    row = conn.execute(
        "SELECT ts, value FROM metrics WHERE metric=? AND value IS NOT NULL "
        "ORDER BY ts DESC LIMIT 1",
        (metric,),
    ).fetchone()
    return (row["ts"], row["value"]) if row else (None, None)


def value_days_ago(conn, metric, days, tolerance_days=5):
    """Giá trị gần nhất TRƯỚC mốc (now - days), trong khoảng dung sai.

    Dung sai rộng để chỉ số tháng (M2, CPI) vẫn có delta 30 ngày.
    """
    target = datetime.now(timezone.utc) - timedelta(days=days)
    floor = target - timedelta(days=tolerance_days)
    row = conn.execute(
        "SELECT value FROM metrics WHERE metric=? AND value IS NOT NULL "
        "AND ts<=? AND ts>=? ORDER BY ts DESC LIMIT 1",
        (metric, iso(target), iso(floor)),
    ).fetchone()
    return row["value"] if row else None


def daily_series(conn, metric, days=90):
    """Chuỗi 1 điểm/ngày (giá trị cuối ngày) cho sparkline."""
    since = iso(datetime.now(timezone.utc) - timedelta(days=days))
    rows = conn.execute(
        "SELECT substr(ts,1,10) AS d, value FROM metrics "
        "WHERE metric=? AND value IS NOT NULL AND ts>=? "
        "GROUP BY d HAVING ts=MAX(ts) ORDER BY d",
        (metric, since),
    ).fetchall()
    return [{"d": r["d"], "v": r["value"]} for r in rows]
