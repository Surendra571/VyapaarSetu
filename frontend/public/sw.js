const CACHE_NAME = 'vyapaarsetu-v2';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/manifest.webmanifest',
  '/images/icon-192.svg',
  '/images/icon-512.svg',
];

// Install: Cache core application shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches
      .open(CACHE_NAME)
      .then((cache) => cache.addAll(STATIC_ASSETS))
      .then(() => self.skipWaiting())
      .catch((err) => {
        console.warn('Service worker pre-caching encountered an error:', err);
      })
  );
});

// Activate: Purge old cache versions and claim clients
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) => {
        return Promise.all(
          keys.filter((key) => key !== CACHE_NAME).map((key) => caches.delete(key))
        );
      })
      .then(() => self.clients.claim())
  );
});

// Fetch: Network-first for APIs, Cache-first for static assets, fallback to index.html for navigation
self.addEventListener('fetch', (event) => {
  const { request } = event;

  // Ignore non-HTTP/HTTPS requests (e.g., chrome-extension://, data:, blob:)
  if (!request.url.startsWith('http')) {
    return;
  }

  const url = new URL(request.url);

  // 1. API Requests: Network-first with graceful offline 503 JSON fallback
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(request).catch(() => {
        return new Response(
          JSON.stringify({
            error: 'Offline',
            message: 'You are currently offline. Orders are queued locally.',
          }),
          { status: 503, headers: { 'Content-Type': 'application/json' } }
        );
      })
    );
    return;
  }

  // 2. Navigation Requests: Network-first for SPA routes with cached index.html fallback
  if (request.mode === 'navigate') {
    event.respondWith(
      fetch(request)
        .then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            const responseClone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => {
              cache.put('/index.html', responseClone).catch(() => {});
            });
          }
          return networkResponse;
        })
        .catch(async () => {
          const cachedIndex = (await caches.match('/index.html')) || (await caches.match('/'));
          if (cachedIndex) {
            return cachedIndex;
          }
          return new Response(
            '<!DOCTYPE html><html><body style="font-family:sans-serif;text-align:center;padding:40px;">' +
            '<h2>VyapaarSetu is currently offline</h2><p>Please check your internet connection.</p>' +
            '</body></html>',
            { status: 503, headers: { 'Content-Type': 'text/html' } }
          );
        })
    );
    return;
  }

  // 3. For non-GET requests (e.g. form uploads, mutations), pass straight through to network
  if (request.method !== 'GET') {
    return;
  }

  // 4. Static Assets: Cache-first, fallback to network with resilient error catching
  event.respondWith(
    caches.match(request).then(async (cachedResponse) => {
      if (cachedResponse) {
        return cachedResponse;
      }

      try {
        const networkResponse = await fetch(request);
        if (
          networkResponse &&
          networkResponse.status === 200 &&
          (networkResponse.type === 'basic' || networkResponse.type === 'cors')
        ) {
          const responseToCache = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => {
            cache.put(request, responseToCache).catch(() => {});
          });
        }
        return networkResponse;
      } catch (fetchErr) {
        // If network failed and asset is not cached, return fallback image if applicable
        if (request.destination === 'image') {
          const fallbackIcon = await caches.match('/images/icon-192.svg');
          if (fallbackIcon) {
            return fallbackIcon;
          }
        }
        // Return 503 response instead of unhandled rejection
        return new Response('Asset unavailable offline', {
          status: 503,
          statusText: 'Service Unavailable',
          headers: { 'Content-Type': 'text/plain' },
        });
      }
    })
  );
});
