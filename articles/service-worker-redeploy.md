# Why Your Service Worker is Breaking on Redeploy

**February 20, 2026 · 6 min read**

You push a fix. You deploy. You refresh the page. Nothing changed.

You hard-refresh. Clear the cache. Open an incognito window. The old version is *still there*. Worse — your API calls are throwing CORS errors that didn't exist five minutes ago.

The culprit? Your service worker is still alive, silently serving stale files from its cache.

## The Problem

Service workers are background scripts that intercept network requests. They're powerful — they enable offline support, push notifications, and instant page loads. But they come with a catch that bites almost every developer at least once:

**Service workers don't die when you deploy.**

Here's what happens:

1. User visits your site → browser installs `sw.js`
2. Service worker caches your HTML, CSS, JS, and API responses
3. You deploy a new version with bug fixes
4. User returns → the *old* service worker intercepts the request
5. Old service worker serves the *cached* version of your files
6. Your fix is invisible

The browser *does* check for an updated `sw.js` on each visit, but the new service worker enters a **"waiting"** state. It won't activate until every tab running the old version is closed. Not refreshed — *closed*.

## When It Gets Worse: CORS and API Caching

The real pain starts when your service worker caches API responses. I hit this building [LootRadar](https://thelootradar.com) — a game deals aggregator that pulls from the CheapShark API.

My service worker was using a "cache-first" strategy:

```javascript
self.addEventListener('fetch', (event) => {
  event.respondWith(
    caches.match(event.request).then((cached) => {
      return cached || fetch(event.request);
    })
  );
});
```

This cached *everything* — including API responses from a different origin. When I switched from direct API calls to a CORS proxy, the service worker kept serving the old cached responses (with the old CORS headers). The result: a wall of CORS errors in the console, but only for returning visitors.

New visitors? Site worked perfectly. Returning visitors? Completely broken. The worst kind of bug — it's invisible to you but visible to your users.

## The Fix

### 1. The Nuclear Option: Unregister Everything

If you've already shipped a broken service worker, you need to clean up. Add this to your main page's JavaScript:

```javascript
// Unregister all service workers and clear caches
if ('serviceWorker' in navigator) {
  navigator.serviceWorker.getRegistrations().then((registrations) => {
    registrations.forEach((registration) => {
      registration.unregister();
    });
  });

  // Also clear the caches they left behind
  caches.keys().then((names) => {
    names.forEach((name) => caches.delete(name));
  });
}
```

Ship this in your HTML, *not* in the service worker itself. The service worker is the problem — you can't trust it to fix itself.

### 2. Skip Waiting (If You Want to Keep the Service Worker)

If you actually need a service worker (for offline support, PWA requirements, etc.), make new versions activate immediately:

```javascript
// In sw.js
self.addEventListener('install', (event) => {
  self.skipWaiting(); // Don't wait for old tabs to close
});

self.addEventListener('activate', (event) => {
  // Delete old caches
  event.waitUntil(
    caches.keys().then((names) => {
      return Promise.all(
        names.filter((name) => name !== CURRENT_CACHE)
             .map((name) => caches.delete(name))
      );
    })
  );
  // Take control of all open tabs immediately
  clients.claim();
});
```

`skipWaiting()` + `clients.claim()` = new service worker takes over immediately on deploy.

### 3. Version Your Cache

Never use a static cache name. Include a version or hash:

```javascript
const CURRENT_CACHE = 'v3'; // Bump on every deploy

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CURRENT_CACHE).then((cache) => {
      return cache.addAll(['/index.html', '/style.css', '/app.js']);
    })
  );
  self.skipWaiting();
});
```

When the cache name changes, the old cache becomes orphaned and gets cleaned up in the `activate` handler.

## Gotchas

**Don't cache API responses with cache-first.** Use "network-first" for anything dynamic:

```javascript
// Network-first: try the network, fall back to cache
event.respondWith(
  fetch(event.request)
    .then((response) => {
      const clone = response.clone();
      caches.open(CURRENT_CACHE).then((cache) => cache.put(event.request, clone));
      return response;
    })
    .catch(() => caches.match(event.request))
);
```

**`update on reload` only works in DevTools.** Chrome's "Update on reload" checkbox in the Application tab is a development convenience. Your users don't have it checked.

**`Clear-Site-Data` header.** If you have server control, you can send `Clear-Site-Data: "storage"` as a one-time response header to wipe everything. Nuclear, but effective.

**GitHub Pages doesn't let you set response headers.** If you're on a static host without header control, the unregister script in your HTML is your only option.

## Takeaway

Service workers are a one-way door. Once a user's browser installs one, it persists across deploys, across sessions, across everything — until it's explicitly replaced or unregistered.

Before you add a service worker, ask: **do I actually need offline support?** If the answer is "not really, I just thought it was cool" — skip it. The caching headaches aren't worth it for a site that requires an internet connection anyway.

If you do need one: version your caches, use `skipWaiting()`, never cache API responses with cache-first, and always have an unregister escape hatch ready.

The best service worker bug is the one you never ship.
