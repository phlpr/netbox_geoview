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

    function renderPopupTableRows(rows) {
        const safeRows = Array.isArray(rows) ? rows : [];
        if (safeRows.length === 0) {
            return '<div class="geoview-popup-none"><em>none</em></div>';
        }
        const tableRows = safeRows.map(function (row) {
            const label = Array.isArray(row) ? row[0] : "";
            const value = Array.isArray(row) ? row[1] : "";
            return `<tr><th>${escapeHtml(label)}</th><td>${escapeHtml(value)}</td></tr>`;
        }).join("");
        return `<table class="geoview-popup-table"><tbody>${tableRows}</tbody></table>`;
    }

    function renderPopupList(items) {
        const safeItems = Array.isArray(items) ? items.filter(Boolean) : [];
        if (safeItems.length === 0) {
            return '<div class="geoview-popup-none"><em>none</em></div>';
        }
        const listItems = safeItems.map(function (item) {
            return `<li>${escapeHtml(item)}</li>`;
        }).join("");
        return `<ul class="geoview-popup-list">${listItems}</ul>`;
    }

    function buildSitePopup(marker) {
        const sections = Array.isArray(marker.popup_sections) ? marker.popup_sections : [];
        const hasCoordinates = Number.isFinite(Number(marker.latitude)) && Number.isFinite(Number(marker.longitude));
        const googleMapsUrl = hasCoordinates
            ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${marker.latitude},${marker.longitude}`)}`
            : "";
        const linkBlock = marker.netbox_url
            ? `<div class="geoview-popup-link">NetBox: <a href="${escapeHtml(marker.netbox_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(marker.netbox_url)}</a></div>`
            : "";
        const mapsBlock = googleMapsUrl
            ? `<div class="geoview-popup-link"><a href="${escapeHtml(googleMapsUrl)}" target="_blank" rel="noopener noreferrer">Open in Google Maps</a></div>`
            : "";
        const sectionBlocks = sections.map(function (section) {
            const title = escapeHtml(section.title || "");
            const mode = section.mode || "table";
            const body = mode === "list"
                ? renderPopupList(section.items)
                : renderPopupTableRows(section.rows);
            return `
                <div class="geoview-popup-section">
                    <div class="geoview-popup-section-title">${title}</div>
                    ${body}
                </div>
            `;
        }).join("");

        return `
            <div class="geoview-popup">
                <div class="geoview-popup-body">
                    <div class="geoview-popup-title">${escapeHtml(marker.name || "")}</div>
                    ${linkBlock}
                    ${mapsBlock}
                    ${sectionBlocks}
                </div>
            </div>
        `;
    }

    function fitMapToBounds(map, bounds, config) {
        if (bounds.length > 0) {
            map.fitBounds(bounds, {
                padding: [24, 24],
                maxZoom: Math.max(config.zoom, 10),
            });
            return;
        }
        map.setView([config.lat, config.lon], config.zoom);
    }

    function addRecenterControl(map, config, bounds) {
        const RecenterControl = window.L.Control.extend({
            options: {
                position: "topleft",
            },
            onAdd: function () {
                const container = window.L.DomUtil.create("div", "leaflet-bar geoview-recenter-control");
                const button = window.L.DomUtil.create("a", "", container);
                button.href = "#";
                button.title = "Center all markers";
                button.setAttribute("aria-label", "Center all markers");
                button.innerHTML = '<i class="mdi mdi-crosshairs-gps" aria-hidden="true"></i>';

                window.L.DomEvent.disableClickPropagation(container);
                window.L.DomEvent.on(button, "click", function (event) {
                    window.L.DomEvent.preventDefault(event);
                    fitMapToBounds(map, bounds, config);
                });

                return container;
            },
        });

        map.addControl(new RecenterControl());
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
            leafletMarker.bindTooltip(escapeHtml(marker.name), {
                permanent: true,
                direction: "top",
                offset: [0, -32],
                className: "geoview-marker-label",
            });
            leafletMarker.addTo(map);
            bounds.push(latLng);
        });

        fitMapToBounds(map, bounds, config);
        return bounds;
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

        const markerBounds = addSiteMarkers(map, config);
        addRecenterControl(map, config, markerBounds);
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-geoview-map]").forEach(renderMap);
    });
}());
