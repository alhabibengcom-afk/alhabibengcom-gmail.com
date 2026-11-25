/* Happiness Plaza brand guide: service worker.
   Keeps the app shell available for fast reopening and offline viewing.
   Pages and code: network first, cached copy when offline.
   Images and fonts: cache first, filled as the visitor browses.
   Videos and PDFs are never cached (large files, range requests). */
const VERSION = 'hp-v15-31';
const SHELL = [
  './',
  'index.html',
  'styles.css?v=15',
  'unit-viewer.css?v=15',
  'location-view.css?v=15',
  'pro.css?v=15t',
  'i18n-en.js?v=15n',
  'i18n.js?v=15b',
  'unit-data.js?v=15',
  'corridor-view.js?v=15',
  'location-links.js?v=15c',
  'location-url.js?v=15',
  'location-view.js?v=15c',
  'panorama.js?v=15',
  'unit-viewer.js?v=15b',
  'document-links.js?v=15',
  'document-data.js?v=15',
  'site-full.js?v=5',
  'i18n-en-full.js?v=5',
  'launcher.js?v=15g',
  'phases.js?v=1',
  'lite.js?v=15b',
  'documents.js?v=15f',
  'hospitality.js?v=15b',
  'lite.html',
  'i18n-en-lite.js?v=12',
  'unit-viewer-lite.js?v=1',
  'site-lite.js?v=10',
  'lite.js?v=4',
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
