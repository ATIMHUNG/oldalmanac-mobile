#!/usr/bin/env python3
"""把 calendar-templates.json 拆成「常驻外壳 + 按需图片分片」。

产物（写入 ./tpl/）：
  index-library.json  模板定义 + CSS + asset 元数据（不含 base64），约 95 KB（原名 shell.json，因 CF WAF 拦 "shell" 字样而改名）
  assets/<id>.json    单个 asset 的 data URI，按需拉取

上游 calendar-art.js 已打过补丁：shell.json 交给 use()，
       图片交给 setAssetLoader() 注册的加载器按需补齐。
"""
import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SRC = ROOT / "calendar-templates.json"
OUT = ROOT / "tpl"
ASSETS = OUT / "assets"

SHARD_RE = re.compile(r"^[\w-]{1,100}$")


def main() -> int:
    if not SRC.exists():
        print(f"找不到 {SRC}", file=sys.stderr)
        return 1
    raw = json.loads(SRC.read_text(encoding="utf-8"))

    ASSETS.mkdir(parents=True, exist_ok=True)

    # ---- 1) 拆图片 ----
    asset_meta = {}
    total_bytes = 0
    for aid, a in raw["assets"].items():
        if not SHARD_RE.match(aid) or aid in ("__proto__", "constructor", "prototype"):
            print(f"跳过非法 asset id: {aid}", file=sys.stderr)
            continue
        payload = {"id": aid, "data": a["data"], "width": a["width"], "height": a["height"]}
        (ASSETS / f"{aid}.json").write_text(
            json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
            encoding="utf-8",
        )
        asset_meta[aid] = {"width": a["width"], "height": a["height"]}
        total_bytes += len(a["data"]) * 3 // 4

    # ---- 2) 写外壳（去掉 base64，只留元数据）----
    shell = {
        "format": raw["format"],
        "version": raw["version"],
        "kind": raw["kind"],
        "canvas": raw["canvas"],
        "css": raw["css"],
        "assets": asset_meta,
        "templates": raw["templates"],
    }
    if "dateRules" in raw:
        shell["dateRules"] = raw["dateRules"]

    shell_path = OUT / "index-library.json"
    shell_path.write_text(
        json.dumps(shell, ensure_ascii=False, separators=(",", ":")), encoding="utf-8"
    )

    # ---- 3) 报告 ----
    orig = SRC.stat().st_size
    new_shell = shell_path.stat().st_size
    n = len(asset_meta)
    print(f"原文件      {orig:>12,} B  ({orig / 1024 / 1024:.2f} MB)")
    print(f"外壳        {new_shell:>12,} B  ({new_shell / 1024:.1f} KB)  ← 首屏只下这个")
    print(f"分片        {n:>12} 个，共 {total_bytes:,} B  ({total_bytes / 1024 / 1024:.2f} MB)  ← 按需")
    print(f"首屏降幅    {(1 - new_shell / orig) * 100:.1f}%")
    avg = total_bytes / n if n else 0
    print(f"平均单片    {avg / 1024:.1f} KB")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
