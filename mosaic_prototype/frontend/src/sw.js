/* eslint-disable no-restricted-globals */
import { clientsClaim } from "workbox-core";
import { precacheAndRoute, createHandlerBoundToURL } from "workbox-precaching";
import { registerRoute, NavigationRoute } from "workbox-routing";
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";

import { BUILD_VERSION } from "./buildVersion";

self.__WB_DISABLE_DEV_LOGS = true;
clientsClaim();
self.skipWaiting();

const CACHE_VERSION = (self.__BUILD_VERSION__ || BUILD_VERSION || "mosaic-v0").toString();
const CACHE_NAME = `${CACHE_VERSION}-cache`;
const STATIC_CACHE = `mosaic-static-${CACHE_VERSION}`;
const IMAGE_CACHE = `mosaic-images-${CACHE_VERSION}`;
const API_CACHE = `mosaic-api-${CACHE_VERSION}`;
const ALLOWED_CACHES = new Set([CACHE_NAME, STATIC_CACHE, IMAGE_CACHE, API_CACHE]);

precacheAndRoute(self.__WB_MANIFEST || [], {
  cacheName: CACHE_NAME,
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys().then((names) =>
      Promise.all(
        names.map((cacheName) => {
          if (ALLOWED_CACHES.has(cacheName)) {
            return Promise.resolve(true);
          }
          return caches.delete(cacheName);
        })
      )
    )
  );
});

const appShellHandler = createHandlerBoundToURL(`${process.env.PUBLIC_URL || ""}/index.html`);
const navigationRoute = new NavigationRoute(appShellHandler, {
  denylist: [/^\/api\//i, /\/__\/webpack\//],
});
registerRoute(navigationRoute);

const staticAssetMatch = ({ request }) =>
  ["style", "script", "font"].includes(request.destination) ||
  (request.destination === "" && /\.(?:js|css)$/.test(new URL(request.url).pathname));

registerRoute(
  staticAssetMatch,
  new CacheFirst({
    cacheName: STATIC_CACHE,
    matchOptions: {
      ignoreSearch: true,
    },
    plugins: [
      new ExpirationPlugin({
        maxEntries: 60,
        purgeOnQuotaError: true,
      }),
    ],
  })
);

const imageMatch = ({ request }) => request.destination === "image";

registerRoute(
  imageMatch,
  new StaleWhileRevalidate({
    cacheName: IMAGE_CACHE,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 60,
        maxAgeSeconds: 60 * 60 * 24 * 7,
        purgeOnQuotaError: true,
      }),
    ],
  })
);

const normalizeBase = (value) => (value ? value.replace(/\/+$/, "") : null);
const configuredApiBase = normalizeBase(process.env.REACT_APP_API_BASE_URL);
const sameOriginApiMatch = ({ url, request }) => {
  if (request.method !== "GET") {
    return false;
  }
  if (configuredApiBase) {
    return url.href.startsWith(configuredApiBase);
  }
  const isSameOrigin = url.origin === self.location.origin;
  return isSameOrigin && url.pathname.startsWith("/api");
};

registerRoute(
  sameOriginApiMatch,
  new NetworkFirst({
    cacheName: API_CACHE,
    networkTimeoutSeconds: 5,
    plugins: [
      new ExpirationPlugin({
        maxEntries: 100,
        maxAgeSeconds: 60 * 30,
        purgeOnQuotaError: true,
      }),
    ],
    fetchOptions: {
      credentials: "include",
    },
  })
);
