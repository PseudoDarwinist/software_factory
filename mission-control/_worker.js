export default {
  async fetch(request, env, ctx) {
    const url = new URL(request.url);
    const backendOrigin = env.BACKEND_ORIGIN || 'https://your-backend.example.com';

    // Proxy API and Socket.IO to backend
    if (url.pathname.startsWith('/api') || url.pathname.startsWith('/socket.io')) {
      const targetUrl = new URL(url.pathname + url.search, backendOrigin);
      const proxyRequest = new Request(targetUrl.toString(), request);
      return fetch(proxyRequest);
    }

    // Serve static assets built by Vite (Pages binds ASSETS automatically)
    return env.ASSETS.fetch(request);
  }
}


