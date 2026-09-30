"""Fear & Greed Index — Alternative.me, không cần key."""
from datetime import datetime, timezone

import db
from collectors import base

SOURCE = "feargreed"
API = "https://api.alternative.me/fng/"


def _rows(data):
    rows = []
    for item in data["data"]:
        dt = datetime.fromtimestamp(int(item["timestamp"]), tz=timezone.utc)
        rows.append(
            (db.iso(dt), "fear_greed", float(item["value"]),
             {"label": item.get("value_classification")})
        )
    return rows


def run(conn):
    return base.save(conn, SOURCE, _rows(base.get_json(API, params={"limit": 1})))


def backfill(conn, days=0):
    # limit=0 = toàn bộ lịch sử từ 2018 — dữ liệu quý cho regime analysis sau này
    return base.save(conn, SOURCE, _rows(base.get_json(API, params={"limit": 0})))
