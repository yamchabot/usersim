/**
 * ScenarioRunner
 *
 * Handles browser lifecycle, scenario dispatch, and usersim.metrics.v1 output.
 * You write the scenario logic; this handles everything else.
 *
 * Usage:
 *   import { createRunner } from 'usersim-web';
 *
 *   const runner = createRunner({ url: 'http://localhost:8000' });
 *
 *   runner.scenario('baseline', async ({ page }) => {
 *     await page.click('#add-habit');
 *     const count = await page.evaluate(() => document.querySelectorAll('.habit').length);
 *     return { habit_count: count };
 *   });
 *
 *   runner.run();
 */

export class ScenarioRunner {
  constructor({ url, scenario, backend = 'auto' } = {}) {
    this._url      = url;
    this._scenario = scenario ?? process.env.USERSIM_SCENARIO ?? process.argv[2];
    this._backend  = backend;
    this._scenarios    = new Map();
    this._initScripts  = [];
  }

  /**
   * Register a scenario by name.
   * The handler receives { page, reload } and must return a plain metrics object.
   * reload() navigates to a fresh page instance preserving storage state,
   * and returns the new page.
   */
  scenario(name, fn) {
    this._scenarios.set(name, fn);
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
   * Run the active scenario (from USERSIM_SCENARIO env var, argv[2], or constructor).
   * Writes usersim.metrics.v1 JSON to stdout on success.
   * Writes errors to stderr and exits 1 on failure.
   */
  async run() {
    const name = this._scenario;

    if (!name) {
      process.stderr.write('usersim-web: no scenario specified\n');
      process.stderr.write('  set USERSIM_SCENARIO or pass as first argument\n');
      process.exit(1);
    }

    const fn = this._scenarios.get(name);
    if (!fn) {
      process.stderr.write(`usersim-web: unknown scenario "${name}"\n`);
      process.stderr.write(`  registered: ${[...this._scenarios.keys()].join(', ')}\n`);
      process.exit(1);
    }

    const backend = await this._resolveBackend();
    try {
      const ctx     = await backend.newContext(this._url, this._initScripts);
      const metrics = await fn(ctx);
      process.stdout.write(JSON.stringify({
        schema:   'usersim.metrics.v1',
        scenario: name,
        metrics:  metrics ?? {},
      }, null, 2));
      process.stdout.write('\n');
    } catch (err) {
      process.stderr.write(`usersim-web: scenario "${name}" threw:\n  ${err.message}\n`);
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

export function createRunner(opts) {
  return new ScenarioRunner(opts);
}

async function canImport(name) {
  try { await import(name); return true; } catch { return false; }
}
