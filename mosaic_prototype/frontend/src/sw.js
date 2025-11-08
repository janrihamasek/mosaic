/* eslint-disable no-restricted-globals */
import { clientsClaim } from "workbox-core";
import { precacheAndRoute, cleanupOutdatedCaches, createHandlerBoundToURL } from "workbox-precaching";
import { registerRoute, NavigationRoute } from "workbox-routing";
import { CacheFirst, NetworkFirst, StaleWhileRevalidate } from "workbox-strategies";
import { ExpirationPlugin } from "workbox-expiration";

self.__WB_DISABLE_DEV_LOGS = true;
clientsClaim();
self.skipWaiting();

precacheAndRoute(self.__WB_MANIFEST || []);
cleanupOutdatedCaches();

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
    cacheName: "mosaic-static-v1",
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
    cacheName: "mosaic-images-v1",
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
    cacheName: "mosaic-api-v1",
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
