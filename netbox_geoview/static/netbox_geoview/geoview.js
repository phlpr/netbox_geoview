(function () {
    function clamp(value, min, max) {
        return Math.min(Math.max(value, min), max);
    }

    function wrap(value, size) {
        return ((value % size) + size) % size;
    }

    function getTileCoordinate(lat, lon, zoom) {
        const latitude = clamp(lat, -85.05112878, 85.05112878);
        const scale = 2 ** zoom;
        const x = ((lon + 180) / 360) * scale;
        const radians = (latitude * Math.PI) / 180;
        const y =
            ((1 - Math.log(Math.tan(radians) + 1 / Math.cos(radians)) / Math.PI) / 2) *
            scale;
        return {
            x: Math.floor(x),
            y: Math.floor(y),
            scale,
        };
    }

    function buildTileUrl(template, zoom, x, y) {
        return template
            .replace("{z}", String(zoom))
            .replace("{x}", String(x))
            .replace("{y}", String(y));
    }

    function renderMap(element) {
        const lat = Number.parseFloat(element.dataset.lat || "20");
        const lon = Number.parseFloat(element.dataset.lon || "0");
        const zoom = Number.parseInt(element.dataset.zoom || "2", 10);
        const tileTemplate = element.dataset.tileUrl || "";
        const overlayAttribution = element.dataset.overlayAttribution || "";
        const center = getTileCoordinate(lat, lon, zoom);
        let tiles = "";

        if (!tileTemplate) {
            return;
        }

        for (let row = -1; row <= 1; row += 1) {
            for (let column = -1; column <= 1; column += 1) {
                const x = wrap(center.x + column, center.scale);
                const y = clamp(center.y + row, 0, center.scale - 1);
                const src = buildTileUrl(tileTemplate, zoom, x, y);
                tiles += `<img class="geoview-map__tile" src="${src}" alt="" loading="lazy">`;
            }
        }

        element.innerHTML = `
            <div class="geoview-map__tiles">${tiles}</div>
            <div class="geoview-map__overlay">
                <span class="geoview-map__overlay-meta">${overlayAttribution}</span>
            </div>
        `;
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-geoview-map]").forEach(renderMap);
    });
}());
