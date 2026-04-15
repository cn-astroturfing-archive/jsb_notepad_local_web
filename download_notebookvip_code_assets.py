#!/usr/bin/env python3
# download_notebookvip_assets.py
# -*- coding: utf-8 -*-

from __future__ import annotations

import argparse
import html
import os
import re
import sys
import time
from html.parser import HTMLParser
from urllib.parse import urldefrag, urljoin, urlparse

import requests


DEFAULT_PAGE_URL = "https://jsb.notebookvip.cn/jsb-wap/"
DEFAULT_OUT_DIR = "jsb_web"

CORDOVA_IGNORE_SUBSTRINGS = (
    "cordova",
    "/plugins/",
    "customplugin.js",
    "/device.js",
    "/logger.js",
)


def human_bytes(n: int) -> str:
    units = ["B", "KB", "MB", "GB", "TB"]
    x = float(n)

    for unit in units:
        if x < 1024 or unit == units[-1]:
            return f"{x:.1f} {unit}"
        x /= 1024

    return f"{n} B"


def ensure_parent(path: str) -> None:
    parent = os.path.dirname(path)
    if parent:
        os.makedirs(parent, exist_ok=True)


def guess_origin(u: str) -> str:
    p = urlparse(u)
    return f"{p.scheme}://{p.netloc}"


def clean_url(u: str) -> str:
    return urldefrag(u.strip())[0]


def is_ignored_asset_url(u: str) -> bool:
    path = urlparse(u).path.lower()
    return any(s in path for s in CORDOVA_IGNORE_SUBSTRINGS)


def is_js_or_css_url(u: str) -> bool:
    path = urlparse(u).path.lower()
    return path.endswith(".js") or path.endswith(".css")


def is_runtime_url(u: str) -> bool:
    name = os.path.basename(urlparse(u).path).lower()
    return name.startswith("runtime.") and name.endswith(".js")


class AssetHTMLParser(HTMLParser):
    def __init__(self, base_url: str):
        super().__init__()
        self.base_url = base_url
        self.assets: set[str] = set()

    def _add(self, ref: str | None) -> None:
        if not ref:
            return

        ref = html.unescape(ref.strip())
        if not ref:
            return

        u = clean_url(urljoin(self.base_url, ref))

        if is_js_or_css_url(u) and not is_ignored_asset_url(u):
            self.assets.add(u)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        attr_map = {k.lower(): v for k, v in attrs}

        if tag == "script":
            self._add(attr_map.get("src"))
            return

        if tag == "link":
            href = attr_map.get("href")
            rel = (attr_map.get("rel") or "").lower()

            if "stylesheet" in rel:
                self._add(href)
                return

            if href and urlparse(href).path.lower().endswith(".css"):
                self._add(href)
                return


def extract_html_assets(html_text: str, base_url: str) -> set[str]:
    parser = AssetHTMLParser(base_url)
    parser.feed(html_text)
    return parser.assets


def extract_public_path(runtime_text: str) -> str | None:
    """
    Common webpack form:

        r.p="/jsb-wap/"

    or:

        someRuntimeObject.p="/jsb-wap/"
    """
    m = re.search(r'\b\w+\.p\s*=\s*["\']([^"\']+)["\']', runtime_text)
    return m.group(1) if m else None


def normalize_public_path(p: str) -> str:
    if not p.startswith("/"):
        p = "/" + p

    if not p.endswith("/"):
        p += "/"

    return p


def parse_numeric_string_map(obj: str) -> dict[int, str]:
    """
    Parses webpack-style object fragments such as:

        13:"3aa377f241ee09054740"
        10:"Vote"
        "13":"3aa377f241ee09054740"

    Returns:

        {13: "3aa377f241ee09054740"}
    """
    pairs = re.findall(
        r'["\']?(\d+)["\']?\s*:\s*["\']([^"\']+)["\']',
        obj,
    )
    return {int(k): v for k, v in pairs}


