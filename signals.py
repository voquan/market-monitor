"""Dựng snapshot có signal/note tính sẵn bằng rule — đầu vào cho daily brief.

AI chỉ tổng hợp thành văn từ các facts đã phân loại ở đây, không tự suy từ số thô.
Ngưỡng phân loại phản chiếu docs/rules.md §3 và §7 (bản gốc cho UI: static/index.html).
"""
from datetime import datetime, timezone

import db
from app import MA_WINDOWS, METRICS, moving_average


def _pctl(series, v):
    if not series or len(series) < 10:
        return None
    return round(100 * sum(1 for p in series if p["v"] <= v) / len(series))


def _sig_note(metric, v, d7, d30, series, ma, all_values):
    """Trả về (signal, note): signal ∈ good/bad/neutral, note = 1 câu facts ngắn."""
    if metric in ("price_btc", "price_eth"):
        if ma:
            gap = (v / ma - 1) * 100
            sig = "good" if gap >= 3 else "bad" if gap <= -3 else "neutral"
            return sig, f"{'trên' if gap >= 0 else 'dưới'} MA200 {gap:+.1f}%"
        return "neutral", None
    if metric == "total_mcap":
        sig = "neutral" if d7 is None else "good" if d7 > 0 else "bad"
        return sig, None
    if metric == "fear_greed":
        if v >= 75: return "bad", "extreme greed"
        if v >= 55: return "neutral", "greed"
        if v <= 25: return "good", "extreme fear (contrarian)"
        if v <= 45: return "neutral", "fear"
        return "neutral", "trung tính"
    if metric == "dxy":
        if d30 is None: return "neutral", None
        if d30 > 0.5: return "bad", f"USD mạnh lên {d30:+.1f}đ/30d"
        if d30 < -0.5: return "good", f"USD yếu đi {d30:+.1f}đ/30d"
        return "neutral", "đi ngang 30d"
    if metric == "us10y":
        lvl = "cao" if v >= 4.5 else "trung bình" if v >= 3.5 else "thấp"
        if d30 is None: return "neutral", f"mức {lvl}"
        sig = "bad" if d30 >= 0.15 else "good" if d30 <= -0.15 else "neutral"
        return sig, f"mức {lvl}, {d30:+.2f}pp/30d"
    if metric == "fed_funds":
        cpi = all_values.get("cpi_yoy")
        if cpi is None: return "neutral", None
        real = v - cpi
        sig = "bad" if real >= 1 else "good" if real < 0 else "neutral"
        state = "thắt chặt" if real >= 1 else "thắt chặt nhẹ" if real >= 0 else "kích thích"
        return sig, f"lãi suất thực {real:+.2f}pp ({state})"
    if metric in ("m2", "net_liquidity"):
        tr = d30 if d30 is not None else (series[-1]["v"] - series[0]["v"] if len(series) >= 2 else None)
        if tr is None: return "neutral", None
        return ("good", "đang mở rộng") if tr > 0 else ("bad", "đang thu hẹp")
    if metric == "cpi_yoy":
        if v - 2 <= 0.3: return "good", "sát mục tiêu 2%"
        sig = "bad" if (d30 is not None and d30 >= 0.1) else "neutral"
        return sig, f"cách mục tiêu 2% {v - 2:+.1f}pp"
    if metric == "btc_dominance":
        note = "co cụm về BTC" if v >= 55 else "cân bằng" if v >= 45 else "lan sang alt"
        return "neutral", note
    if metric == "usdt_dominance":
        if d7 is None: return "neutral", None
        if d7 >= 0.15: return "bad", "tăng — tiền trú ẩn (risk-off)"
        if d7 <= -0.15: return "good", "giảm — tiền vào lại (risk-on)"
        return "neutral", "đi ngang"
    if metric == "stablecoin_mcap":
        tr = d30 / (v - d30) * 100 if d30 is not None and v != d30 else None
        if tr is None: return "neutral", None
        if tr >= 1: return "good", f"mở rộng {tr:+.1f}%/30d — tiền mới vào ngành"
        if tr <= -1: return "bad", f"thu hẹp {tr:+.1f}%/30d"
        return "neutral", "đi ngang 30d"
    if metric == "mvrv_btc":
        if v >= 3: return "bad", "vùng đỉnh chu kỳ (>3)"
        if v >= 2: return "neutral", "định giá ấm (2–3)"
        if v >= 1: return "neutral", "vùng trung tính (1–2)"
        return "good", "vùng đáy chu kỳ (<1)"
    if metric in ("funding_btc", "funding_eth"):
        if v >= 0.1: return "bad", "quá nóng — rủi ro long squeeze"
        if v >= 0.05: return "bad", "nóng"
        if v < 0: return "neutral", "âm — short trả phí, thận trọng"
        return "neutral", "lành mạnh"
    if metric == "oi_btc_usd":
        p = _pctl(series, v)
        if p is None: return "neutral", None
        sig = "bad" if p >= 80 else "neutral"
        return sig, f"percentile {p} của 30d"
    if metric in ("etf_flow_btc", "etf_flow_eth"):
        if not series: return "neutral", None
        s7 = sum(p["v"] for p in series[-7:])
        sig = "good" if s7 > 0 else "bad" if s7 < 0 else "neutral"
        return sig, f"tổng 7 phiên {s7:+,.0f}M USD ({'mua ròng' if s7 > 0 else 'bán ròng'})"
    return "neutral", None


def build_snapshot():
    """Snapshot JSON-able: mỗi metric gồm value, deltas, signal, note."""
    conn = db.connect()
    values = {}
    raw = {}
    for metric in METRICS:
        ts, value = db.latest(conn, metric)
        values[metric] = value
        raw[metric] = {"ts": ts, "value": value,
                       "series": db.daily_series(conn, metric, days=90)}
    out = {}
    for metric, (group, label, unit) in METRICS.items():
        r = raw[metric]
        v = r["value"]
        if v is None:
            continue
        deltas = {}
        for key, days in [("d1", 1), ("d7", 7), ("d30", 30)]:
            past = db.value_days_ago(conn, metric, days)
            deltas[key] = None if past is None else round(v - past, 6)
        ma = moving_average(conn, metric, MA_WINDOWS[metric]) if metric in MA_WINDOWS else None
        sig, note = _sig_note(metric, v, deltas["d7"], deltas["d30"], r["series"], ma, values)
        out[metric] = {
            "label": label, "group": group, "unit": unit,
            "value": round(v, 6), "deltas": deltas,
            "signal": sig,
        }
        if note:
            out[metric]["note"] = note
        if ma:
            out[metric]["ma200"] = round(ma, 2)
    conn.close()
    return {
        "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "metrics": out,
    }
