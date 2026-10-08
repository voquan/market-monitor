"""Xoay vòng ngành: market cap 9 sector curate từ CoinGecko categories.

Danh sách sector + lý do curate: docs/rules.md §10 — sửa ở đó trước khi sửa đây.
Lịch sử category là API trả phí nên tự tích lũy từ ngày thu thập đầu (08/10/2026);
excess 7d chỉ có nghĩa sau ~1 tuần dữ liệu.
"""
import db
from collectors import base

SOURCE = "sectors"
API = "https://api.coingecko.com/api/v3"

# slug CoinGecko -> tên hiển thị (phản chiếu rules.md §10)
SECTORS = {
    "decentralized-finance-defi": "DeFi",
    "real-world-assets-rwa": "RWA",
    "meme-token": "Meme",
    "artificial-intelligence": "AI",
    "oracle": "Oracle",
    "depin": "DePIN",
    "layer-2": "Layer 2",
    "gaming": "GameFi",
    "privacy-coins": "Privacy",
}


def run(conn):
    ts = db.now_iso()
    cats = base.get_json(f"{API}/coins/categories", params={"order": "market_cap_desc"})
    by_id = {c["id"]: c for c in cats}
    rows, missing = [], []
    for slug, label in SECTORS.items():
        c = by_id.get(slug)
        if c is None or not c.get("market_cap"):
            missing.append(slug)
            continue
        meta = {"label": label, "change_24h": c.get("market_cap_change_24h")}
        rows.append((ts, f"cat_{slug}", float(c["market_cap"]), meta))
    if missing:
        print(f"  [!] sectors: CoinGecko không trả về {missing} — kiểm tra slug trong rules.md §10")
    return base.save(conn, SOURCE, rows)
