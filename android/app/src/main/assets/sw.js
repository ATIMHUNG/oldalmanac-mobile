/*
 * 老黄历 Service Worker
 * 策略：
 *   - 应用外壳（HTML/JS/CSS/字体/内联 JSON）：stale-while-revalidate
 *   - 模板分片 data/assets/*：cache-first（内容不变，拉过一次就别再拉）
 *   - 导航请求：优先网络，断网回退缓存
 */
const VERSION = "oa-v1";
const SHELL_CACHE = `${VERSION}-shell`;
const ASSET_CACHE = `${VERSION}-assets`;

const SHELL_FILES = [
  "./",
  "./index.html",
  "./manifest.json",
  "./lunar.js",
  "./snapdom.js",
  "./lite-datepicker.js",
  "./calendar-art.js",
  "./data/index-library.json",
  "./FZXingKai-S04S.subset.woff2",
  "./remixicon-subset.woff2",
  "./remixicon.css",
  "./STHupo.woff2",
  "./shengxiao.ttf",
  "./shengxiao1.ttf",
  "./icon.svg",
];

self.addEventListener("install", (event) => {
  event.waitUntil(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      // 单个失败不阻断安装：外层资源缺一个不该让整个 SW 挂掉。
      await Promise.all(
        SHELL_FILES.map((f) => cache.add(f).catch(() => null)),
      );
      await self.skipWaiting();
    })(),
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    (async () => {
      const keys = await caches.keys();
      await Promise.all(
        keys.filter((k) => !k.startsWith(VERSION)).map((k) => caches.delete(k)),
      );
      await self.clients.claim();
    })(),
  );
});

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;

  // 模板图片分片：cache-first，拉过一次就长期用
  if (url.pathname.includes("/data/assets/")) {
    event.respondWith(
      (async () => {
        const cache = await caches.open(ASSET_CACHE);
        const hit = await cache.match(req);
        if (hit) return hit;
        try {
          const res = await fetch(req);
          if (res.ok) cache.put(req, res.clone());
          return res;
        } catch (e) {
          return new Response("", { status: 504, statusText: "offline" });
        }
      })(),
    );
    return;
  }

  // 导航：网络优先，断网回退缓存
  if (req.mode === "navigate") {
    event.respondWith(
      (async () => {
        try {
          const res = await fetch(req);
          const cache = await caches.open(SHELL_CACHE);
          cache.put(req, res.clone());
          return res;
        } catch (e) {
          const cache = await caches.open(SHELL_CACHE);
          return (
            (await cache.match(req)) ||
            (await cache.match("./index.html")) ||
            new Response("离线且无缓存", { status: 503 })
          );
        }
      })(),
    );
    return;
  }

  // 其他同源静态资源：stale-while-revalidate
  event.respondWith(
    (async () => {
      const cache = await caches.open(SHELL_CACHE);
      const hit = await cache.match(req);
      const fetching = fetch(req)
        .then((res) => {
          if (res.ok) cache.put(req, res.clone());
          return res;
        })
        .catch(() => null);
      return hit || (await fetching) || new Response("", { status: 504 });
    })(),
  );
});
