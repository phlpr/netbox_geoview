(function () {
    function escapeHtml(value) {
        return String(value)
            .replaceAll("&", "&amp;")
            .replaceAll("<", "&lt;")
            .replaceAll(">", "&gt;")
            .replaceAll('"', "&quot;")
            .replaceAll("'", "&#39;");
    }

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

    function createSiteMarkerIcon(markerStyle) {
        if (markerStyle.icon_url) {
            return window.L.icon({
                iconUrl: markerStyle.icon_url,
                iconSize: markerStyle.icon_size,
                iconAnchor: markerStyle.icon_anchor,
                popupAnchor: markerStyle.popup_anchor,
            });
        }

        const symbol = markerStyle.symbol ? `<span class="geoview-site-marker__symbol">${escapeHtml(markerStyle.symbol)}</span>` : "";

        return window.L.divIcon({
            className: "geoview-site-marker-icon",
            html: `
                <span class="geoview-site-marker" style="--geoview-marker-color: ${escapeHtml(markerStyle.color || "#f1c40f")};">
                    <span class="geoview-site-marker__body"></span>
                    ${symbol}
                </span>
            `,
            iconSize: markerStyle.icon_size,
            iconAnchor: markerStyle.icon_anchor,
            popupAnchor: markerStyle.popup_anchor,
        });
    }

    function buildSitePopup(marker) {
        const lines = [`<strong>${escapeHtml(marker.name)}</strong>`];
        if (marker.group_name) {
            lines.push(escapeHtml(marker.group_name));
        }
        return lines.join("<br>");
    }

    function addSiteMarkers(map, config) {
        const markers = Array.isArray(config.site_markers) ? config.site_markers : [];
        const bounds = [];

        markers.forEach(function (marker) {
            const latLng = [marker.latitude, marker.longitude];
            const leafletMarker = window.L.marker(latLng, {
                icon: createSiteMarkerIcon(marker.marker_style || {}),
            });
            leafletMarker.bindPopup(buildSitePopup(marker));
            leafletMarker.addTo(map);
            bounds.push(latLng);
        });

        if (bounds.length > 0) {
            map.fitBounds(bounds, {
                padding: [24, 24],
                maxZoom: Math.max(config.zoom, 10),
            });
        }
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

        addSiteMarkers(map, config);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-geoview-map]").forEach(renderMap);
    });
}());
