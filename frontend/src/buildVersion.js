/* eslint-disable no-restricted-globals */
export const BUILD_VERSION = 'mosaic-v20251111';
export const __BUILD_VERSION__ = BUILD_VERSION;
const globalScope = typeof self !== 'undefined' ? self : typeof window !== 'undefined' ? window : null;
if (globalScope) {
  globalScope.__BUILD_VERSION__ = BUILD_VERSION;
}
