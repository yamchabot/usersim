/**
 * Playwright backend — real browser (Chromium by default).
 *
 * page is the raw Playwright Page object.
 * reload() closes the current page, opens a fresh one in the same browser context
 * (so cookies and localStorage are preserved), and returns the new page.
 */
export class PlaywrightBackend {
  async newContext(url, initScripts = []) {
    const { chromium } = await import('playwright');
    this._browser  = await chromium.launch({ headless: true });
    this._context  = await this._browser.newContext();

    for (const code of initScripts) {
      await this._context.addInitScript(code);
    }

    const page = await this._openPage(url);

    return {
      page,
      reload: async () => {
        await page.close();
        return this._openPage(url);
      },
    };
  }

  async _openPage(url) {
    const page = await this._context.newPage();
    await page.goto(url, { waitUntil: 'domcontentloaded' });
    return page;
  }

  async close() {
    await this._browser?.close();
  }
}
