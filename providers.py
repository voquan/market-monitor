"""Tầng gọi model — swap qua env BRIEF_PROVIDER: claude_cli (mặc định) | claude_api | gemini.

Đổi provider = đổi env, không đụng pipeline. Xem docs/roadmap.md nhật ký quyết định.
"""
import os
import subprocess
import time

import requests

TIMEOUT = 300
RETRIES = 4  # free tier hay trả 429/503 tạm thời — retry với backoff


def generate(instruction, payload, provider=None):
    provider = provider or os.environ.get("BRIEF_PROVIDER", "claude_cli")
    fn = {"claude_cli": _claude_cli, "claude_api": _claude_api, "gemini": _gemini}.get(provider)
    if fn is None:
        raise ValueError(f"Provider không hỗ trợ: {provider} (có: claude_cli, claude_api, gemini)")
    return fn(instruction, payload)


def _claude_cli(instruction, payload):
    """Claude Code headless — dùng subscription sẵn có, chi phí biên $0."""
    proc = subprocess.run(
        ["claude", "-p", instruction, "--output-format", "text"],
        input=payload, capture_output=True, text=True, timeout=TIMEOUT,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI lỗi (exit {proc.returncode}): {proc.stderr.strip()[:500]}")
    out = proc.stdout.strip()
    if not out:
        raise RuntimeError("claude CLI trả về rỗng")
    return out


def _claude_api(instruction, payload):
    """Claude API trả phí — cần ANTHROPIC_API_KEY. Model đổi qua BRIEF_MODEL."""
    import anthropic  # cần: pip install anthropic
    client = anthropic.Anthropic()
    response = client.messages.create(
        model=os.environ.get("BRIEF_MODEL", "claude-opus-5"),
        max_tokens=2000,
        messages=[{"role": "user", "content": f"{instruction}\n\n{payload}"}],
    )
    return "".join(b.text for b in response.content if b.type == "text").strip()


def _gemini(instruction, payload):
    """Gemini free tier — cần GEMINI_API_KEY (aistudio.google.com)."""
    key = os.environ.get("GEMINI_API_KEY")
    if not key:
        raise RuntimeError("Thiếu GEMINI_API_KEY")
    model = os.environ.get("GEMINI_MODEL", "gemini-3.8-flash")
    for attempt in range(RETRIES):
        r = requests.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            # key dạng mới "AQ.*" chỉ nhận qua header x-goog-api-key, không nhận ?key=
            headers={"x-goog-api-key": key},
            json={"contents": [{"parts": [{"text": f"{instruction}\n\n{payload}"}]}]},
            timeout=TIMEOUT,
        )
        if r.status_code in (429, 500, 503) and attempt < RETRIES - 1:
            delay = 15 * (2 ** attempt)
            print(f"  [i] Gemini {r.status_code} — thử lại sau {delay}s ({attempt + 1}/{RETRIES - 1})")
            time.sleep(delay)
            continue
        break
    r.raise_for_status()
    data = r.json()
    return "".join(
        p.get("text", "") for p in data["candidates"][0]["content"]["parts"]
    ).strip()
