//service-worker.js
const CACHE_NAME = 'photo-journal-cache-v1';
const urlsToCache = [
    '/',
    '/static/style.css',
    '/static/uploads/',
    '/register',
    '/login',
    '/offline',
    '/static/icons/icon-192x192.png',
    '/static/icons/icon-512x512.png',
    '/static/icons/icon-delete-64x64.png',
    '/static/icons/icon-edit-64x64.png',
    '/static/icons/favicon.png',
    '/manifest.json'
  ]
  

// Helper function for debugging
const debug = (message) => {
  console.log(`[ServiceWorker] ${message}`);
};

// Install event handler
self.addEventListener('install', event => {
  debug('Installing Service Worker');
  event.waitUntil(
    caches.open(CACHE_NAME)
      .then(cache => {
        debug('caching offline page and other resources');
        // First cache the offline page
        return cache.add('/offline')
          .then(() => {
            debug('Offline page cached successfully');
            return cache.addAll(urlsToCache);
          })
          .then(() => {
            debug('All resources cached successfully');
          });
      })
      .then(() => {
        debug('skipping waiting - taking control immediately');
        return self.skipWaiting();
      })
      .catch(error => {
        console.error('[ServiceWorker] Install error:', error);
      })
  );
});

// Activate event handler
self.addEventListener('activate', event => {
  debug('Activating Service Worker');
  event.waitUntil(
    Promise.all([
      caches.keys().then(cacheNames => {
        debug('Cleaning old caches');
        return Promise.all(
          cacheNames
            .filter(cacheName => cacheName !== CACHE_NAME)
            .map(cacheName => {
              debug(`Deleting old cache: ${cacheName}`);
              return caches.delete(cacheName);
            })
        );
      }),
      self.clients.claim()
    ]).then(() => {
      debug('Service Worker activated and controlling pages');
    })
  );
});

// Fetch event handler
self.addEventListener('fetch', event => {
  debug(`Fetch request for ${event.request.url}`);

  // Special handling for navigation requests
  if (event.request.mode === 'navigate') {
    debug('Handling navigation request');
    event.respondWith(
      fetch(event.request).catch(() => {
        debug('Network request failed, attempting to return offline page');
        return caches.open(CACHE_NAME).then(cache => {
          debug('Looking for offline page in cache');
          return cache.match('/offline').then(response => {
            if (response) {
              debug('Found offline page in cache, returning it');
              return response;
            }
            debug('Offline page not found in cache, returning basic offline message');
            return new Response(
              '<html><body><h1>Offline</h1><p>The offline page could not be loaded.</p></body></html>',
              { headers: { 'Content-Type': 'text/html' } }
            );
          });
        });
      })
    );
  }

  // For non-navigation requests, use network-first strategy
  else {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          debug(`Network request successful for: ${event.request.url}`);
          // Clone the response before caching
          const responseToCache = response.clone();

          // Only cache successful responses
          if (response.status === 200) {
            caches.open(CACHE_NAME)
              .then(cache => {
                cache.put(event.request, responseToCache);
                debug(`Cached response for: ${event.request.url}`);
              });
          }

          return response;
        })
        .catch(() => {
          debug(`Network request failed for: ${event.request.url}, checking cache`);
          return caches.match(event.request)
            .then(response => {
              if (response) {
                debug(`Found cached response for: ${event.request.url}`);
                return response;
              }
              debug(`No cached response found for: ${event.request.url}`);
              return new Response('', {
                status: 404,
                statusText: 'Not found'
              });
            });
        })
    );
  }
});
