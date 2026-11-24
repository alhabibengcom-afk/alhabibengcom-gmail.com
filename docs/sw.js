/* Happiness Plaza brand guide: service worker.
   Keeps the app shell available for fast reopening and offline viewing.
   Pages and code: network first, cached copy when offline.
   Images and fonts: cache first, filled as the visitor browses.
   Videos and PDFs are never cached (large files, range requests). */
const VERSION = 'hp-v15-9';
const SHELL = [
  './',
  'index.html',
  'styles.css?v=15',
  'unit-viewer.css?v=15',
  'location-view.css?v=15',
  'pro.css?v=15',
  'i18n-en.js?v=15',
  'i18n.js?v=15',
  'unit-data.js?v=15',
  'corridor-view.js?v=15',
  'location-links.js?v=15',
  'location-url.js?v=15',
  'location-view.js?v=15',
  'panorama.js?v=15',
  'unit-viewer.js?v=15',
  'document-links.js?v=15',
  'document-data.js?v=15',
  'site.js?v=15',
  'documents.js?v=15',
  'hospitality.js?v=15',
  'manifest.webmanifest',
  'app/icon-192.png',
  'assets/Happiness_Plaza_Opening.jpg'
];

self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys()
      .then(keys => Promise.all(keys.filter(k => k !== VERSION).map(k => caches.delete(k))))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', event => {
  const req = event.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;
  if (/\.(mp4|pdf)$/i.test(url.pathname) || req.headers.has('range')) return;

  const isMedia = /\.(jpe?g|png|webp|gif|svg|woff2?)$/i.test(url.pathname);
  if (isMedia) {
    event.respondWith(
      caches.match(req).then(hit => hit || fetch(req).then(res => {
        if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
        return res;
      }))
    );
    return;
  }

  event.respondWith(
    fetch(req).then(res => {
      if (res.ok) { const copy = res.clone(); caches.open(VERSION).then(c => c.put(req, copy)); }
      return res;
    }).catch(() => caches.match(req, { ignoreSearch: req.mode === 'navigate' })
      .then(hit => hit || caches.match('index.html')))
  );
});
