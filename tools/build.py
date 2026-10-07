#!/usr/bin/env python3
"""把 index.html 改造成「单文件自包含 + 模板懒加载」版本。

做四件事：
  1. 内联 couplets.json / jiemeng.json / holidays.json 为 <script id="oa-data">
     → 双击 index.html 也能跑（file:// 下 fetch 会被跨域拦截）
  2. 把 loadDailyText / loadHolidayCouplets 改为「先读内联，缺了再 fetch」
  3. 把模板加载从 fetchDefault()（12 MB）换成「shell.json + 分片加载器」
  4. 注入 PWA manifest + service worker 注册（file:// 下自动跳过）

产物：./dist/index.html（原文件保持不动）
"""
import json
import re
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DIST = ROOT / "dist"


def inline_js(name: str, data) -> str:
    payload = json.dumps(data, ensure_ascii=False, separators=(",", ":"))
    return f"window.__OA__={payload};\n"


def main() -> int:
    src_html = (ROOT / "index.html").read_text(encoding="utf-8")

    couplets = json.loads((ROOT / "couplets.json").read_text(encoding="utf-8"))
    jiemeng = json.loads((ROOT / "jiemeng.json").read_text(encoding="utf-8"))
    holidays = json.loads((ROOT / "holidays.json").read_text(encoding="utf-8"))

    DIST.mkdir(exist_ok=True)

    # ---------- 1) 内联数据脚本（放在主脚本之前） ----------
    inline = (
        "<script>/* 内联数据：使 file:// 双击打开也能运行 */\n"
        + inline_js("couplets", couplets)
        + inline_js("jiemeng", jiemeng)
        + inline_js("holidays", holidays)
        + "</script>\n"
    )
    # 挂在第一个 <script src="./lunar.js"> 之前
    anchor = '  <script src="./lunar.js"'
    if anchor not in src_html:
        print("找不到注入锚点（lunar.js 脚本标签）", file=sys.stderr)
        return 1
    html = src_html.replace(anchor, inline + anchor, 1)

    # ---------- 2) loadDailyText：内联优先 ----------
    old_load = """      async function loadDailyText() {
        await Promise.all(
          Object.values(DAILY_TEXT).map(async (src) => {
            try {
              const res = await fetch(src.file);
              if (!res.ok) throw new Error(`HTTP ${res.status}`);
              const raw = await res.json();
              const items = (Array.isArray(raw) ? raw : []).map(src.normalize).filter(Boolean);
              if (!items.length) throw new Error("文件为空或格式不符");
              src.items = items;
            } catch (error) {
              console.warn(`[Calendar] 加载 ${src.file} 失败，改用内置兜底文案（本地打开时请通过 http 服务访问）：`, error);
            }
          }),
        );
      }"""
    new_load = """      async function loadDailyText() {
        const INLINE = { "couplets.json": window.__OA__?.couplets, "jiemeng.json": window.__OA__?.jiemeng };
        await Promise.all(
          Object.values(DAILY_TEXT).map(async (src) => {
            try {
              // 1) 优先用内联数据（file:// 可用）
              let raw = INLINE[src.file];
              // 2) 内联缺失时才走网络
              if (!raw) {
                const res = await fetch(src.file);
                if (!res.ok) throw new Error(`HTTP ${res.status}`);
                raw = await res.json();
              }
              const items = (Array.isArray(raw) ? raw : []).map(src.normalize).filter(Boolean);
              if (!items.length) throw new Error("文件为空或格式不符");
              src.items = items;
            } catch (error) {
              console.warn(`[Calendar] 加载 ${src.file} 失败，改用内置兜底文案：`, error);
            }
          }),
        );
      }"""
    if old_load not in html:
        print("loadDailyText 锚点不匹配", file=sys.stderr)
        return 1
    html = html.replace(old_load, new_load, 1)

    # ---------- 3) loadHolidayCouplets：内联优先 ----------
    old_hol = """        try {
          const res = await fetch(HOLIDAY_COUPLETS.file);
          if (!res.ok) throw new Error(`HTTP ${res.status}`);
          const raw = await res.json();
          const map = Object.create(null);"""
    new_hol = """        try {
          let raw = window.__OA__?.holidays;
          if (!raw) {
            const res = await fetch(HOLIDAY_COUPLETS.file);
            if (!res.ok) throw new Error(`HTTP ${res.status}`);
            raw = await res.json();
          }
          const map = Object.create(null);"""
    if old_hol not in html:
        print("loadHolidayCouplets 锚点不匹配", file=sys.stderr)
        return 1
    html = html.replace(old_hol, new_hol, 1)

    # ---------- 4) 模板加载：shell.json + 分片 ----------
    old_lib = """      async function initLibrary() {
        artBusy = true;
        try {
          if (!window.CalendarArt) throw new Error("calendar-art.js 未加载");
          window.CalendarArt.use(await window.CalendarArt.fetchDefault(), "calendar-templates.json");
        } catch (error) {
          console.warn("[Calendar Art] " + (error.message || "模板读取失败") + "；日期数字照常显示。");
        } finally { artBusy = false; }
      }"""
    new_lib = """      // 分片模式：外壳（模板定义+CSS+尺寸元数据，约 95 KB）常驻，
      // 图片按模板 id 从 tpl/assets/<assetId>.json 按需拉取，拉过的进内存缓存。
      const TPL_BASE = "data/";
      async function loadTplShell() {
        const res = await fetch(TPL_BASE + "index-library.json", { cache: "force-cache" });
        if (!res.ok) throw new Error("模板库 HTTP " + res.status);
        return await res.json();
      }
      function makeAssetLoader() {
        const inflight = new Map();
        return (assetId) => {
          if (inflight.has(assetId)) return inflight.get(assetId);
          const p = (async () => {
            try {
              const res = await fetch(TPL_BASE + "assets/" + encodeURIComponent(assetId) + ".json", { cache: "force-cache" });
              if (!res.ok) return null;
              return await res.json();
            } catch (error) {
              console.warn("[Calendar Art] 图片分片拉取失败：" + assetId, error);
              return null;
            } finally {
              inflight.delete(assetId);
            }
          })();
          inflight.set(assetId, p);
          return p;
        };
      }
      async function initLibrary() {
        artBusy = true;
        try {
          if (!window.CalendarArt) throw new Error("calendar-art.js 未加载");
          if (location.protocol === "file:") throw new Error("file:// 下无法读取模板分片");
          window.CalendarArt.setAssetLoader(makeAssetLoader());
          window.CalendarArt.use(await loadTplShell(), "data/index-library.json");
        } catch (error) {
          console.warn("[Calendar Art] " + (error.message || "模板读取失败") + "；日期数字照常显示。");
        } finally { artBusy = false; }
      }"""
    if old_lib not in html:
        print("initLibrary 锚点不匹配", file=sys.stderr)
        return 1
    html = html.replace(old_lib, new_lib, 1)

    # ---------- 5) 渲染前预热模板图片，避免首帧空插画 ----------
    old_apply = """      async function prepareCalendarArt(card, d) {
        try { return await window.CalendarArt?.apply(card, d, themePalette(!!d?.isWeekend).primary); }
        catch (error) { console.warn("[Calendar Art] 保留日期数字：", error); return null; }
      }"""
    new_apply = """      async function prepareCalendarArt(card, d) {
        try {
          const CA = window.CalendarArt;
          if (!CA) return null;
          // 先按候选模板预热图片（分片模式），再走正常渲染；预热失败不影响降级。
          if (CA.preloadTemplate && CA.candidates) {
            const ids = CA.candidates(d.date);
            if (ids.length) await Promise.all(ids.slice(0, 2).map((id) => CA.preloadTemplate(id).catch(() => null)));
          }
          return await CA.apply(card, d, themePalette(!!d?.isWeekend).primary);
        }
        catch (error) { console.warn("[Calendar Art] 保留日期数字：", error); return null; }
      }"""
    if old_apply not in html:
        print("prepareCalendarArt 锚点不匹配", file=sys.stderr)
        return 1
    html = html.replace(old_apply, new_apply, 1)

    # ---------- 6) PWA manifest + SW 注册 ----------
    pwa = """<link rel="manifest" href="manifest.json" />"""
    if '<link rel="icon" href="data:," />' in html:
        html = html.replace('<link rel="icon" href="data:," />', '<link rel="icon" href="data:," />\n  ' + pwa, 1)

    sw = """<script>
// PWA：注册 Service Worker（file:// 下自动跳过）。缓存静态资源，断网也能开。
if ("serviceWorker" in navigator && location.protocol.startsWith("http")) {
  window.addEventListener("load", () => {
    navigator.serviceWorker.register("sw.js").catch((e) => console.warn("[PWA] SW 注册失败：", e));
  });
}
</script>
</body>"""
    html = html.replace("</body>", sw, 1)

    # ---------- 返回月视图悬浮按钮 ----------
    # 单日页原本没有任何回月视图的入口（点 ☰ 进来就是单向路），这里补一个。
    # 只在从月视图进入（?from=month）或宽屏以外都显示，保证随时能回去。
    back = """<style>
  #backToMonth {
    position: fixed; left: 50%; transform: translateX(-50%);
    bottom: calc(18px + env(safe-area-inset-bottom)); z-index: 999;
    display: inline-flex; align-items: center; gap: 6px;
    padding: 10px 20px; border: 1px solid #E8E8E8; border-radius: 999px;
    background: rgba(255,255,255,.94); backdrop-filter: blur(8px);
    color: #333; font-size: 14px; font-family: inherit; text-decoration: none;
    box-shadow: 0 3px 14px rgba(0,0,0,.13); cursor: pointer;
    -webkit-tap-highlight-color: transparent;
  }
  #backToMonth:active { background: #F2F2F2; }
  #backToMonth b { color: #E22B37; font-weight: 700; }
</style>
<a id="backToMonth" href="./"><b>‹</b> 返回月视图</a>
</body>"""
    html = html.replace("</body>", back, 1)

    # ---------- 写出 ----------
    out = DIST / "day.html"
    out.write_text(html, encoding="utf-8")

    # 复制依赖到 dist
    for f in [
        "lunar.js", "snapdom.js", "lite-datepicker.js", "calendar-art.js",
        "FZXingKai-S04S.subset.woff2", "remixicon-subset.woff2", "STHupo.woff2",
        "shengxiao.ttf", "shengxiao1.ttf", "remixicon.css",
    ]:
        p = ROOT / f
        if p.exists():
            shutil.copy2(p, DIST / f)
        else:
            print(f"⚠️  缺失依赖 {f}", file=sys.stderr)

    # 模板分片目录（用 data/ 而非 tpl/：CF 免费版 WAF 会拦 /tpl/ 路径）
    tpl_dst = DIST / "data"
    if tpl_dst.exists():
        shutil.rmtree(tpl_dst)
    stale = DIST / "tpl"
    if stale.exists():
        shutil.rmtree(stale)
    shutil.copytree(ROOT / "tpl", DIST / "data")

    print(f"dist/day.html  {out.stat().st_size:,} B  ({out.stat().st_size/1024:.1f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
