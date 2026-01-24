#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Download a list of image URLs and preserve URL directory structure.

Example output:

  https://jsb.notebookvip.cn/jsb-files/applogo/weibo.png
  -> out/jsb-files/applogo/weibo.png

  https://img01.yzcdn.cn/vant/coupon-empty.png
  -> out/vant/coupon-empty.png
"""

from __future__ import annotations

import os
import time
import argparse
from urllib.parse import urlparse

import requests


URLS = [
    # --- default_img ---
    "https://jsb.notebookvip.cn/jsb-files/default_img/zhuanlan_01.png",
    "https://jsb.notebookvip.cn/jsb-files/default_img/zhuanlan_02.png",
    "https://jsb.notebookvip.cn/jsb-files/default_img/zhuanlan_03.png",
    "https://jsb.notebookvip.cn/jsb-files/default_img/zhuanlan_04.png",
    "https://jsb.notebookvip.cn/jsb-files/default_img/zhuanlan_05.png",

    # --- applogo ---
    "https://jsb.notebookvip.cn/jsb-files/applogo/baidu.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/benteng_rongmei.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/bilibili.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/cac.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/caoyuan_quanmei.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/cctv.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/cctv_net.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/changjiangyun.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/douyin.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/fenghuang.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/hubeiribao.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/kuaishou.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/other.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/people.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/people_rb.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/sina.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/souhu.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/study.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/tencent.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/toutiao.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/wangyi.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/weibo.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/weixin.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/xinhua_net.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/xinhuashe.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/yidianzx.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/zhihu.png",
    "https://jsb.notebookvip.cn/jsb-files/applogo/zxw.png",

    # --- external images ---
    "https://img01.yzcdn.cn/upload_files/2020/06/24/FmKWDg0bN9rMcTp9ne8MXiQWGtLn.png",
    "https://img01.yzcdn.cn/vant/coupon-empty.png",

    # --- static/img ---
    "https://jsb.notebookvip.cn/jsb-wap/static/img/20220321.87ab634.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/20231009_banner.8233434.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/baidu.2edb6eb.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/banner1.5db8dd7.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/capture_1.4793ac0.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/capture_2.69fab31.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/capture_3.fb225f5.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/create.6be0c80.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/create_active.154c8fe.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/description_1.ca65eb8.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/description_2.1b64336.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/face.6d6e017.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/feedback.ab90ae3.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/feedback_1.a81b0f6.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/feedback_2.6747bbc.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/fenghuang.19af9c8.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/figerprint.58e45eb.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/heroes.42c6bba.jpg",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/hot.514aa01.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/icon-score.67caff5.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/icon-statistics.6869dd2.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/login.e154576.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/logo_2.e8ac193.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/my.fef0f82.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/my_active.8ed115d.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/notification_bar_diagram.1cbbbcc.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pengpai.41acd3a.jpeg",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/permission_1.3f4b7e3.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/permission_2.cb69755.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/permission_3.88e1f1a.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/permission_4.308ab85.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/permission_5.bbef38d.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pingce_award.0bda695.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pingce_award_poster.82c216c.jpg",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pwd_1.d94eab1.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pwd_2.23f76fb.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/pwd_3.4b08e81.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/share_1.d7f1458.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/share_2.4bb75f7.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/share_3.37288f0.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/sina.bb843a4.jpeg",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/souhu.c9ac253.jpeg",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/square.dc53b66.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/square_active.d04d5a3.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/statistics.061deed.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/statistics_active.db0cba6.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/tengxun.74ffd75.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/toutiao.a2d10c5.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/toutiao.b9e50be.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/toutiao_active.dc06fc8.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/unlock_1.4b9392f.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/unlock_2.047d630.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/video_empty.c4bc188.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/wangyi.0ff45c8.png",
    "https://jsb.notebookvip.cn/jsb-wap/static/img/weibo.83f4916.png",
]


def save_with_url_structure(out_root: str, url: str) -> str:
    """
    Convert URL to local path preserving directory structure:
      https://host/a/b/c.png -> out_root/host/a/b/c.png
    """
    p = urlparse(url)
    rel = p.netloc + p.path   # keep host as top folder
    rel = rel.lstrip("/")
    local_path = os.path.join(out_root, rel)
    os.makedirs(os.path.dirname(local_path), exist_ok=True)
    return local_path


def download_one(session: requests.Session, url: str, out_root: str) -> None:
    path = save_with_url_structure(out_root, url)

    if os.path.exists(path):
        print(f"[SKIP] {url}")
        return

    print(f"[GET ] {url}")
    r = session.get(url, timeout=30)
    r.raise_for_status()

    with open(path, "wb") as f:
        f.write(r.content)

    print(f"      -> {path}")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="images_out", help="Output folder")
    args = ap.parse_args()

    s = requests.Session()
    s.headers.update({
        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) Chrome/120 Safari/537.36"
    })

    ok = 0
    fail = 0

    for url in URLS:
        try:
            download_one(s, url, args.out)
            ok += 1
            time.sleep(0.1)
        except Exception as e:
            fail += 1
            print(f"[FAIL] {url}: {e}")

    print(f"\nDone. OK={ok}, FAIL={fail}")
    print(f"Saved under: {args.out}/")


if __name__ == "__main__":
    main()
