// Self-contained regression checks using the real Leaflet and GeoView assets.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const http = require('node:http');
const path = require('node:path');
const {chromium} = require('playwright');

const assets = path.resolve(__dirname, '../../netbox_geoview/static/netbox_geoview');
const image = Buffer.from('iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+jRZkAAAAASUVORK5CYII=', 'base64');
const markerStyle = {icon_size: [28, 40], icon_anchor: [14, 40], popup_anchor: [0, -36]};
const config = {
    // Deliberately far from the marker, so preliminary viewport requests fail the test.
    lat: 0, lon: 0, zoom: 4, min_zoom: 1, max_zoom: 18,
    fit_bounds: true, scroll_wheel_zoom: false, default_tile_layer_id: 'base',
    routing: {enabled: false}, ui: {show_route_actions: false},
    tile_proxy_url_template: '/tiles/__layer__/{z}/{x}/{y}.png',
    tile_layers: ['base', 'other'].map(id => ({id, name: id, min_zoom: 1, max_zoom: 18})),
    site_markers: [{name: 'Original', latitude: 48.2, longitude: 16.37, marker_style: markerStyle}],
};
let dataStatus = 200;
let dataDelay = 0;
let dataRequests = 0;
let tileRequests = 0;
let tileRevalidations = 0;
let holdNextTile = true;
let tileStatus = 200;
const tilePaths = [];
const pendingTiles = [];
const html = `<!doctype html><html><head>
<style>.d-none {display:none}</style>
</head><body><div data-geoview-widget="1" class="geoview-widget" style="width:640px;height:400px"
 data-url="/map-data/" data-loading="Loading" data-empty="Empty" data-error="Error"
 data-leaflet-css="/static/vendor/leaflet/leaflet.css" data-geoview-css="/static/geoview.css"
 data-leaflet-js="/static/vendor/leaflet/leaflet.js" data-geoview-js="/static/geoview.js">
 <div><a data-geoview-open class="d-none">Open</a><button data-geoview-refresh>Refresh</button></div>
 <div data-geoview-status></div><div data-geoview-widget-map data-loading-label="Loading map"
 class="geoview-map geoview-map--widget"></div>
</div><script src="/static/widget.js"></script></body></html>`;

const server = http.createServer((req, res) => {
    const url = new URL(req.url, 'http://localhost');
    if (url.pathname === '/') return res.end(html);
    if (url.pathname === '/map/') return res.end(`<!doctype html><html><head>
        <link rel="stylesheet" href="/static/vendor/leaflet/leaflet.css">
        <link rel="stylesheet" href="/static/geoview.css">
        <script defer src="/static/vendor/leaflet/leaflet.js"></script>
        <script defer src="/static/geoview.js"></script></head><body>
        <script type="application/json" id="config">${JSON.stringify(config)}</script>
        <div data-geoview-map data-config-id="config" data-loading-label="Loading map"
        class="geoview-map" style="width:700px;height:450px;min-height:0"></div></body></html>`);
    if (url.pathname === '/map-data/') {
        dataRequests++;
        const body = JSON.stringify({config, map_url: '/plugins/geoview/?filter_id=1'});
        const status = dataStatus;
        return setTimeout(() => {
            res.writeHead(status, {'Content-Type': 'application/json', 'Cache-Control': 'private, no-store'});
            res.end(body);
        }, dataDelay);
    }
    if (url.pathname.startsWith('/tiles/')) {
        tileRequests++;
        tilePaths.push(url.pathname);
        const unchanged = tileStatus === 200 && req.headers['if-none-match'] === '"tile"';
        if (unchanged) tileRevalidations++;
        const status = unchanged ? 304 : tileStatus;
        const respond = () => {
            res.writeHead(status, status === 404 ? {
                'Content-Type': 'text/plain', 'Cache-Control': 'no-store',
            } : {
                'Content-Type': 'image/png',
                'Cache-Control': 'private, no-cache', ETag: '"tile"',
            });
            res.end(status === 404 ? 'Missing tile' : (unchanged ? undefined : image));
        };
        if (holdNextTile) {
            holdNextTile = false;
            return pendingTiles.push(respond);
        }
        return respond();
    }
    if (url.pathname.startsWith('/static/')) {
        const file = path.resolve(assets, url.pathname.slice('/static/'.length));
        if (file.startsWith(assets + path.sep) && fs.existsSync(file)) {
            res.setHeader('Content-Type', file.endsWith('.css') ? 'text/css' : 'application/javascript');
            return res.end(fs.readFileSync(file));
        }
    }
    res.writeHead(404).end();
});

