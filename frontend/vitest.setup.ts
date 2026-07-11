import "@testing-library/jest-dom/vitest";

// Node's own built-in `localStorage` global (not jsdom's) shadows jsdom's
// implementation in this environment and is non-functional without a
// `--localstorage-file` flag (e.g. `.clear()` is missing) — replace it with
// a plain in-memory Storage so components that use window.localStorage are
// testable regardless of the Node runtime's experimental global.
class MemoryStorage implements Storage {
  private store = new Map<string, string>();

  get length() {
    return this.store.size;
  }

  clear() {
    this.store.clear();
  }

  getItem(key: string) {
    return this.store.has(key) ? this.store.get(key)! : null;
  }

  key(index: number) {
    return Array.from(this.store.keys())[index] ?? null;
  }

  removeItem(key: string) {
    this.store.delete(key);
  }

  setItem(key: string, value: string) {
    this.store.set(key, String(value));
  }
}

Object.defineProperty(window, "localStorage", {
  value: new MemoryStorage(),
  writable: true,
});
