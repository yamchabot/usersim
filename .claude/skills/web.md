# usersim-web — Browser Instrumentation for Web Projects

Use this skill when the application under test runs in a browser.
Read `.claude/skills/SKILL.md` first — this skill covers Phase 4 (Instrumentation) only.

`usersim-web` is a Node.js package that handles browser lifecycle, scenario dispatch,
and `usersim.metrics.v1` output. You write the scenario logic and data extraction;
it handles everything else.

---

## Installation

```bash
cd user_simulation/instrumentation
npm init -y
npm install usersim-web

# Real browser (preferred):
npm install playwright
npx playwright install chromium

# Or headless DOM (no display, CI-friendly):
npm install jsdom
```

The backend is selected automatically based on what's installed.
Playwright is used if available; jsdom is the fallback.

---

## collect.js — scenario runner

Create `user_simulation/instrumentation/collect.js`:

```js
import { createRunner } from 'usersim-web';

const runner = createRunner({
  url:      'http://localhost:8000',   // your app's URL
  scenario: process.env.USERSIM_SCENARIO,
});

// Optional: inject monitoring hooks before the app loads
// runner.inject(`
//   window.__mon = { fetches: 0 };
//   const _f = fetch;
//   fetch = (...a) => { window.__mon.fetches++; return _f(...a); };
// `);

runner.scenario('baseline', async ({ page }) => {
  // Perform actions using the Playwright Page API (or jsdom subset)
  await page.click('#some-button');
  await page.fill('#some-input', 'hello');

  // Extract data — write your own querySelector/evaluate code
  const itemCount = await page.evaluate(() =>
    document.querySelectorAll('.item').length
  );
  const stored = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('items') || '[]').length
  );

  // Return a plain object — becomes the metrics doc
  return {
    item_count:       itemCount,
    items_in_storage: stored,
  };
});

runner.scenario('persistence', async ({ page, reload }) => {
  // seed state
  await page.click('#add-item');
  const before = await page.evaluate(() =>
    JSON.parse(localStorage.getItem('items') || '[]').length
  );

  // reload() returns a fresh page with the same localStorage state
  const page2 = await reload();

  const after = await page2.evaluate(() =>
    JSON.parse(localStorage.getItem('items') || '[]').length
  );

  return {
    items_before_reload: before,
    items_after_reload:  after,
    reload_loss_count:   before - after,
  };
});

runner.run();
```

---

## usersim.yaml instrumentation command

```yaml
instrumentation: node user_simulation/instrumentation/collect.js
```

If `node` is not on PATH in your environment, use the full path:

```yaml
instrumentation: /path/to/node user_simulation/instrumentation/collect.js
```

---

## Page API

The `page` object passed to each scenario handler is the raw Playwright `Page`
when using the Playwright backend. Refer to the Playwright documentation for
the full API: https://playwright.dev/docs/api/class-page

When using the jsdom backend, `page` is a wrapper that implements a compatible subset:

| Method                              | Description                             |
|-------------------------------------|-----------------------------------------|
| `page.click(selector)`              | Click first matching element            |
| `page.fill(selector, value)`        | Set value, fire input + change events   |
| `page.evaluate(fn)`                 | Call fn with window as argument         |
| `page.$(selector)`                  | querySelector                           |
| `page.$$(selector)`                 | querySelectorAll (returns Array)        |
| `page.waitForSelector(sel, opts?)`  | Poll until selector appears             |

For anything not in this list, use `page.evaluate()` to access the DOM directly.

---

## Injecting monitoring hooks

Use `runner.inject(code)` to run JavaScript before the app on every page load,
including after `reload()`. Useful for intercepting fetch, XHR, localStorage, etc.

```js
runner.inject(`
  window.__mon = { fetchCount: 0, storageWrites: 0 };

  const _fetch = window.fetch;
  window.fetch = (...args) => {
    window.__mon.fetchCount++;
    return _fetch(...args);
  };

  const _setItem = Storage.prototype.setItem;
  Storage.prototype.setItem = function(k, v) {
    window.__mon.storageWrites++;
    return _setItem.call(this, k, v);
  };
`);

runner.scenario('baseline', async ({ page }) => {
  // ... actions ...
  const mon = await page.evaluate(() => window.__mon);
  return {
    fetch_call_count:    mon.fetchCount,
    storage_write_count: mon.storageWrites,
  };
});
```

---

## Testing scenarios individually

```bash
USERSIM_SCENARIO=baseline node user_simulation/instrumentation/collect.js
USERSIM_SCENARIO=persistence node user_simulation/instrumentation/collect.js
```

Each should print valid `usersim.metrics.v1` JSON to stdout with no errors
before you run the full `usersim run`.
