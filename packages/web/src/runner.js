/**
 * Collector
 *
 * Handles browser lifecycle, path dispatch, and usersim.metrics.v1 output.
 * You write the collection logic; this handles everything else.
 *
 * Usage:
 *   import { createCollector } from 'usersim-web';
 *
 *   const collector = createCollector({ url: 'http://localhost:8000' });
 *
 *   collector.path('baseline', async ({ page }) => {
 *     await page.click('#add-habit');
 *     const count = await page.evaluate(() => document.querySelectorAll('.habit').length);
 *     return { habit_count: count };
 *   });
 *
 *   collector.collect();
 */

export class Collector {
  constructor({ url, path, backend = 'auto' } = {}) {
    this._url      = url;
    this._path     = path ?? process.env.USERSIM_PATH ?? process.argv[2];
    this._backend  = backend;
    this._paths       = new Map();
    this._initScripts = [];
  }

  /**
   * Register a path by name.
   * The handler receives { page, reload } and must return a plain metrics object.
   * reload() navigates to a fresh page instance preserving storage state,
   * and returns the new page.
   */
  path(name, fn) {
    this._paths.set(name, fn);
    return this;
  }

  /**
   * Inject JavaScript that runs before the application code on every page load
   * (including after reload()). Use this for monitoring hooks.
   *
   * Playwright: injected via context.addInitScript()
   * jsdom:      evaluated in window scope via beforeParse hook
   */
  inject(code) {
    this._initScripts.push(code);
    return this;
  }

  /**
   * Run the active path (from USERSIM_PATH env var, argv[2], or constructor).
   * Writes usersim.metrics.v1 JSON to stdout on success.
   * Writes errors to stderr and exits 1 on failure.
   */
  async collect() {
    const name = this._path;

    if (!name) {
      process.stderr.write('usersim-web: no path specified\n');
      process.stderr.write('  set USERSIM_PATH or pass as first argument\n');
      process.exit(1);
    }

    const fn = this._paths.get(name);
    if (!fn) {
      process.stderr.write(`usersim-web: unknown path "${name}"\n`);
      process.stderr.write(`  registered: ${[...this._paths.keys()].join(', ')}\n`);
      process.exit(1);
    }

    const backend = await this._resolveBackend();
    try {
      const ctx     = await backend.newContext(this._url, this._initScripts);
      const metrics = await fn(ctx);
      process.stdout.write(JSON.stringify({
        schema:  'usersim.metrics.v1',
        path:    name,
        metrics: metrics ?? {},
      }, null, 2));
      process.stdout.write('\n');
    } catch (err) {
      process.stderr.write(`usersim-web: path "${name}" threw:\n  ${err.message}\n`);
      if (err.stack) process.stderr.write(err.stack + '\n');
      process.exit(1);
    } finally {
      await backend.close().catch(() => {});
    }
  }

  async _resolveBackend() {
    const b = this._backend;
    if (b === 'playwright' || (b === 'auto' && await canImport('playwright'))) {
      const { PlaywrightBackend } = await import('./backends/playwright.js');
      return new PlaywrightBackend();
    }
    if (b === 'jsdom' || (b === 'auto' && await canImport('jsdom'))) {
      const { JsdomBackend } = await import('./backends/jsdom.js');
      return new JsdomBackend();
    }
    throw new Error(
      'usersim-web: no browser backend available.\n' +
      '  Install playwright:  npm install playwright && npx playwright install chromium\n' +
      '  Or jsdom:            npm install jsdom'
    );
  }
}

export function createCollector(opts) {
  return new Collector(opts);
}

// Keep createRunner as a deprecated alias
export function createRunner(opts) {
  return new Collector(opts);
}

async function canImport(name) {
  try { await import(name); return true; } catch { return false; }
}
