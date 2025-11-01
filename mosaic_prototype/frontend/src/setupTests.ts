import '@testing-library/jest-dom';

const createStorage = () => {
  let store: Record<string, string> = {};
  return {
    getItem(key: string) {
      return Object.prototype.hasOwnProperty.call(store, key) ? store[key] : null;
    },
    setItem(key: string, value: string) {
      store[key] = String(value);
    },
    removeItem(key: string) {
      delete store[key];
    },
    clear() {
      store = {};
    },
  };
};

Object.defineProperty(window, 'localStorage', {
  value: createStorage(),
  writable: true,
});

Object.defineProperty(window, 'sessionStorage', {
  value: createStorage(),
  writable: true,
});
