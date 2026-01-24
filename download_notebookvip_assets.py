#!/usr/bin/env python3
# download_notebookvip_assets.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import os
import re
import time
from urllib.parse import urlparse, urljoin

import requests


def ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def guess_origin(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}"


def extract_public_path(runtime_text: str) -> str | None:
    # matches: r.p="/jsb-wap/" (or similar)
    m = re.search(r'r\.p\s*=\s*["\']([^"\']+)["\']', runtime_text)
    return m.group(1) if m else None


def normalize_public_path(p: str) -> str:
    # ensure leading + trailing slash
    if not p.startswith("/"):
        p = "/" + p
    if not p.endswith("/"):
        p = p + "/"
    return p


def parse_js_chunk_map(runtime_text: str) -> dict[int, str]:
    # Typical: r.p+"static/js/"+e+"."+{...}[e]+".js"
    m = re.search(
        r'r\.p\+"static/js/"\+e\+"\."\+\{(.*?)\}\[e\]\+"\.\s*js"',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m:
        m = re.search(
            r'"static/js/"\+e\+"\."\+\{(.*?)\}\[e\]\+"\.\s*js"',
            runtime_text,
            flags=re.DOTALL,
        )
    if not m:
        raise ValueError("Could not find JS chunk hash map in runtime.")

    obj = m.group(1)
    pairs = re.findall(r'(\d+)\s*:\s*"([0-9a-f]{8,})"', obj)
    return {int(k): v for k, v in pairs}


def parse_css_chunk_map(runtime_text: str) -> tuple[dict[int, str], dict[int, str]]:
    # Typical: "static/css/"+({10:"Vote"}[e]||e)+"."+{...}[e]+".css"
    name_map: dict[int, str] = {}

    m_name = re.search(r'\(\{(.*?)\}\[e\]\|\|e\)', runtime_text, flags=re.DOTALL)
    if m_name:
        name_obj = m_name.group(1)
        name_pairs = re.findall(r'(\d+)\s*:\s*"([^"]+)"', name_obj)
        name_map = {int(k): v for k, v in name_pairs}

    m_hash = re.search(
        r'"static/css/"\+\(\{.*?\}\[e\]\|\|e\)\+"\."\+\{(.*?)\}\[e\]\+"\.\s*css"',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m_hash:
        m_hash = re.search(
            r'"static/css/"\+.*?\+"\."\+\{(.*?)\}\[e\]\+"\.\s*css"',
            runtime_text,
            flags=re.DOTALL,
        )
    if not m_hash:
        raise ValueError("Could not find CSS chunk hash map in runtime.")

    obj = m_hash.group(1)
    pairs = re.findall(r'(\d+)\s*:\s*"([0-9a-f]{8,})"', obj)
    hash_map = {int(k): v for k, v in pairs}
    return name_map, hash_map


def http_get_bytes(
    url: str,
    session: requests.Session,
    *,
    retries: int = 3,
    timeout: int = 30,
) -> bytes:
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            r = session.get(url, timeout=timeout)
            r.raise_for_status()
            return r.content
        except Exception as e:
            last_exc = e
            if attempt < retries:
                time.sleep(0.8 * attempt)
                continue
            raise last_exc


def save_file(out_root: str, url_path: str, data: bytes) -> str:
    # url_path like "/jsb-wap/static/js/xx.js"
    rel = url_path.lstrip("/")
    local_path = os.path.join(out_root, rel)
    ensure_parent(local_path)
    with open(local_path, "wb") as f:
        f.write(data)
    return local_path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--runtime-url",
        required=True,
        help="Full URL to runtime.*.js",
    )
    ap.add_argument("--out", default="fjii", help="Output folder (default: fjii)")
    ap.add_argument(
        "--public-path",
        default="",
        help="Override webpack publicPath (e.g. /jsb-wap/). If empty, parse from runtime (r.p).",
    )
    ap.add_argument(
        "--origin",
        default="",
        help="Override origin (scheme+host), e.g. https://jsb.notebookvip.cn . If empty, derived from runtime-url.",
    )
    ap.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (Linux; Android 11; sdk_gphone_arm64 Build/RSR1.240422.006; wv) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/91.0.4472.114 Mobile Safari/537.36",
    )
    args = ap.parse_args()

    origin = args.origin.strip() or guess_origin(args.runtime_url)

    s = requests.Session()
    s.headers.update({"User-Agent": args.user_agent})

    print(f"[+] Fetch runtime: {args.runtime_url}")
    runtime_bytes = http_get_bytes(args.runtime_url, s)
    runtime_text = runtime_bytes.decode("utf-8", errors="replace")

    runtime_path = urlparse(args.runtime_url).path
    saved = save_file(args.out, runtime_path, runtime_bytes)
    print(f"    saved -> {saved}")

    parsed_pp = extract_public_path(runtime_text) or "/"
    public_path = normalize_public_path(args.public_path.strip() or parsed_pp)
    print(f"[+] Using publicPath: {public_path}")
    print(f"[+] Using origin: {origin}")

    js_map = parse_js_chunk_map(runtime_text)
    name_map, css_map = parse_css_chunk_map(runtime_text)

    print(f"[+] JS chunks: {len(js_map)}")
    print(f"[+] CSS chunks: {len(css_map)}")

    targets: list[str] = []

    for cid, h in sorted(js_map.items()):
        p = f"{public_path}static/js/{cid}.{h}.js"
        targets.append(urljoin(origin, p))

    for cid, h in sorted(css_map.items()):
        name = name_map.get(cid, str(cid))
        p = f"{public_path}static/css/{name}.{h}.css"
        targets.append(urljoin(origin, p))

    targets = sorted(set(targets))
    print(f"[+] Total targets (js+css): {len(targets)}")

    ok = 0
    fail = 0
    for idx, url in enumerate(targets, 1):
        up = urlparse(url)
        try:
            data = http_get_bytes(url, s)
            saved_path = save_file(args.out, up.path, data)
            ok += 1
            if idx % 25 == 0 or idx == len(targets):
                print(f"    [{idx}/{len(targets)}] OK -> {saved_path}")
        except Exception as e:
            fail += 1
            print(f"    [{idx}/{len(targets)}] FAIL {url}: {e}")

    print(f"[+] Done. OK={ok}, FAIL={fail}, out={args.out}")
    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
