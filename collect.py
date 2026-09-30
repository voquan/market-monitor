#!/usr/bin/env python3
"""Chạy các collector và ghi vào SQLite.

  python collect.py                    # chạy tất cả
  python collect.py coingecko binance  # chạy một số nguồn
  python collect.py --backfill         # nạp lịch sử (chạy 1 lần lúc setup)

Mỗi collector độc lập — một nguồn fail không chặn các nguồn khác.
Exit code 1 nếu có bất kỳ nguồn nào fail (để cron/CI báo động).
"""
import sys
import traceback

try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

import db
from collectors import binance, coingecko, coinmetrics, etf_flows, feargreed, fred

COLLECTORS = {
    "coingecko": coingecko,
    "feargreed": feargreed,
    "binance": binance,
    "fred": fred,
    "etf_flows": etf_flows,
    "coinmetrics": coinmetrics,
}


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    backfill = "--backfill" in sys.argv[1:]

    names = args or list(COLLECTORS)
    unknown = [n for n in names if n not in COLLECTORS]
    if unknown:
        sys.exit(f"Nguồn không tồn tại: {unknown}. Có: {list(COLLECTORS)}")

    conn = db.connect()
    failed = []
    for name in names:
        mod = COLLECTORS[name]
        fn = getattr(mod, "backfill", None) if backfill else mod.run
        if fn is None:
            print(f"[-] {name}: không hỗ trợ backfill, bỏ qua")
            continue
        try:
            saved, rejected = fn(conn)
            note = f", {rejected} bị loại (sanity)" if rejected else ""
            print(f"[o] {name}: lưu {saved} giá trị{note}")
        except Exception as e:
            failed.append(name)
            print(f"[x] {name}: FAIL — {e}")
            if "-v" in sys.argv:
                traceback.print_exc()
    conn.close()

    if failed:
        print(f"\nCó nguồn fail: {failed} — dashboard sẽ hiển thị dữ liệu cũ cho các nguồn này.")
        sys.exit(1)


if __name__ == "__main__":
    main()
