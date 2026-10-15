#!/usr/bin/env python3
"""Di cư toàn bộ dữ liệu từ data/market.db (local) lên Turso. Chạy MỘT lần.

Cần TURSO_DATABASE_URL + TURSO_AUTH_TOKEN trong .env.
An toàn chạy lại: dùng INSERT OR REPLACE, không nhân đôi dữ liệu.
"""
import os
import sqlite3
import sys

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db

BATCH = 200  # số dòng mỗi HTTP round trip


def main():
    if not os.environ.get("TURSO_DATABASE_URL"):
        sys.exit("Thiếu TURSO_DATABASE_URL trong .env — xem README phần deploy.")

    local = sqlite3.connect(db.DB_PATH)
    local.row_factory = sqlite3.Row
    remote = db.connect()
    assert isinstance(remote, db.TursoConn), "TURSO_DATABASE_URL chưa được đọc?"

    tables = {
        "metrics": "INSERT OR REPLACE INTO metrics (ts, source, metric, value, meta) VALUES (?,?,?,?,?)",
        "briefs": "INSERT OR REPLACE INTO briefs (date, content, snapshot) VALUES (?,?,?)",
        "alerts": "INSERT OR REPLACE INTO alerts (rowid, ts, rule, message, acknowledged) VALUES (?,?,?,?,?)",
    }
    for table, sql in tables.items():
        cols = "rowid, *" if table == "alerts" else "*"
        rows = local.execute(f"SELECT {cols} FROM {table}").fetchall()
        print(f"{table}: {len(rows)} dòng", end="", flush=True)
        for i in range(0, len(rows), BATCH):
            stmts = [
                {"sql": sql, "args": [db.TursoConn._arg(v) for v in tuple(r)]}
                for r in rows[i:i + BATCH]
            ]
            remote.pipeline(stmts)
            print(".", end="", flush=True)
        print(" xong")

    # Đối chiếu số dòng hai bên
    for table in tables:
        n_local = local.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        n_remote = remote.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
        flag = "OK" if n_local == n_remote else "LỆCH!"
        print(f"[{flag}] {table}: local={n_local} turso={n_remote}")


if __name__ == "__main__":
    main()
