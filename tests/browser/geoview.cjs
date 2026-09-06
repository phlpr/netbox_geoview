// Local end-to-end checks. Requires Playwright, seeded sites and an authenticated cookie file.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const { chromium } = require('playwright');

(async () => {
    const baseURL = process.env.GEOVIEW_BASE_URL || 'http://127.0.0.1:8001';
    const output = process.env.GEOVIEW_ARTIFACTS || '/tmp/geoview-browser-tests';
    const siteIds = process.env.GEOVIEW_SITE_IDS;
    assert(siteIds, 'Set GEOVIEW_SITE_IDS to the three seeded site IDs (comma-separated)');
    fs.mkdirSync(output, {recursive: true});
    const browser = await chromium.launch({headless: true});
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    await context.addCookies([JSON.parse(fs.readFileSync(process.env.GEOVIEW_COOKIE_FILE, 'utf8'))]);
    const page = await context.newPage();
    const errors = [];
    const results = [];
    page.on('pageerror', error => errors.push(error.message));
    const check = async (name, fn) => {
        try { const details = await fn(); results.push({name, passed: true, details}); }
        catch (error) { results.push({name, passed: false, error: error.message}); }
        console.log(JSON.stringify(results.at(-1)));
    };
    const siteQuery = siteIds.split(',').map(id => `site=${encodeURIComponent(id)}`).join('&');
    const openMap = async (query = siteQuery) => {
        const response = await page.goto(`${baseURL}/plugins/geoview/?${query}`, {waitUntil: 'networkidle'});
        assert.equal(response.status(), 200);
        assert.equal(new URL(page.url()).pathname, '/plugins/geoview/', 'Test session is missing or expired');
        const hide = page.getByText('Hide »', {exact: true});
        if (await hide.isVisible()) await hide.click();
        await page.locator('[data-geoview-rendered="1"]').waitFor();
    };
    const marker = async name => {
        const names = await page.locator('#geoview-map-config').evaluate(el => JSON.parse(el.textContent).site_markers.map(m => m.name));
        assert(names.includes(name), `Missing marker ${name}`);
        await page.locator('.leaflet-marker-icon').nth(names.indexOf(name)).click();
        await page.waitForFunction(() => document.querySelectorAll('.leaflet-popup').length === 1);
        await page.locator('.leaflet-popup').waitFor();
        await page.waitForFunction(() => getComputedStyle(document.querySelector('.leaflet-popup')).opacity === '1');
    };
    await check('Map, assets and three site markers', async () => {
        await openMap();
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 3);
        assert(await page.locator('.leaflet-tile-loaded').count() > 0);
        assert.equal(await page.locator('[data-geoview-static-warning]').isVisible(), false);
    });
    await check('Filter tab and dynamic search', async () => {
        await page.locator('#filter-tab').click();
        await page.locator('#id_q').fill('geoview');
        const form = page.locator('#filter-panel form');
        await Promise.all([page.waitForURL('**/plugins/geoview/**'), form.locator('button[type="submit"]').click()]);
        await page.locator('[data-geoview-rendered="1"]').waitFor();
        // The user's local database can contain additional matching devices.
        assert(await page.locator('.leaflet-marker-icon').count() >= 9);
    });
    for (const theme of ['light', 'dark']) {
        await check(`${theme} device popup and custom fields`, async () => {
            await openMap('q=gv-vie-core-01');
            if (await page.locator('html').getAttribute('data-bs-theme') !== theme) {
                await page.locator('.color-mode-toggle:visible').click();
            }
            assert.equal(await page.locator('html').getAttribute('data-bs-theme'), theme);
            await marker('gv-vie-core-01');
            assert((await page.locator('.geoview-popup').innerText()).includes('geoview_mapping'));
            const colors = await page.locator('.leaflet-popup-content-wrapper').evaluate(el => {
                const css = getComputedStyle(el);
                const probe = document.createElement('div');
                probe.style.backgroundColor = 'var(--tblr-bg-surface)';
                document.body.append(probe);
                const expected = getComputedStyle(probe).backgroundColor;
                probe.remove();
                return {background: css.backgroundColor, text: css.color, expected};
            });
            assert.equal(colors.background, colors.expected);
            assert.notEqual(colors.background, colors.text);
            await page.screenshot({path: path.join(output, `popup-${theme}.png`), fullPage: true});
            return colors;
        });
    }
    await check('Start, destination and direct distance', async () => {
        await openMap();
        await marker('GeoView Vienna DC');
        await page.locator('[data-route-point="start"]').click();
        await marker('GeoView Linz Hub');
        await page.locator('[data-route-point="end"]').click();
        await page.locator('[data-route-distance]').click();
        const measurement = await page.locator('[data-measure-summary]').innerText();
        assert.match(measurement, /155\s*km/);
        return measurement;
    });
    await check('Live Valhalla route through the NetBox proxy', async () => {
        const [response] = await Promise.all([
            page.waitForResponse(r => r.url().includes('/geoview/route/')),
            page.locator('[data-route-open]').click(),
        ]);
        const data = await response.json();
        assert.equal(response.status(), 200, JSON.stringify(data));
        assert.equal(data.success, true);
        assert(data.route.distance > 150 && data.route.distance < 300);
        assert(data.route.geometry.length > 100);
        await page.screenshot({path: path.join(output, 'route-dark.png'), fullPage: true});
        return {distance: data.route.distance, duration_minutes: data.route.duration_minutes, points: data.route.geometry.length};
    });
    await check('Collapse, expand and clear route panel', async () => {
        await page.locator('[data-route-toggle]').click();
        await page.locator('[data-route-toggle]').click();
        await page.locator('[data-route-clear]').click();
        assert.equal(await page.locator('[data-route-panel]').isVisible(), false);
    });
    await check('Live bicycle and pedestrian routes', async () => {
        const routes = [];
        for (const costing of ['bicycle', 'pedestrian']) {
            const query = new URLSearchParams({start_lat: '48.20849', start_lon: '16.37208',
                end_lat: '48.2088', end_lon: '16.3732', costing});
            const response = await context.request.get(`${baseURL}/plugins/geoview/route/?${query}`);
            const data = await response.json();
            assert.equal(response.status(), 200, JSON.stringify(data));
            assert.equal(data.success, true);
            assert(data.route.geometry.length > 1);
            routes.push({costing, distance: data.route.distance, duration_minutes: data.route.duration_minutes});
        }
        return routes;
    });
    for (const viewport of [{width: 1920, height: 1080}, {width: 1366, height: 768}, {width: 390, height: 844}]) {
        await check(`Viewport ${viewport.width}x${viewport.height}`, async () => {
            await page.setViewportSize(viewport);
            await openMap();
            const dimensions = await page.evaluate(() => {
                const rect = document.querySelector('[data-geoview-map]').getBoundingClientRect();
                return {width: innerWidth, height: innerHeight, documentWidth: document.documentElement.scrollWidth,
                    documentHeight: document.documentElement.scrollHeight, mapBottom: rect.bottom, mapHeight: rect.height};
            });
            assert(dimensions.documentWidth <= dimensions.width + 1, JSON.stringify(dimensions));
            assert(dimensions.mapHeight > 200, JSON.stringify(dimensions));
            if (viewport.width >= 1000) assert(dimensions.documentHeight <= dimensions.height + 1, JSON.stringify(dimensions));
            await page.screenshot({path: path.join(output, `map-${viewport.width}.png`), fullPage: true});
            return dimensions;
        });
    }
    await check('No uncaught JavaScript errors', async () => assert.deepEqual(errors, []));
    fs.writeFileSync(path.join(output, 'results.json'), JSON.stringify(results, null, 2));
    await browser.close();
    if (results.some(result => !result.passed)) process.exitCode = 1;
})().catch(error => { console.error(error); process.exitCode = 1; });
