const CACHE = 'shokuza-log-v1';
const STATIC_ASSETS = ['/', '/manifest.json'];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE).then(c => c.addAll(STATIC_ASSETS)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', e => {
  const url = new URL(e.request.url);

  // API呼び出し（/analyze, /save, /history, /record/）はネットワーク優先
  if (['/analyze', '/save', '/history'].includes(url.pathname) || url.pathname.startsWith('/record/')) {
    e.respondWith(
      fetch(e.request).catch(() =>
        new Response(JSON.stringify({ error: 'オフラインです。ネットワーク接続を確認してください。' }), {
          headers: { 'Content-Type': 'application/json' }
        })
      )
    );
    return;
  }

  // その他（ページ・静的ファイル）はキャッシュ優先
  e.respondWith(
    caches.match(e.request).then(cached => {
      const network = fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE).then(c => c.put(e.request, clone));
        }
        return res;
      });
      return cached || network;
    })
  );
});