def parse_js_chunk_map(runtime_text: str) -> dict[int, str]:
    """
    Looks for webpack runtime code like:

        r.p+"static/js/"+e+"."+{13:"xxxx",11:"yyyy"}[e]+".js"

    Returns:

        {13: "xxxx", 11: "yyyy"}
    """
    patterns = [
        r'\b\w+\.p\s*\+\s*["\']static/js/["\']\s*\+\s*e\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[e\]\s*\+\s*["\']\.js["\']',
        r'["\']static/js/["\']\s*\+\s*e\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[e\]\s*\+\s*["\']\.js["\']',
        r'\b\w+\.p\s*\+\s*["\']static/js/["\']\s*\+\s*\w+\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[\w+\]\s*\+\s*["\']\.js["\']',
        r'["\']static/js/["\']\s*\+\s*\w+\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[\w+\]\s*\+\s*["\']\.js["\']',
    ]

    for pat in patterns:
        m = re.search(pat, runtime_text, flags=re.DOTALL)
        if not m:
            continue

        raw_map = parse_numeric_string_map(m.group(1))

        return {
            k: v
            for k, v in raw_map.items()
            if re.fullmatch(r"[0-9a-fA-F]{8,}", v)
        }

    return {}


def parse_css_chunk_map(runtime_text: str) -> tuple[dict[int, str], dict[int, str]]:
    """
    Looks for webpack runtime code like:

        "static/css/"+({10:"Vote"}[e]||e)+"."+{10:"abcd"}[e]+".css"

    Returns:

        name_map = {10: "Vote"}
        hash_map = {10: "abcd"}
    """
    name_map: dict[int, str] = {}
    hash_map: dict[int, str] = {}

    combined_patterns = [
        r'["\']static/css/["\']\s*\+\s*\(\s*\{(.*?)\}\[e\]\s*\|\|\s*e\s*\)\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[e\]\s*\+\s*["\']\.css["\']',
        r'["\']static/css/["\']\s*\+\s*\(\s*\{(.*?)\}\[\w+\]\s*\|\|\s*\w+\s*\)\s*\+\s*["\']\.["\']\s*\+\s*\{(.*?)\}\[\w+\]\s*\+\s*["\']\.css["\']',
    ]

    for pat in combined_patterns:
        m = re.search(pat, runtime_text, flags=re.DOTALL)
        if not m:
            continue

        name_map = parse_numeric_string_map(m.group(1))

        raw_hash_map = parse_numeric_string_map(m.group(2))
        hash_map = {
            k: v
            for k, v in raw_hash_map.items()
            if re.fullmatch(r"[0-9a-fA-F]{8,}", v)
        }

        return name_map, hash_map

    # Fallback: find name map separately.
    m_name = re.search(
        r'\(\s*\{(.*?)\}\[e\]\s*\|\|\s*e\s*\)',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m_name:
        m_name = re.search(
            r'\(\s*\{(.*?)\}\[\w+\]\s*\|\|\s*\w+\s*\)',
            runtime_text,
            flags=re.DOTALL,
        )

    if m_name:
        name_map = parse_numeric_string_map(m_name.group(1))

    # Fallback: find CSS hash map separately.
    m_hash = re.search(
        r'["\']static/css/["\']\s*\+.*?\+\s*\{(.*?)\}\[e\]\s*\+\s*["\']\.css["\']',
        runtime_text,
        flags=re.DOTALL,
    )
    if not m_hash:
        m_hash = re.search(
            r'["\']static/css/["\']\s*\+.*?\+\s*\{(.*?)\}\[\w+\]\s*\+\s*["\']\.css["\']',
            runtime_text,
            flags=re.DOTALL,
        )

    if m_hash:
        raw_hash_map = parse_numeric_string_map(m_hash.group(1))
        hash_map = {
            k: v
            for k, v in raw_hash_map.items()
            if re.fullmatch(r"[0-9a-fA-F]{8,}", v)
        }

    return name_map, hash_map


def runtime_indexed_assets(
    runtime_text: str,
    *,
    origin: str,
    public_path_override: str = "",
) -> set[str]:
    parsed_public_path = extract_public_path(runtime_text) or "/"
    public_path = normalize_public_path(public_path_override.strip() or parsed_public_path)

    js_map = parse_js_chunk_map(runtime_text)
    name_map, css_map = parse_css_chunk_map(runtime_text)

    targets: set[str] = set()

    for chunk_id, chunk_hash in sorted(js_map.items()):
        path = f"{public_path}static/js/{chunk_id}.{chunk_hash}.js"
        targets.add(clean_url(urljoin(origin, path)))

    for chunk_id, chunk_hash in sorted(css_map.items()):
        css_name = name_map.get(chunk_id, str(chunk_id))
        path = f"{public_path}static/css/{css_name}.{chunk_hash}.css"
        targets.add(clean_url(urljoin(origin, path)))

    return {
        u
        for u in targets
        if is_js_or_css_url(u) and not is_ignored_asset_url(u)
    }


def save_page_html_as_index(out_root: str, page_url: str, data: bytes) -> str:
    """
    Save the fetched page HTML as index.html under the URL path.

    Example:
        page_url = https://jsb.notebookvip.cn/jsb-wap/
        output   = jsb_web/jsb-wap/index.html
    """
    path = urlparse(page_url).path

    if path.endswith("/"):
        rel = path.lstrip("/") + "index.html"
    else:
        rel = path.lstrip("/")
        if not os.path.basename(rel):
            rel = os.path.join(rel, "index.html")

    local_path = os.path.join(out_root, rel)
    ensure_parent(local_path)

    with open(local_path, "wb") as f:
        f.write(data)

    return local_path

def http_get_bytes(
    url: str,
    session: requests.Session,
    cache: dict[str, bytes],
    *,
    retries: int = 3,
    timeout: int = 30,
    chunk_size: int = 1024 * 128,
) -> bytes:
    url = clean_url(url)

    if url in cache:
        print(f"    cached -> {url}")
        return cache[url]

    last_exc: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            print(f"    downloading -> {url}")

            with session.get(url, timeout=timeout, stream=True) as r:
                r.raise_for_status()

                total_header = r.headers.get("Content-Length")
                total = int(total_header) if total_header and total_header.isdigit() else 0

                chunks: list[bytes] = []
                downloaded = 0
                last_print_time = 0.0

                for chunk in r.iter_content(chunk_size=chunk_size):
                    if not chunk:
                        continue

                    chunks.append(chunk)
                    downloaded += len(chunk)

                    now = time.time()

                    # Avoid too much terminal spam, but always print first and final-ish updates.
                    if now - last_print_time >= 0.1:
                        if total:
                            pct = downloaded / total * 100
                            msg = (
                                f"\r        {human_bytes(downloaded)} / "
                                f"{human_bytes(total)} ({pct:5.1f}%)"
                            )
                        else:
                            msg = f"\r        {human_bytes(downloaded)}"

                        print(msg, end="", flush=True)
                        last_print_time = now

                if total:
                    print(
                        f"\r        {human_bytes(downloaded)} / "
                        f"{human_bytes(total)} (100.0%)"
                    )
                else:
                    print(f"\r        {human_bytes(downloaded)}")

                data = b"".join(chunks)
                cache[url] = data
                return data

        except Exception as e:
            last_exc = e
            print(f"\n    attempt {attempt}/{retries} failed: {e}")

            if attempt < retries:
                time.sleep(0.8 * attempt)

    raise last_exc if last_exc else RuntimeError(f"failed to fetch {url}")


def save_file(out_root: str, url: str, data: bytes) -> str:
    path = urlparse(url).path
    rel = path.lstrip("/") or "index.html"
    local_path = os.path.join(out_root, rel)

    ensure_parent(local_path)

    with open(local_path, "wb") as f:
        f.write(data)

    return local_path


def fetch_and_save(
    url: str,
    out_root: str,
    session: requests.Session,
    cache: dict[str, bytes],
) -> str:
    data = http_get_bytes(url, session, cache)
    return save_file(out_root, url, data)


def main() -> int:
    ap = argparse.ArgumentParser()

    ap.add_argument(
        "--page-url",
        default=DEFAULT_PAGE_URL,
        help=f"HTML page URL to fetch and parse. Default: {DEFAULT_PAGE_URL}",
    )
    ap.add_argument(
        "--out",
        default=DEFAULT_OUT_DIR,
        help=f"Output folder. Default: {DEFAULT_OUT_DIR}",
    )
    ap.add_argument(
        "--origin",
        default="",
        help="Override origin, e.g. https://jsb.notebookvip.cn",
    )
    ap.add_argument(
        "--public-path",
        default="",
        help="Override webpack publicPath, e.g. /jsb-wap/",
    )
    ap.add_argument(
        "--user-agent",
        default=(
                "Mozilla/5.0 (Linux; Android 14; Pixel 8) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/147.0.0.0 Mobile Safari/537.36"
        ),
    )

    args = ap.parse_args()

    page_url = args.page_url
    origin = args.origin.strip() or guess_origin(page_url)

    session = requests.Session()
    session.headers.update({"User-Agent": args.user_agent})

    cache: dict[str, bytes] = {}

    print(f"[+] Fetch page HTML: {page_url}")

    try:
        html_bytes = http_get_bytes(page_url, session, cache)
    except Exception as e:
        print(f"[!] Failed to fetch page HTML: {e}", file=sys.stderr)
        return 1

    html_saved_path = save_page_html_as_index(args.out, page_url, html_bytes)
    print(f"[+] Saved page HTML -> {html_saved_path}")

    html_text = html_bytes.decode("utf-8", errors="replace")

    html_assets = extract_html_assets(html_text, page_url)
    targets: set[str] = set(html_assets)

    print(f"[+] HTML js/css assets: {len(html_assets)}")
    for u in sorted(html_assets):
        print(f"    HTML -> {u}")

    runtime_urls = {u for u in html_assets if is_runtime_url(u)}

    print(f"[+] Runtime files to inspect: {len(runtime_urls)}")

    for runtime_url in sorted(runtime_urls):
        print(f"[+] Fetch/parse runtime: {runtime_url}")

        try:
            runtime_bytes = http_get_bytes(runtime_url, session, cache)
        except Exception as e:
            print(f"    runtime fetch failed: {e}")
            continue

        runtime_text = runtime_bytes.decode("utf-8", errors="replace")

        indexed = runtime_indexed_assets(
            runtime_text,
            origin=origin,
            public_path_override=args.public_path,
        )

        print(f"    runtime-indexed js/css assets: {len(indexed)}")
        for u in sorted(indexed):
            print(f"    Runtime -> {u}")

        targets.update(indexed)

    targets = {
        clean_url(u)
        for u in targets
        if is_js_or_css_url(u) and not is_ignored_asset_url(u)
    }

    print(f"[+] Total js/css targets to download: {len(targets)}")
    print(f"[+] Output folder: {args.out}")

    ok = 0
    fail = 0

    for idx, url in enumerate(sorted(targets), 1):
        print(f"[{idx}/{len(targets)}] {url}")

        try:
            saved_path = fetch_and_save(url, args.out, session, cache)
            ok += 1
            print(f"        saved -> {saved_path}")
        except Exception as e:
            fail += 1
            print(f"        FAIL -> {e}")

    print(f"[+] Done. OK={ok}, FAIL={fail}, out={args.out}")

    return 0 if fail == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())