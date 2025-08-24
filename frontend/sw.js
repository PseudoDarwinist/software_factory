// Simple service worker for Mission Control
self.addEventListener('install', (event) => {
  console.log('Service worker installed');
});

self.addEventListener('activate', (event) => {
  console.log('Service worker activated');
});

self.addEventListener('fetch', (event) => {
  // Bypass SW for API and websockets to avoid network errors during streaming and socket.io
  const url = new URL(event.request.url)
  const isApi = url.pathname.startsWith('/api/')
  const isSocket = url.pathname.startsWith('/socket.io/') || url.protocol === 'ws:' || url.protocol === 'wss:'
  if (isApi || isSocket) {
    return
  }
  // Pass through other requests
  event.respondWith(fetch(event.request))
});