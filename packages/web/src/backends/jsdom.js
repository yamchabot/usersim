/**
 * jsdom backend — no display required, good for CI and sandboxed environments.
 *
 * page exposes a subset of the Playwright Page API:
 *   page.click(selector)
 *   page.fill(selector, value)
 *   page.evaluate(fn)        — fn receives window as argument
 *   page.$(selector)         — returns first matching element
 *   page.$$(selector)        — returns all matching elements
 *   page.waitForSelector(selector, { timeout? })
 *
 * reload() serialises the current localStorage state, creates a new JSDOM
 * instance with that data pre-loaded, and returns the new page.
 *
 * Note: jsdom does not execute all browser APIs faithfully. For complex apps
 * that rely on layout, animations, or browser-specific APIs, use the
 * Playwright backend instead.
 */

export class JsdomBackend {
  constructor() {
    this._dom = null;
  }

  async newContext(url, initScripts = []) {
    const dom  = await this._createDom(url, {}, initScripts);
    this._dom  = dom;
    this._url  = url;
    this._initScripts = initScripts;

    return {
      page:   new JsdomPage(dom.window),
      reload: async () => {
        const storage = captureStorage(dom.window.localStorage);
        const newDom  = await this._createDom(url, storage, initScripts);
        this._dom     = newDom;
        return new JsdomPage(newDom.window);
      },
    };
  }

  async _createDom(url, initialStorage = {}, initScripts = []) {
    const { JSDOM } = await import('jsdom');

    const html = await fetchHtml(url);

    const dom = new JSDOM(html, {
      url,
      runScripts: 'dangerously',
      resources:  'usable',
      beforeParse(window) {
        // Seed localStorage from a previous session
        for (const [k, v] of Object.entries(initialStorage)) {
          window.localStorage.setItem(k, v);
        }
        // Run any injected monitoring scripts before the app code
        for (const code of initScripts) {
          try {
            // eslint-disable-next-line no-new-func
            const fn = new window.Function(code);
            fn.call(window);
          } catch (e) {
            process.stderr.write(`usersim-web (jsdom): init script error: ${e.message}\n`);
          }
        }
      },
    });

    // Allow scripts to settle
    await tick(50);
    return dom;
  }

  async close() {
    this._dom?.window.close();
  }
}

// ── JsdomPage — Playwright-compatible page API subset ────────────────────────

class JsdomPage {
  constructor(window) {
    this._window   = window;
    this._document = window.document;
  }

  async click(selector) {
    const el = this._require(selector);
    el.click();
    await tick();
  }

  async fill(selector, value) {
    const el = this._require(selector);
    el.value = value;
    el.dispatchEvent(new this._window.Event('input',  { bubbles: true }));
    el.dispatchEvent(new this._window.Event('change', { bubbles: true }));
    await tick();
  }

  /** Alias for fill — set a value and fire input events */
  async type(selector, value) {
    return this.fill(selector, value);
  }

  /**
   * Evaluate a function in the page's window context.
   * fn receives window as its first argument.
   *
   * Example:
   *   const count = await page.evaluate(w => w.document.querySelectorAll('.item').length);
   */
  async evaluate(fn) {
    return fn.call(this._window, this._window);
  }

  /** Returns the first element matching selector, or null */
  async $(selector) {
    return this._document.querySelector(selector);
  }

  /** Returns all elements matching selector as an Array */
  async $$(selector) {
    return [...this._document.querySelectorAll(selector)];
  }

  async waitForSelector(selector, { timeout = 5000 } = {}) {
    const deadline = Date.now() + timeout;
    while (Date.now() < deadline) {
      const el = this._document.querySelector(selector);
      if (el) return el;
      await tick(20);
    }
    throw new Error(`Timeout (${timeout}ms) waiting for: ${selector}`);
  }

  _require(selector) {
    const el = this._document.querySelector(selector);
    if (!el) throw new Error(`Element not found: ${selector}`);
    return el;
  }
}

// ── Helpers ───────────────────────────────────────────────────────────────────

function tick(ms = 10) {
  return new Promise(r => setTimeout(r, ms));
}

function captureStorage(localStorage) {
  const out = {};
  for (let i = 0; i < localStorage.length; i++) {
    const k = localStorage.key(i);
    out[k]  = localStorage.getItem(k);
  }
  return out;
}

async function fetchHtml(url) {
  if (url.startsWith('file://')) {
    const { readFileSync } = await import('fs');
    return readFileSync(url.slice('file://'.length), 'utf8');
  }
  const res = await fetch(url);
  if (!res.ok) throw new Error(`fetchHtml: ${res.status} ${res.statusText} — ${url}`);
  return res.text();
}
