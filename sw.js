/* 自動生成 — 編集しないこと。build.py が _sw.template.js から生成する。 */
var CACHE = 'pocket-cards-c93659df7e4b';

var ASSETS = [
  "./",
  "./index.html",
  "./app.webmanifest",
  "./icons/icon-192.png",
  "./icons/icon-512.png",
  "./icons/icon-maskable-512.png",
  "./icons/icon-180.png",
  "./cards/nms.html",
  "./cards/ich-postop.html",
  "./cards/ich-targets.html",
  "./cards/nephrosclerosis.html",
  "./cards/respiratory-mechanics.html",
  "./cards/ncse-eeg-trainer.html"
];

// 新バージョンをまとめて取り込み、即座に有効化する
self.addEventListener('install', function (e) {
  e.waitUntil(
    caches.open(CACHE)
      .then(function (c) { return c.addAll(ASSETS); })
      .then(function () { return self.skipWaiting(); })
  );
});

// 旧バージョンのキャッシュを破棄
self.addEventListener('activate', function (e) {
  e.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.map(function (k) {
        if (k !== CACHE && k.indexOf('pocket-cards-') === 0) return caches.delete(k);
      }));
    }).then(function () { return self.clients.claim(); })
  );
});

// キャッシュ優先 + バックグラウンド更新（stale-while-revalidate）
self.addEventListener('fetch', function (e) {
  var req = e.request;
  if (req.method !== 'GET') return;
  if (new URL(req.url).origin !== self.location.origin) return;

  e.respondWith(
    caches.match(req).then(function (cached) {
      var fresh = fetch(req).then(function (res) {
        if (res && res.ok) {
          var copy = res.clone();
          caches.open(CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        // オフラインでページ遷移した場合はハブを返す
        if (req.mode === 'navigate') return caches.match('./index.html');
        return cached;
      });
      return cached || fresh;
    })
  );
});
