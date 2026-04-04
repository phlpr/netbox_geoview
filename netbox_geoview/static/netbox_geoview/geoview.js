(function () {
    function getMapConfig(element) {
        const configId = element.dataset.configId;

        if (!configId) {
            return null;
        }

        const configNode = document.getElementById(configId);

        if (!configNode) {
            return null;
        }

        return JSON.parse(configNode.textContent);
    }

    function buildTileUrl(template, layerId) {
        return template.replace("__layer__", encodeURIComponent(layerId));
    }

    function createBaseLayer(config, layer) {
        return window.L.tileLayer(buildTileUrl(config.tile_proxy_url_template, layer.id), {
            attribution: layer.attribution || "",
            minZoom: layer.min_zoom,
            maxZoom: layer.max_zoom,
        });
    }

    function renderMap(element) {
        if (!window.L) {
            return;
        }

        const config = getMapConfig(element);

        if (!config || !Array.isArray(config.tile_layers) || config.tile_layers.length === 0) {
            return;
        }

        const map = window.L.map(element, {
            center: [config.lat, config.lon],
            zoom: config.zoom,
            minZoom: config.min_zoom,
            maxZoom: config.max_zoom,
            scrollWheelZoom: Boolean(config.scroll_wheel_zoom),
            zoomControl: true,
        });

        const baseLayers = {};
        let activeLayer = null;

        config.tile_layers.forEach(function (layer) {
            const tileLayer = createBaseLayer(config, layer);
            baseLayers[layer.name] = tileLayer;
            if (layer.id === config.default_tile_layer_id) {
                activeLayer = tileLayer;
            }
        });

        if (!activeLayer) {
            activeLayer = Object.values(baseLayers)[0];
        }

        if (activeLayer) {
            activeLayer.addTo(map);
        }

        window.L.control.layers(baseLayers, {}, {
            collapsed: true,
            position: "topright",
        }).addTo(map);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-geoview-map]").forEach(renderMap);
    });
}());
