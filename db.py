"""Storage cho Market Monitor: SQLite local, hoặc Turso khi chạy online.

- Local (mặc định): một file data/market.db. Schema xem kien-truc.md.
- Online: đặt TURSO_DATABASE_URL + TURSO_AUTH_TOKEN -> cùng schema trên Turso,
  nói chuyện qua HTTP pipeline API (không cần native lib, chạy được mọi nơi).
"""
import os
import sqlite3
from datetime import datetime, timedelta, timezone

import requests

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
    if os.environ.get("TURSO_DATABASE_URL"):
        return TursoConn(os.environ["TURSO_DATABASE_URL"], os.environ["TURSO_AUTH_TOKEN"])
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.executescript(SCHEMA)
    return conn


# ─── Turso: adapter HTTP tối giản, cùng interface với sqlite3 ───

class Row:
    """Hàng kết quả: truy cập được cả row["col"], row[0] và unpack như tuple."""
    def __init__(self, cols, vals):
        self._cols, self._vals = cols, vals

    def __getitem__(self, k):
        return self._vals[k] if isinstance(k, int) else self._vals[self._cols.index(k)]

    def __iter__(self):
        return iter(self._vals)

    def keys(self):
        return self._cols


class _Cursor:
    def __init__(self, rows):
        self._rows = rows

    def fetchone(self):
        return self._rows[0] if self._rows else None

    def fetchall(self):
        return self._rows

    def __iter__(self):
        return iter(self._rows)


class TursoConn:
    _schema_ready = set()  # url đã chạy schema trong process này

    def __init__(self, url, token):
        if url.startswith("libsql://"):
            url = "https://" + url[len("libsql://"):]
        self._url = url.rstrip("/") + "/v2/pipeline"
        self._s = requests.Session()
        self._s.headers["Authorization"] = f"Bearer {token}"
        if self._url not in TursoConn._schema_ready:
            self.executescript(SCHEMA)
            TursoConn._schema_ready.add(self._url)

    @staticmethod
    def _arg(v):
        if v is None:
            return {"type": "null"}
        if isinstance(v, bool):
            return {"type": "integer", "value": str(int(v))}
        if isinstance(v, int):
            return {"type": "integer", "value": str(v)}
        if isinstance(v, float):
            return {"type": "float", "value": v}
        return {"type": "text", "value": str(v)}

    @staticmethod
    def _val(cell):
        t = cell["type"]
        if t == "null":
            return None
        if t == "integer":
            return int(cell["value"])  # Turso trả integer dạng chuỗi
        if t == "float":
            return float(cell["value"])
        return cell["value"]

    def pipeline(self, stmts):
        """stmts: list {"sql":..., "args":[...]} — nhiều lệnh trong 1 round trip."""
        reqs = [{"type": "execute", "stmt": s} for s in stmts] + [{"type": "close"}]
        r = self._s.post(self._url, json={"requests": reqs}, timeout=60)
        r.raise_for_status()
        out = []
        for res in r.json()["results"]:
            if res["type"] == "error":
                raise RuntimeError(f"Turso: {res['error'].get('message')}")
            if res["type"] == "ok" and res["response"]["type"] == "execute":
                rr = res["response"]["result"]
                cols = [c["name"] for c in rr["cols"]]
                out.append([Row(cols, [self._val(c) for c in row]) for row in rr["rows"]])
        return out

    def execute(self, sql, params=()):
        rows = self.pipeline([{"sql": sql, "args": [self._arg(p) for p in params]}])
        return _Cursor(rows[0] if rows else [])

    def executescript(self, script):
        self.pipeline([{"sql": s.strip(), "args": []} for s in script.split(";") if s.strip()])

    def commit(self):
        pass  # mỗi pipeline tự commit

    def close(self):
        self._s.close()


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
