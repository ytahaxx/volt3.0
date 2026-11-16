/* Volt Explorer — service worker.
   - Fichiers statiques : cache d'abord (rapide, disponible hors ligne).
   - Pages HTML : réseau d'abord, repli sur la dernière version vue si hors ligne.
   - API (/api/*) : toujours le réseau (l'assistant et la recherche ont besoin du serveur). */
const VERSION = "v2";
const STATIC_CACHE = "ve-static-" + VERSION;
const PAGES_CACHE = "ve-pages-" + VERSION;
const PRECACHE = [
  "/static/css/style.css", "/static/js/app.js", "/static/js/search.js",
  "/static/js/quiz.js", "/static/js/assistant.js",
  "/static/images/icon-192.png", "/static/images/icon-512.png"
];

self.addEventListener("install", function (event) {
  event.waitUntil(caches.open(STATIC_CACHE).then(function (c) { return c.addAll(PRECACHE); }));
  self.skipWaiting();
});

self.addEventListener("activate", function (event) {
  event.waitUntil(
    caches.keys().then(function (keys) {
      return Promise.all(keys.filter(function (k) {
        return k !== STATIC_CACHE && k !== PAGES_CACHE;
      }).map(function (k) { return caches.delete(k); }));
    }).then(function () { return self.clients.claim(); })
  );
});

self.addEventListener("fetch", function (event) {
  var req = event.request;
  if (req.method !== "GET") return;
  var url = new URL(req.url);
  if (url.origin !== location.origin || url.pathname.startsWith("/api/")) return; // réseau direct

  if (url.pathname.startsWith("/static/")) {
    event.respondWith(
      caches.match(req).then(function (hit) {
        return hit || fetch(req).then(function (res) {
          var copy = res.clone();
          caches.open(STATIC_CACHE).then(function (c) { c.put(req, copy); });
          return res;
        });
      })
    );
    return;
  }

  if (req.mode === "navigate") {
    event.respondWith(
      fetch(req).then(function (res) {
        if (res.ok) {
          var copy = res.clone();
          caches.open(PAGES_CACHE).then(function (c) { c.put(req, copy); });
        }
        return res;
      }).catch(function () {
        return caches.match(req).then(function (hit) {
          return hit || new Response(
            "<!doctype html><meta charset=utf-8><meta name=viewport content='width=device-width,initial-scale=1'>" +
            "<body style='font-family:system-ui;padding:2rem'><h1>Hors ligne</h1>" +
            "<p>Cette page n'a pas encore été visitée. Reconnectez-vous puis réessayez.</p></body>",
            { status: 503, headers: { "Content-Type": "text/html; charset=utf-8" } });
        });
      })
    );
  }
});
