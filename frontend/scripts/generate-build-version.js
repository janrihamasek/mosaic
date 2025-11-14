const fs = require('fs');
const path = require('path');

(function generateBuildVersion() {
  const date = new Date();
  const pad = (value) => String(value).padStart(2, '0');
  const dateStamp = `${date.getFullYear()}${pad(date.getMonth() + 1)}${pad(date.getDate())}`;
  const version = `mosaic-v${dateStamp}`;
  const filePath = path.join(__dirname, '..', 'src', 'buildVersion.js');
  const fileContent = `/* eslint-disable no-restricted-globals */\nexport const BUILD_VERSION = '${version}';\nexport const __BUILD_VERSION__ = BUILD_VERSION;\nconst globalScope = typeof self !== 'undefined' ? self : typeof window !== 'undefined' ? window : null;\nif (globalScope) {\n  globalScope.__BUILD_VERSION__ = BUILD_VERSION;\n}\n`;

  fs.writeFileSync(filePath, fileContent);
})();
