"""ETF flows BTC (Farside Investors) — scrape HTML, điểm mong manh nhất của hệ thống.

Collector này được PHÉP fail: collect.py sẽ báo lỗi rõ ràng thay vì
im lặng dùng dữ liệu cũ. Khi Farside đổi HTML, sửa hàm _parse().
"""
import re

import cloudscraper
from bs4 import BeautifulSoup

from collectors import base

SOURCE = "etf_flows"
PAGES = {  # metric -> trang Farside
    "etf_flow_btc": "https://farside.co.uk/btc/",
    "etf_flow_eth": "https://farside.co.uk/eth/",
}


def _fetch(url):
    # Farside nằm sau Cloudflare — requests thường bị 403, cloudscraper vượt được
    r = cloudscraper.create_scraper().get(url, timeout=base.TIMEOUT + 10)
    r.raise_for_status()
    return r.text


def _to_number(text):
    """'(123.4)' -> -123.4 ; '1,234.5' -> 1234.5 ; '-' / '' -> None"""
    t = text.strip().replace(",", "")
    if t in ("", "-", "–"):
        return None
    neg = t.startswith("(") and t.endswith(")")
    t = t.strip("()")
    try:
        v = float(t)
    except ValueError:
        return None
    return -v if neg else v


def _parse_all(html):
    """Trả về list (date_iso, total_flow_musd) của mọi dòng có số liệu."""
    soup = BeautifulSoup(html, "html.parser")
    table = soup.find("table")
    if table is None:
        raise RuntimeError("Không tìm thấy bảng — Farside có thể đã đổi HTML hoặc chặn request")

    header = [th.get_text(strip=True) for th in table.find_all("tr")[0].find_all(["th", "td"])]
    try:
        total_idx = [h.lower() for h in header].index("total")
    except ValueError:
        total_idx = len(header) - 1  # Total thường là cột cuối

    date_re = re.compile(r"^(\d{1,2}) (\w{3}) (\d{4})$")
    months = {m: i + 1 for i, m in enumerate(
        ["Jan", "Feb", "Mar", "Apr", "May", "Jun",
         "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"])}

    rows = []
    for tr in table.find_all("tr"):
        cells = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(cells) <= total_idx:
            continue
        m = date_re.match(cells[0])
        if not m:
            continue
        total = _to_number(cells[total_idx])
        if total is None:
            continue
        day, mon, year = int(m.group(1)), months.get(m.group(2)), int(m.group(3))
        if mon:
            rows.append((f"{year:04d}-{mon:02d}-{day:02d}", total))

    if not rows:
        raise RuntimeError("Không parse được dòng dữ liệu nào — kiểm tra lại cấu trúc bảng Farside")
    return rows


def _collect(conn, latest_only):
    saved, rejected = 0, 0
    for metric, url in PAGES.items():
        parsed = _parse_all(_fetch(url))
        if latest_only:
            parsed = parsed[-1:]
        rows = [(d + "T00:00:00Z", metric, v) for d, v in parsed]
        s, r = base.save(conn, SOURCE, rows)
        saved, rejected = saved + s, rejected + r
    return saved, rejected


def run(conn):
    return _collect(conn, latest_only=True)


def backfill(conn, days=None):
    # Các trang Farside chứa sẵn bảng nhiều ngày gần nhất — lưu hết
    return _collect(conn, latest_only=False)
