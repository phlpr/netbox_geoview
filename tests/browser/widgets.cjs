// Saved-filter and dashboard scenarios against an isolated, authenticated NetBox.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const {chromium} = require('playwright');

(async () => {
    const base = process.env.GEOVIEW_BASE_URL;
    const output = process.env.GEOVIEW_ARTIFACTS;
    assert(base && output && process.env.GEOVIEW_COOKIE_FILE && process.env.GEOVIEW_SITE_IDS);
    fs.mkdirSync(output, {recursive: true});
    const browser = await chromium.launch({headless: true});
    try {
    const context = await browser.newContext({viewport: {width: 1440, height: 1000}});
    await context.addCookies([JSON.parse(fs.readFileSync(process.env.GEOVIEW_COOKIE_FILE, 'utf8'))]);
    const page = await context.newPage();
    const errors = [];
    const results = [];
    page.on('pageerror', error => errors.push(error.message));
    const check = async (name, fn) => {
        try { await fn(); results.push({name, passed: true}); }
        catch (error) { results.push({name, passed: false, error: error.message}); }
        console.log(JSON.stringify(results.at(-1)));
    };
    const suffix = Date.now().toString();
    const slug = 'widget-browser-' + suffix;
    let filterId;
    await check('Save and reload exclusion filter through GeoView UI', async () => {
        const firstSite = process.env.GEOVIEW_SITE_IDS.split(',')[0];
        await page.goto(`${base}/plugins/geoview/?site=${firstSite}&site_op=n`);
        await page.locator('[data-geoview-rendered="1"]').waitFor();
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 2);
        await page.locator('a[href*="/plugins/geoview/saved-filters/add/"]').click();
        await page.locator('#id_name').fill('Widget browser ' + suffix);
        await page.locator('#id_slug').fill(slug);
        await page.getByRole('button', {name: 'Save', exact: true}).click();
        await page.waitForURL('**/plugins/geoview/?filter_id=*');
        filterId = new URL(page.url()).searchParams.get('filter_id');
        assert(filterId);
        await page.locator('[data-geoview-rendered="1"]').waitFor();
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 2);
        await page.locator('#filter-tab').click();
        assert.equal(await page.locator('select[name="site_op"]').inputValue(), 'n');
    });
    assert(filterId, 'Filter creation failed; cannot continue widget checks');
    await check('Add two native dashboard widgets through configuration forms', async () => {
        await page.goto(`${base}/plugins/geoview/?q=gv-vie-core-01`);
        await page.locator('a[href*="/plugins/geoview/saved-filters/add/"]').click();
        await page.locator('#id_name').fill('Widget device ' + suffix);
        await page.locator('#id_slug').fill(slug + '-device');
        await page.getByRole('button', {name: 'Save', exact: true}).click();
        await page.waitForURL('**/plugins/geoview/?filter_id=*');
        const deviceFilterId = new URL(page.url()).searchParams.get('filter_id');
        await page.goto(`${base}/`);
        const csrf = (await context.cookies()).find(cookie => cookie.name === 'csrftoken').value;
        // Exercise NetBox's actual add view, including the plugin ConfigForm and JSON storage.
        for (const [title, selectedFilter] of [['GeoView browser A', filterId], ['GeoView browser B', deviceFilterId]]) {
            const response = await context.request.post(`${base}/extras/dashboard/widgets/add/`, {
                headers: {'X-CSRFToken': csrf, 'HX-Request': 'true', 'Referer': base + '/'},
                form: {widget_class: 'netbox_geoview.GeoViewMapWidget', title,
                    'config-saved_filter_id': selectedFilter, 'config-fit_bounds': 'on'},
            });
            assert.equal(response.status(), 200);
            assert(response.headers()['hx-redirect'], 'NetBox rejected the widget configuration');
        }
        await page.reload();
        await page.locator('[data-geoview-widget-map][data-geoview-rendered="1"]').nth(1).waitFor();
        const roots = page.locator('[data-geoview-widget]');
        assert.equal(await roots.count(), 2);
        assert.equal(await roots.nth(0).locator('.leaflet-marker-icon').count(), 2);
        assert.equal(await roots.nth(1).locator('.leaflet-marker-icon').count(), 1);
        assert.equal(await page.locator('script[src*="vendor/leaflet/leaflet.js"]').count(), 1);
        assert.equal(await page.locator('script[src*="/geoview.js"]').count(), 1);
    });
    await check('Widget popup, full-view link and refresh', async () => {
        const widget = page.locator('[data-geoview-widget]').first();
        await widget.locator('.leaflet-marker-icon').first().click();
        await widget.locator('.leaflet-popup').waitFor();
        assert.equal(await widget.locator('[data-route-point]').count(), 0);
        assert((await widget.locator('[data-geoview-open]').getAttribute('href')).includes('filter_id=' + filterId));
        await widget.locator('[data-geoview-refresh]').click();
        await widget.locator('[data-geoview-widget-map][data-geoview-rendered="1"]').waitFor();
        assert.equal(await widget.locator('.leaflet-marker-icon').count(), 2);
    });
    await check('Unavailable filter clears previous marker data without fallback', async () => {
        const widget = page.locator('[data-geoview-widget]').first();
        const original = await widget.getAttribute('data-url');
        await widget.evaluate(root => { root.dataset.url = '/plugins/geoview/map-data/?filter_id=999999999'; });
        await Promise.all([
            page.waitForResponse(response => response.url().includes('filter_id=999999999')),
            widget.locator('[data-geoview-refresh]').click(),
        ]);
        await widget.locator('[data-geoview-refresh]').waitFor({state: 'visible'});
        await page.waitForFunction(() => !document.querySelector('[data-geoview-widget] [data-geoview-refresh]').disabled);
        await widget.evaluate(root => window.GeoView.init(root));
        assert.equal(await widget.locator('.leaflet-marker-icon').count(), 0);
        assert.equal(await widget.locator('script[type="application/json"]').count(), 0);
        await widget.evaluate((root, value) => { root.dataset.url = value; }, original);
        await widget.locator('[data-geoview-refresh]').click();
        await widget.locator('[data-geoview-widget-map][data-geoview-rendered="1"]').waitFor();
    });
    await check('Independent resize and idempotent HTMX initialization', async () => {
        const widget = page.locator('[data-geoview-widget]').first();
        await widget.evaluate(root => {
            root.style.height = '340px';
            document.dispatchEvent(new CustomEvent('htmx:load', {detail: {elt: root}}));
            window.GeoView.init(root);
            window.GeoViewWidgets.init(root);
        });
        await page.waitForTimeout(150);
        assert.equal(await widget.locator('.leaflet-container').count(), 1);
        assert.equal(await widget.locator('.leaflet-marker-icon').count(), 2);
    });
    for (const theme of ['light', 'dark']) {
        await check('Dashboard map ' + theme + ' theme', async () => {
            if (await page.locator('html').getAttribute('data-bs-theme') !== theme) await page.locator('.color-mode-toggle:visible').click();
            const widget = page.locator('[data-geoview-widget]').first();
            const close = widget.locator('.leaflet-popup-close-button');
            if (await close.isVisible()) {
                await close.click();
                await widget.locator('.leaflet-popup').waitFor({state: 'detached'});
            }
            await widget.locator('.leaflet-marker-icon').first().click();
            await widget.locator('.leaflet-popup').waitFor();
            await page.waitForFunction(() => {
                const popup = document.querySelector('[data-geoview-widget] .leaflet-popup');
                return popup && getComputedStyle(popup).opacity === '1';
            }, null, {timeout: 5000});
            await page.waitForTimeout(300);
            const bounds = await widget.evaluate(root => {
                const map = root.querySelector('[data-geoview-widget-map]').getBoundingClientRect();
                const popup = root.querySelector('.leaflet-popup').getBoundingClientRect();
                return {mapTop: map.top, mapBottom: map.bottom, popupTop: popup.top, popupBottom: popup.bottom};
            });
            assert(bounds.popupTop >= bounds.mapTop - 2 && bounds.popupBottom <= bounds.mapBottom + 2, JSON.stringify(bounds));
            const colors = await widget.locator('.leaflet-popup-content-wrapper').evaluate(element => {
                const probe = document.createElement('div');
                probe.style.backgroundColor = 'var(--tblr-bg-surface)';
                document.body.appendChild(probe);
                const expected = getComputedStyle(probe).backgroundColor;
                probe.remove();
                return {actual: getComputedStyle(element).backgroundColor, expected};
            });
            assert.equal(colors.actual, colors.expected);
            await widget.screenshot({path: path.join(output, 'widget-' + theme + '.png')});
        });
    }
    await check('Mobile dashboard without horizontal overflow', async () => {
        const popupClose = page.locator('[data-geoview-widget] .leaflet-popup-close-button');
        if (await popupClose.isVisible()) {
            await popupClose.click();
            await page.locator('[data-geoview-widget] .leaflet-popup').waitFor({state: 'detached'});
        }
        await page.setViewportSize({width: 390, height: 844});
        await page.waitForTimeout(350);
        assert(await page.evaluate(() => document.documentElement.scrollWidth <= innerWidth + 1));
        const widgetsFit = await page.locator('[data-geoview-widget]').evaluateAll(roots => roots.every(root => {
            const map = root.querySelector('[data-geoview-widget-map]').getBoundingClientRect();
            const refresh = root.querySelector('[data-geoview-refresh]').getBoundingClientRect();
            const bounds = root.getBoundingClientRect();
            return refresh.left >= bounds.left && refresh.right <= bounds.right + 1 &&
                Array.from(root.querySelectorAll('.leaflet-marker-icon')).every(marker => {
                    const point = marker.getBoundingClientRect();
                    const x = point.left + point.width / 2;
                    const y = point.bottom;
                    return x >= map.left && x <= map.right && y >= map.top && y <= map.bottom;
                });
        }));
        assert(widgetsFit, 'Widget toolbar or marker escaped the mobile map bounds');
        await page.screenshot({path: path.join(output, 'widget-mobile.png'), fullPage: true});
    });
    await check('No browser JavaScript errors', async () => assert.deepEqual(errors, []));
    fs.writeFileSync(path.join(output, 'widget-results.json'), JSON.stringify(results, null, 2));
    if (results.some(result => !result.passed)) process.exitCode = 1;
    } finally {
        await browser.close();
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
