#!/usr/bin/env python3
"""为老黄历生成「月视图」页面 —— 在原单日页之外扩展一个月视图

设计：
  - 月视图网格：每格显示 公历日 + 农历日/节气/节日 + 放假/补班标签
  - 点某天 → 跳到当天详情（复用老黄历原生的单日卡片，同一套 almanac() 真算法）
  - 不重写历法：全部走 lunar.js（与老黄历一致，宜忌为真算法非伪随机）

做法：从 dist/index.html 里抽出可复用的资产（lunar.js 引用、卡片模板、样式），
生成独立的 month.html，避免改动已上线的单日页。
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def main() -> int:
    idx = (DIST / "index.html").read_text(encoding="utf-8")

    # ---------- 抽取卡片模板（#tpl 整个 div）----------
    m = re.search(r'(<div class="calendar-card" id="tpl">.*?\n    </div>)', idx, re.S)
    if not m:
        print("找不到 #tpl 卡片模板", file=sys.stderr)
        return 1
    card_tpl = m.group(1)

    # ---------- 抽取主样式（到 </style> 为止，取第一段）----------
    styles = re.findall(r"<style[^>]*>(.*?)</style>", idx, re.S)
    if not styles:
        print("找不到样式块", file=sys.stderr)
        return 1
    main_css = styles[0]

    print(f"卡片模板 {len(card_tpl):,} B | 主样式 {len(main_css):,} B")
    (ROOT / "_month_assets").mkdir(exist_ok=True)
    (ROOT / "_month_assets" / "card.html").write_text(card_tpl, encoding="utf-8")
    (ROOT / "_month_assets" / "main.css").write_text(main_css, encoding="utf-8")
    print("已导出到 _month_assets/")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
