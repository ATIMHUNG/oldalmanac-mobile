#!/usr/bin/env python3
"""生成「单文件版」index-standalone.html —— 双击即可打开（file:// 可用）。

与 dist/ 版的区别：
  - 模板分片不再走网络，全部内联进 HTML（约 12 MB，体积大但自包含）
  - 因此不需要 http 服务，拷到 U 盘/NAS 任意位置都能开

用法：python3 tools/build_standalone.py
产物：./standalone/index-standalone.html
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "standalone"


def main() -> int:
    src = (ROOT / "dist" / "index.html")
    if not src.exists():
        print("请先运行 tools/build.py 生成 dist/", file=sys.stderr)
        return 1
    html = src.read_text(encoding="utf-8")

    # ---- 1) 内联全部模板图片分片 ----
    shell = json.loads((ROOT / "tpl" / "shell.json").read_text(encoding="utf-8"))
    assets = {}
    for aid in shell["assets"]:
        p = ROOT / "tpl" / "assets" / f"{aid}.json"
        if p.exists():
            a = json.loads(p.read_text(encoding="utf-8"))
            assets[aid] = {"data": a["data"], "width": a["width"], "height": a["height"]}

    # 组装成完整模板库（即上游 calendar-templates.json 的等价物）
    full_pack = {
        "format": shell["format"],
        "version": shell["version"],
        "kind": shell["kind"],
        "canvas": shell["canvas"],
        "css": shell["css"],
        "assets": assets,
        "templates": shell["templates"],
    }
    payload = json.dumps(full_pack, ensure_ascii=False, separators=(",", ":"))
    # 防止 </script> 提前闭合
    payload = payload.replace("</", "<\\/")

    inline_tpl = f"<script>/* 内联模板库：使 file:// 双击打开也能显示节气插画 */\nwindow.__OA_TPL__={payload};</script>\n"

    # ---- 2) 替换模板加载逻辑为「直接读内联」 ----
    old = 'const TPL_BASE = "data/";'
    new = 'const TPL_BASE = "data/";\n      const INLINE_TPL = window.__OA_TPL__ || null;'
    if old not in html:
        print("找不到 TPL_BASE 锚点", file=sys.stderr)
        return 1
    html = html.replace(old, new, 1)

    old_init = """      async function initLibrary() {
        artBusy = true;
        try {
          if (!window.CalendarArt) throw new Error("calendar-art.js 未加载");
          if (location.protocol === "file:") throw new Error("file:// 下无法读取模板分片");
          window.CalendarArt.setAssetLoader(makeAssetLoader());
          window.CalendarArt.use(await loadTplShell(), "tpl/shell.json");
        } catch (error) {
          console.warn("[Calendar Art] " + (error.message || "模板读取失败") + "；日期数字照常显示。");
        } finally { artBusy = false; }
      }"""
    new_init = """      async function initLibrary() {
        artBusy = true;
        try {
          if (!window.CalendarArt) throw new Error("calendar-art.js 未加载");
          // 单文件版：模板库已内联，无需网络；分片加载器仅作兜底。
          if (INLINE_TPL) {
            window.CalendarArt.setAssetLoader(null);
            window.CalendarArt.use(INLINE_TPL, "inline");
          } else {
            window.CalendarArt.setAssetLoader(makeAssetLoader());
            window.CalendarArt.use(await loadTplShell(), "tpl/shell.json");
          }
        } catch (error) {
          console.warn("[Calendar Art] " + (error.message || "模板读取失败") + "；日期数字照常显示。");
        } finally { artBusy = false; }
      }"""
    if old_init not in html:
        print("找不到 initLibrary 锚点", file=sys.stderr)
        return 1
    html = html.replace(old_init, new_init, 1)

    # ---- 3) 注入内联模板（放在主脚本前的内联数据之后） ----
    anchor = '  <script src="./lunar.js"'
    html = html.replace(anchor, inline_tpl + anchor, 1)

    # ---- 4) 内联四个外部脚本，做成真正的单文件 ----
    def inline_script(m: re.Match) -> str:
        rel = m.group(1).split("?")[0].lstrip("./")
        p = ROOT / "dist" / rel
        if not p.exists():
            print(f"⚠️  找不到 {rel}，保持外链", file=sys.stderr)
            return m.group(0)
        code = p.read_text(encoding="utf-8")
        # 防止脚本内容里的 </script> 提前闭合
        code = code.replace("</script", "<\\/script")
        onerror = m.group(2) or ""
        return f"<script{onerror}>\n{code}\n</script>"

    html = re.sub(
        r'<script src="\./([^"]+)"([^>]*)></script>',
        inline_script,
        html,
    )

    # 字体也内联成 data URI（file:// 下相对路径其实可用，但内联后真正单文件）
    for font, mime in [
        ("FZXingKai-S04S.subset.woff2", "font/woff2"),
        ("STHupo.woff2", "font/woff2"),
        ("remixicon-subset.woff2", "font/woff2"),
    ]:
        p = ROOT / "dist" / font
        if not p.exists():
            continue
        import base64

        b64 = base64.b64encode(p.read_bytes()).decode()
        html = html.replace(f"./{font}", f"data:{mime};base64,{b64}")

    # 字体 ttf 同样内联
    for ttf in ("shengxiao.ttf", "shengxiao1.ttf"):
        p = ROOT / "dist" / ttf
        if not p.exists():
            continue
        import base64

        b64 = base64.b64encode(p.read_bytes()).decode()
        html = html.replace(f"./{ttf}", f"data:font/ttf;base64,{b64}")

    # ---- 5) 关掉 PWA 注册（file:// 下无意义） ----
    html = html.replace(
        'if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {',
        'if (false && "serviceWorker" in navigator && location.protocol.startsWith("http")) {',
        1,
    )

    OUT.mkdir(exist_ok=True)
    out = OUT / "index-standalone.html"
    out.write_text(html, encoding="utf-8")
    size = out.stat().st_size
    print(f"standalone/index-standalone.html  {size:,} B  ({size/1024/1024:.2f} MB)")
    print("双击即可打开，无需 http 服务。")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
