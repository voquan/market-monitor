#!/usr/bin/env python3
"""Cảnh báo bất thường bằng RULE CỨNG (không AI) -> bảng alerts + Telegram.

  python alerts.py          # kiểm tra các rule, gửi cảnh báo mới
  python alerts.py --list   # xem cảnh báo 7 ngày gần nhất

Rule + ngưỡng + cooldown: docs/rules.md §8. Chạy bằng cron mỗi giờ sau collect.
Không cấu hình Telegram thì chỉ in ra console.
"""
import os
import sys
from datetime import datetime, timedelta, timezone

import requests

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db


def send_telegram(text):
    """Gửi tin nhắn Telegram. Trả về True nếu gửi được, False nếu chưa cấu hình."""
    token = os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")
    if not token or not chat_id:
        return False
    r = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": chat_id, "text": text},
        timeout=20,
    )
    r.raise_for_status()
    return True


# ─── Rules: (tên, cooldown giờ, hàm check trả về message hoặc None) ───

def _funding_hot(conn):
    _, v = db.latest(conn, "funding_btc")
    if v is not None and v >= 0.05:
        lvl = "QUÁ NÓNG" if v >= 0.1 else "nóng"
        return f"Funding BTC {v:.4f}%/8h — đòn bẩy long {lvl}, rủi ro long squeeze."
    return None


def _fng_extreme(conn):
    _, v = db.latest(conn, "fear_greed")
    if v is None:
        return None
    if v >= 75:
        return f"Fear & Greed = {v:.0f} — extreme greed, vùng thận trọng."
    if v <= 25:
        return f"Fear & Greed = {v:.0f} — extreme fear, vùng contrarian."
    return None


def _usdt_spike(conn):
    _, v = db.latest(conn, "usdt_dominance")
    past = db.value_days_ago(conn, "usdt_dominance", 1)
    if v is not None and past is not None and v - past >= 0.3:
        return f"USDT dominance tăng {v - past:+.2f}pp/24h ({v:.2f}%) — tiền đang rút về trú ẩn."
    return None


def _etf_flip(conn):
    s = db.daily_series(conn, "etf_flow_btc", days=30)
    if len(s) < 9:
        return None
    now7 = sum(p["v"] for p in s[-7:])
    prev7 = sum(p["v"] for p in s[-8:-1])
    if now7 * prev7 < 0:  # đổi dấu
        dir_ = "mua ròng → bán ròng" if now7 < 0 else "bán ròng → mua ròng"
        return f"ETF flow BTC đảo chiều 7 phiên: {dir_} ({now7:+,.0f}M USD)."
    return None


RULES = [
    ("funding_hot", 12, _funding_hot),
    ("fng_extreme", 24, _fng_extreme),
    ("usdt_spike", 24, _usdt_spike),
    ("etf_flip", 48, _etf_flip),
]


def _in_cooldown(conn, rule, hours):
    since = db.iso(datetime.now(timezone.utc) - timedelta(hours=hours))
    return conn.execute(
        "SELECT 1 FROM alerts WHERE rule=? AND ts>=?", (rule, since)
    ).fetchone() is not None


def main():
    conn = db.connect()
    if "--list" in sys.argv:
        since = db.iso(datetime.now(timezone.utc) - timedelta(days=7))
        for r in conn.execute("SELECT ts, rule, message FROM alerts WHERE ts>=? ORDER BY ts DESC", (since,)):
            print(f"{r['ts']}  [{r['rule']}]  {r['message']}")
        return

    fired = 0
    for rule, cooldown, check in RULES:
        msg = check(conn)
        if msg is None or _in_cooldown(conn, rule, cooldown):
            continue
        conn.execute(
            "INSERT INTO alerts (ts, rule, message) VALUES (?,?,?)",
            (db.now_iso(), rule, msg),
        )
        conn.commit()
        fired += 1
        print(f"[!] {rule}: {msg}")
        if send_telegram(f"⚠️ {msg}"):
            print("    → đã gửi Telegram")
    if fired == 0:
        print("[o] Không có cảnh báo mới.")
    conn.close()


if __name__ == "__main__":
    main()
