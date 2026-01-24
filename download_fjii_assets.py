#!/usr/bin/env python3
# download_fjii_assets.py
# -*- coding: utf-8 -*-

"""
Remotely fetch a webpack runtime.*.js and download all referenced JS/CSS chunks.

Example:
  python3 download_fjii_assets.py \
    --runtime-url "https://mt.fjii.com/wap/static/js/runtime.4fd41322fab2a84ecc89.js" \
    --out fjii

It will save files under:
  fjii/wap/static/js/...
  fjii/wap/static/css/...
"""

from __future__ import annotations

import argparse
import os
import re
import sys
import time
from urllib.parse import urlparse, urljoin

import requests


# -----------------------------
# Helpers
# -----------------------------
def ensure_parent(path: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)


def guess_base_from_url(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}"


def extract_public_path(runtime_text: str) -> str:
    # matches: r.p="/wap/" (or similar)
    m = re.search(r'r\.p\s*=\s*["\']([^"\']+)["\']', runtime_text)
    if not m:
        # fallback: many builds have "/"
        return "/"
    return m.group(1)


def parse_js_chunk_map(runtime_text: str) -> dict[int, str]:
    """
    Parse: n.src = r.p+"static/js/"+e+"."+{0:"hash",1:"hash",...}[e]+".js"
    We'll grab the { ... } mapping used for JS.
    """
    # try to locate the object literal right before '+"\.js"'
    # We find a big {...} that contains many entries like 0:"abcd..."
    # Use DOTALL to allow newlines.
    m = re.search(
        r'r\.p\+"static/js/"\+e\+"\."\+\{(.*?)\}\[e\]\+"\.\s*js"',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m:
        # Alternative minifier shapes (just in case)
        m = re.search(
            r'"static/js/"\+e\+"\."\+\{(.*?)\}\[e\]\+"\.\s*js"',
            runtime_text,
            flags=re.DOTALL,
        )
    if not m:
        raise ValueError("Could not find JS chunk hash map in runtime.")

    obj = m.group(1)

    # entries like: 0:"963a5d1c64ba2d597ebf"
    pairs = re.findall(r'(\d+)\s*:\s*"([0-9a-f]{8,})"', obj)
    return {int(k): v for k, v in pairs}


def parse_css_chunk_map(runtime_text: str) -> tuple[dict[int, str], dict[int, str]]:
    """
    Parse: d="static/css/"+({10:"Vote"}[e]||e)+"."+{0:"hash",...}[e]+".css"
    Returns: (name_overrides, hash_map)
      - name_overrides: {10: "Vote"} part
      - hash_map: {chunk_id: css_hash}
    """
    # find name override map: ({10:"Vote"}[e]||e)
    name_map: dict[int, str] = {}
    m_name = re.search(r'\(\{(.*?)\}\[e\]\|\|e\)', runtime_text, flags=re.DOTALL)
    if m_name:
        name_obj = m_name.group(1)
        name_pairs = re.findall(r'(\d+)\s*:\s*"([^"]+)"', name_obj)
        name_map = {int(k): v for k, v in name_pairs}

    # find css hash map: +"."+{...}[e]+".css"
    m_hash = re.search(
        r'"static/css/"\+\(\{.*?\}\[e\]\|\|e\)\+"\."\+\{(.*?)\}\[e\]\+"\.\s*css"',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m_hash:
        # Another possible minified shape
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
    # url_path like "/wap/static/js/xx.js" or "wap/static/js/xx.js"
    rel = url_path.lstrip("/")
    local_path = os.path.join(out_root, rel)
    ensure_parent(local_path)
    with open(local_path, "wb") as f:
        f.write(data)
    return local_path


# -----------------------------
# Main
# -----------------------------
def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument(
        "--runtime-url",
        required=True,
        help="Full URL to runtime.*.js, e.g. https://mt.fjii.com/wap/static/js/runtime.<hash>.js",
    )
    ap.add_argument("--out", default="fjii", help="Output folder (default: fjii)")
    ap.add_argument(
        "--user-agent",
        default="Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36",
    )
    args = ap.parse_args()

    base = guess_base_from_url(args.runtime_url)

    s = requests.Session()
    s.headers.update({"User-Agent": args.user_agent})

    # 1) download runtime
    print(f"[+] Fetch runtime: {args.runtime_url}")
    runtime_bytes = http_get_bytes(args.runtime_url, s)
    runtime_text = runtime_bytes.decode("utf-8", errors="replace")

    # save runtime locally (keep /wap/static/js/... path)
    runtime_path = urlparse(args.runtime_url).path
    saved = save_file(args.out, runtime_path, runtime_bytes)
    print(f"    saved -> {saved}")

    # 2) parse public path (r.p)
    public_path = extract_public_path(runtime_text)
    # normalize to have leading and trailing slash if possible
    if not public_path.startswith("/"):
        public_path = "/" + public_path
    # r.p often ends with "/"
    if not public_path.endswith("/"):
        public_path = public_path + "/"
    print(f"[+] Detected publicPath: {public_path}")

    # 3) parse chunk maps
    js_map = parse_js_chunk_map(runtime_text)
    name_map, css_map = parse_css_chunk_map(runtime_text)

    print(f"[+] JS chunks: {len(js_map)}")
    print(f"[+] CSS chunks: {len(css_map)}")

    # 4) build URLs and download
    targets: list[str] = []

    # JS: /wap/static/js/<id>.<hash>.js
    for cid, h in sorted(js_map.items()):
        p = f"{public_path}static/js/{cid}.{h}.js"
        targets.append(urljoin(base, p))

    # CSS: /wap/static/css/<name>.<hash>.css , name = name_map.get(id, str(id))
    for cid, h in sorted(css_map.items()):
        name = name_map.get(cid, str(cid))
        p = f"{public_path}static/css/{name}.{h}.css"
        targets.append(urljoin(base, p))

    # also include the runtime url itself (already downloaded) but keep list unique
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