(async () => {
    let browser;
    await new Promise(resolve => server.listen(0, '127.0.0.1', resolve));
    try {
        browser = await chromium.launch({headless: true});
        const page = await browser.newPage({viewport: {width: 1000, height: 700}});
        const errors = [];
        page.on('pageerror', error => errors.push(error.message));
        const ready = async () => {
            await page.waitForFunction(() => document.querySelector('[data-geoview-widget-map]').dataset.geoviewRendered === '1' &&
                document.querySelector('[data-geoview-widget-map]').dataset.geoviewLoading === '0' &&
                !document.querySelector('[data-geoview-refresh]').disabled);
            await page.waitForLoadState('networkidle');
        };
        const refresh = async () => { await page.locator('[data-geoview-refresh]').click(); await ready(); };
        const rememberTiles = async () => page.evaluate(() => {
            window.previousTiles = Array.from(document.querySelectorAll('.leaflet-tile-loaded'));
            if (!window.previousTiles.length) throw new Error('No loaded tiles');
            window.previousPane = document.querySelector('.leaflet-map-pane');
            window.previousTransform = window.previousPane.style.transform;
        });
        const assertTilesKept = async () => assert(await page.evaluate(() =>
            window.previousTiles.every(tile => tile.isConnected) &&
            document.querySelector('.leaflet-map-pane') === window.previousPane &&
            window.previousPane.style.transform === window.previousTransform), 'Refresh replaced tiles or moved the view');
        const partiallyLoaded = async () => {
            await page.waitForFunction(() => document.querySelector('[data-geoview-map]')?.dataset.geoviewLoading === '1' &&
                document.querySelector('.leaflet-tile-loaded'));
            assert.equal(pendingTiles.length, 1);
            assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '0',
                'Partially loaded tiles were visible');
            assert.equal(await page.locator('[data-geoview-map]').getAttribute('aria-busy'), 'true');
        };
        const releaseTiles = () => pendingTiles.splice(0).forEach(respond => respond());

        await page.goto(`http://127.0.0.1:${server.address().port}/`, {waitUntil: 'domcontentloaded'});
        await partiallyLoaded();
        assert(tilePaths.length > 1 && tilePaths.every(url => url.includes('/10/')), 'Requested a preliminary viewport');
        releaseTiles();
        await ready();
        assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '1');
        assert.equal(await page.locator('.leaflet-fade-anim').count(), 0);
        console.log('Only the final viewport loads; initial tiles appear together without fading: passed');
        await page.locator('.leaflet-control-layers').hover();
        await page.getByLabel('other', {exact: true}).check();
        await page.locator('.leaflet-control-zoom-in').click();
        await page.waitForFunction(() => Array.from(document.querySelectorAll('.leaflet-tile')).some(tile => tile.src.includes('/11/')));
        await page.waitForFunction(() => !document.querySelector('.leaflet-zoom-anim'));
        await page.waitForLoadState('networkidle');
        await rememberTiles();
        const requestsBefore = tileRequests;
        const dataBefore = dataRequests;
        for (let i = 0; i < 3; i++) {
            config.site_markers[0].name = 'Updated ' + i;
            await refresh();
            await assertTilesKept();
            assert.equal(tileRequests, requestsBefore, 'Refresh requested tiles again');
            assert(await page.getByLabel('other', {exact: true}).isChecked(), 'Refresh reset the selected layer');
            await page.locator('.leaflet-marker-icon').click();
            await page.locator('.leaflet-popup').waitFor();
            assert.equal(await page.locator('.geoview-popup-title').innerText(), 'Updated ' + i);
            await page.locator('[data-popup-close]').click();
            await page.locator('.leaflet-popup').waitFor({state: 'detached'});
        }
        assert.equal(dataRequests, dataBefore + 3, 'Refresh did not fetch fresh marker data');
        console.log('Repeated refresh updates popups and retains tiles, layer and viewport: passed');

        config.site_markers[0].latitude = 50;
        config.site_markers[0].longitude = 10;
        await refresh();
        await assertTilesKept();
        const recenterRequest = page.waitForRequest(request => request.url().includes('/tiles/'));
        await page.locator('.geoview-recenter-control a').click();
        await recenterRequest;
        await page.waitForFunction(() => !document.querySelector('.leaflet-zoom-anim') && document.querySelector('.leaflet-tile-loaded'));
        await page.waitForLoadState('networkidle');
        assert(tileRequests > requestsBefore, 'Recenter ignored the updated marker coordinates');
        console.log('Recenter uses refreshed marker coordinates: passed');

        await rememberTiles();
        config.site_markers = [];
        await refresh();
        await assertTilesKept();
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 0);
        console.log('Empty result clears markers while retaining tiles: passed');

        config.site_markers = [{name: 'Recovered', latitude: 48.2, longitude: 16.37, marker_style: markerStyle}];
        await refresh();
        dataStatus = 403;
        await page.locator('[data-geoview-refresh]').click();
        await page.waitForFunction(() => document.querySelector('[data-geoview-status]').textContent === 'Error');
        assert.equal(await page.locator('.leaflet-marker-icon, .leaflet-tile, script[type="application/json"]').count(), 0);
        await page.evaluate(() => window.GeoView.init(document));
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 0);
        dataStatus = 200;
        await refresh();
        assert.equal(await page.locator('.leaflet-marker-icon').count(), 1);
        console.log('Denied refresh removes stale data; later refresh recovers: passed');

        await rememberTiles();
        config.max_zoom = 17;
        await refresh();
        assert(await page.evaluate(() => window.previousTiles.every(tile => !tile.isConnected)));
        await page.evaluate(() => {
            const root = document.querySelector('[data-geoview-widget]');
            document.dispatchEvent(new CustomEvent('htmx:load', {detail: {elt: root}}));
            window.GeoViewWidgets.init(root);
        });
        assert.equal(await page.locator('.leaflet-container').count(), 1);
        console.log('Changed map settings rebuild the map; HTMX initialization stays idempotent: passed');

        holdNextTile = true;
        const reloadStart = tilePaths.length;
        await page.reload({waitUntil: 'domcontentloaded'});
        await partiallyLoaded();
        releaseTiles();
        await ready();
        assert(tileRevalidations > 0, 'Page reload did not revalidate browser-cached tile images');
        assert(tilePaths.slice(reloadStart).every(url => url.includes('/10/')), 'Reload requested a preliminary viewport');
        assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '1');
        console.log('Page reload presents cached tiles together and revalidates their bytes: passed');

        tileStatus = 404;
        await page.reload();
        await ready();
        assert(await page.locator('.leaflet-tile').evaluateAll(tiles => tiles.length > 0 && tiles.every(tile => tile.naturalWidth === 0)));
        assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '1');
        tileStatus = 200;
        console.log('Failed tile requests reveal the usable map instead of hiding it indefinitely: passed');

        holdNextTile = true;
        await page.reload({waitUntil: 'domcontentloaded'});
        await partiallyLoaded();
        await page.waitForFunction(() => document.querySelector('[data-geoview-widget-map]').dataset.geoviewLoading === '0',
            null, {timeout: 15000});
        assert.equal(pendingTiles.length, 1, 'Stalled response unexpectedly completed before fallback');
        assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '1');
        releaseTiles();
        await ready();
        console.log('A stalled tile triggers the 12-second fallback: passed');

        config.tile_layers.forEach(layer => { layer.min_zoom = 12; });
        await page.reload();
        await ready();
        assert.equal(await page.locator('.leaflet-tile').count(), 0);
        config.tile_layers.forEach(layer => { layer.min_zoom = 1; });
        console.log('A view outside the tile layer zoom range is revealed immediately: passed');

        holdNextTile = true;
        await page.reload({waitUntil: 'domcontentloaded'});
        await partiallyLoaded();
        await page.evaluate(() => {
            window.removedMap = document.querySelector('[data-geoview-widget-map]');
            const root = document.querySelector('[data-geoview-widget]');
            document.dispatchEvent(new CustomEvent('htmx:beforeCleanupElement', {detail: {elt: root}}));
            root.remove();
        });
        releaseTiles();
        await page.waitForLoadState('networkidle');
        assert.equal(await page.evaluate(() => window.removedMap.dataset.geoviewLoading), undefined);
        console.log('HTMX cleanup cancels the initial tile reveal: passed');

        await page.goto(`http://127.0.0.1:${server.address().port}/`);
        await ready();
        dataDelay = 200;
        await page.locator('[data-geoview-refresh]').click();
        await page.evaluate(() => {
            const root = document.querySelector('[data-geoview-widget]');
            document.dispatchEvent(new CustomEvent('htmx:beforeCleanupElement', {detail: {elt: root}}));
            root.remove();
        });
        await page.waitForTimeout(300);
        assert.equal(await page.locator('.leaflet-container').count(), 0);
        holdNextTile = true;
        const fullMapStart = tilePaths.length;
        await page.goto(`http://127.0.0.1:${server.address().port}/map/`, {waitUntil: 'domcontentloaded'});
        await partiallyLoaded();
        releaseTiles();
        await page.waitForFunction(() => document.querySelector('[data-geoview-map]').dataset.geoviewLoading === '0');
        await page.waitForLoadState('networkidle');
        assert(tilePaths.slice(fullMapStart).every(url => url.includes('/10/')));
        assert.equal(await page.locator('.leaflet-map-pane').evaluate(el => getComputedStyle(el).opacity), '1');
        assert.equal(await page.locator('.leaflet-fade-anim').count(), 0);
        console.log('The full map also starts in the final viewport and appears together: passed');
        assert.deepEqual(errors, []);
        console.log('HTMX cleanup aborts pending refresh without JavaScript errors: passed');
    } finally {
        pendingTiles.splice(0).forEach(respond => respond());
        if (browser) await browser.close();
        await new Promise(resolve => server.close(resolve));
    }
})().catch(error => { console.error(error); process.exitCode = 1; });
