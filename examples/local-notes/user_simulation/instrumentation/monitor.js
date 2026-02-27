/**
 * monitor.js — Pre-init monitoring hooks
 *
 * This script must run BEFORE the app's own code initialises.
 * In Playwright: page.addInitScript({ path: 'monitor.js' })
 * In jsdom: passed to beforeParse(window)
 *
 * It patches browser globals to record events without modifying the app.
 */

(function installMonitor(window) {
  window.__monitor = {
    requests: [],
    storageWrites: [],
    storageErrors: 0,
    interactions: 0,
    startTime: Date.now(),
  };

  // ── Network interception ─────────────────────────────────────────────────
  // Override fetch
  window.fetch = function (url, opts) {
    window.__monitor.requests.push({ url: String(url), method: opts?.method || 'GET', ts: Date.now() });
    // Reject — no real network in instrumentation runs
    return Promise.reject(new Error(`[monitor] blocked fetch: ${url}`));
  };

  // Override XMLHttpRequest
  window.XMLHttpRequest = class MockXHR {
    open(method, url) {
      window.__monitor.requests.push({ url: String(url), method, ts: Date.now() });
    }
    send() {}
    setRequestHeader() {}
    addEventListener() {}
  };

  // ── localStorage interception ────────────────────────────────────────────
  const _setItem = window.localStorage.setItem.bind(window.localStorage);
  const _getItem = window.localStorage.getItem.bind(window.localStorage);

  window.localStorage.setItem = function (key, value) {
    window.__monitor.storageWrites.push({ key, ts: Date.now() });
    try {
      return _setItem(key, value);
    } catch (e) {
      window.__monitor.storageErrors++;
      throw e;
    }
  };

  window.localStorage.getItem = function (key) {
    try {
      return _getItem(key);
    } catch (e) {
      window.__monitor.storageErrors++;
      throw e;
    }
  };

  // ── Interaction counting ─────────────────────────────────────────────────
  // Counts clicks and keypresses — used to measure capture path length
  window.addEventListener('click',   () => window.__monitor.interactions++, true);
  window.addEventListener('keydown', () => window.__monitor.interactions++, true);

}(window));
