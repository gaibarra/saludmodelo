// Offline artifact check: no server, database or application processes.
const { chromium } = require('../frontend/node_modules/playwright');
const { pathToFileURL } = require('node:url');
const path = require('node:path');
const assert = require('node:assert/strict');
(async () => {
  const browser = await chromium.launch({headless:true});
  try {
    const page = await browser.newPage();
    const network = [];
    const errors = [];
    page.on('request', request => { if (/^https?:/.test(request.url())) network.push(request.url()); });
    page.on('pageerror', error => errors.push(error.message));
    await page.goto(pathToFileURL(path.resolve(process.argv[2])).href);
    assert.equal(await page.locator('article').count(), 177);
    assert.equal(await page.locator('article h4').count(), 1770);
    await page.getByRole('link', {name:/C15 Expediente/}).click();
    await page.locator('article').last().locator('summary').click();
    assert.equal(await page.locator('article').last().locator('details').getAttribute('open'), '');
    for (const width of [1280, 375]) {
      await page.setViewportSize({width, height:900});
      assert(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `Desbordamiento a ${width}px`);
    }
    assert.deepEqual(network, []);
    assert.deepEqual(errors, []);
    console.log('177 fichas, 1770 apartados, navegación y referencias: correctos. Escritorio/móvil sin desbordamiento; sin peticiones HTTP ni errores.');
  } finally { await browser.close(); }
})().catch(error => { console.error(error); process.exitCode=1; });
