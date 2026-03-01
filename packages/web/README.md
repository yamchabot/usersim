# usersim-web

Browser instrumentation helpers for [usersim](https://github.com/yamchabot/usersim).

Handles browser lifecycle, path dispatch, and `usersim.metrics.v1` output.
You write the path logic and data extraction — this handles everything else.

---

## Installation

```bash
npm install usersim-web

# Real browser (preferred):
npm install playwright
npx playwright install chromium

# Or headless DOM (no display required):
npm install jsdom
```

The backend is selected automatically based on what's installed. Playwright is preferred.
Force a specific backend with the `backend` option.

---

## Usage

```js
// collect.js
import { createCollector } from 'usersim-web';

const runner = createCollector({
  url:      'http://localhost:8000',
  path: process.env.USERSIM_PATH,  // set by usersim runner automatically
  // backend: 'playwright',               // or 'jsdom' — default: auto
});

collector.path('baseline', async ({ page }) => {
  await page.click('#add-habit');
  await page.fill('#habit-name', 'Exercise');
  await page.click('#save');

  const habitCount = await page.evaluate(() =>
    document.querySelectorAll('.habit-card').length
  );
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('habits') || '[]').length
  );

  return {
    habit_count:       habitCount,
    habits_in_storage: stored,
  };
});

collector.path('persistence', async ({ page, reload }) => {
  await page.click('#add-habit');
  await page.fill('#habit-name', 'Exercise');
  await page.click('#save');

  const before = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('habits') || '[]').length
  );

  // reload() returns a fresh page with the same localStorage state
  const page2  = await reload();

  const after  = await page2.evaluate(() =>
    JSON.parse(localStorage.getItem('habits') || '[]').length
  );

  return {
    habits_before_reload: before,
    habits_after_reload:  after,
    reload_loss_count:    before - after,
  };
});

runner.run();
```

Run a specific path:
```bash
USERSIM_PATH=baseline node collect.js
USERSIM_PATH=persistence node collect.js
```

Output (written to stdout):
```json
{
  "schema":   "usersim.metrics.v1",
  "path": "baseline",
  "metrics": {
    "habit_count": 1,
    "habits_in_storage": 1
  }
}
```

---

## Injecting monitoring hooks

Use `runner.inject(code)` to run JavaScript before the application code on every page load,
including after `reload()`. Write whatever monitoring logic your path needs.

```js
runner.inject(`
  window.__monitor = { fetchCount: 0, storageWrites: 0 };

  const _fetch = window.fetch;
  window.fetch = (...args) => {
    window.__monitor.fetchCount++;
    return _fetch(...args);
  };

  const _setItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function(k, v) {
    window.__monitor.storageWrites++;
    return _setItem.call(this, k, v);
  };
`);

collector.path('baseline', async ({ page }) => {
  // ... actions ...

  const mon = await page.evaluate(() => window.__monitor);
  return {
    fetch_call_count:  mon.fetchCount,
    storage_write_count: mon.storageWrites,
  };
});
```

---

## API

### `createCollector(options)` → `ScenarioRunner`

| Option     | Type     | Default  | Description                              |
|------------|----------|----------|------------------------------------------|
| `url`      | `string` | required | URL to navigate to                       |
| `path` | `string` | env/argv | Scenario name (overrides auto-detection) |
| `backend`  | `string` | `'auto'` | `'playwright'`, `'jsdom'`, or `'auto'`   |

### `collector.path(name, fn)` → `runner`

Register a path. `fn` receives `{ page, reload }`:
- **`page`** — Playwright `Page` object (or jsdom wrapper, see below)
- **`reload()`** — returns a new `page` with the same storage state

### `runner.inject(code)` → `runner`

Inject a JavaScript string to execute before the app on every page load.
Called before `collector.path()` or after — order doesn't matter.

### `runner.run()`

Dispatch the active path and write `usersim.metrics.v1` JSON to stdout.

---

## jsdom page API

When using the jsdom backend, `page` is a wrapper that implements a subset of
the Playwright Page API. The same path code works on both backends for
common operations:

| Method                             | Description                              |
|------------------------------------|------------------------------------------|
| `page.click(selector)`             | Click the first matching element         |
| `page.fill(selector, value)`       | Set value, fire input + change events    |
| `page.type(selector, value)`       | Alias for fill                           |
| `page.evaluate(fn)`                | Call fn with window as argument          |
| `page.$(selector)`                 | querySelector (returns element or null)  |
| `page.$$(selector)`                | querySelectorAll (returns Array)         |
| `page.waitForSelector(sel, opts?)` | Poll until selector appears              |

For anything not in this list, use `page.evaluate()` to access the DOM directly.

---

## Choosing a backend

| | Playwright | jsdom |
|---|---|---|
| Real browser engine | ✅ | ❌ |
| CSS layout | ✅ | ❌ |
| Needs display | No (headless) | No |
| Works in CI | ✅ | ✅ |
| Works in Docker | ✅ (with deps) | ✅ |
| API surface | Full Playwright | Subset (see above) |
| Setup | `npm i playwright && npx playwright install chromium` | `npm i jsdom` |

Use Playwright when your path depends on real rendering or browser APIs.
Use jsdom when you're in a constrained environment and your app doesn't need layout.
