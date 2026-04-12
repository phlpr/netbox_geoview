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

    function buildSitePopup(marker, uiLabels) {
        const labels = uiLabels || {};
        const sections = Array.isArray(marker.popup_sections) ? marker.popup_sections : [];
        const hasCoordinates = Number.isFinite(Number(marker.latitude)) && Number.isFinite(Number(marker.longitude));
        const googleMapsUrl = hasCoordinates
            ? `https://www.google.com/maps/search/?api=1&query=${encodeURIComponent(`${marker.latitude},${marker.longitude}`)}`
            : "";
        const encodedName = encodeURIComponent(String(marker.name || ""));
        const encodedType = encodeURIComponent(String(marker.object_type || ""));
        const linkBlock = marker.netbox_url
            ? `<div class="geoview-popup-link">${escapeHtml(labels.netbox || "NetBox")}: <a href="${escapeHtml(marker.netbox_url)}" target="_blank" rel="noopener noreferrer">${escapeHtml(marker.netbox_url)}</a></div>`
            : "";
        const mapsBlock = googleMapsUrl
            ? `<div class="geoview-popup-link"><a href="${escapeHtml(googleMapsUrl)}" target="_blank" rel="noopener noreferrer">${escapeHtml(labels.open_google_maps || "Open in Google Maps")}</a></div>`
            : "";
        const closeButtonBlock = `
            <div class="geoview-popup-actions">
                <button type="button" class="btn btn-sm btn-secondary" data-popup-close>
                    ${escapeHtml(labels.close || "Close")}
                </button>
            </div>
        `;
        const routeActionsBlock = hasCoordinates
            ? `
                <div class="geoview-popup-route-actions">
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary"
                        data-route-point="start"
                        data-marker-lat="${escapeHtml(String(marker.latitude))}"
                        data-marker-lon="${escapeHtml(String(marker.longitude))}"
                        data-marker-name="${escapeHtml(encodedName)}"
                        data-marker-type="${escapeHtml(encodedType)}"
                    >${escapeHtml(labels.set_start || "Set as start")}</button>
                    <button
                        type="button"
                        class="btn btn-sm btn-outline-primary"
                        data-route-point="end"
                        data-marker-lat="${escapeHtml(String(marker.latitude))}"
                        data-marker-lon="${escapeHtml(String(marker.longitude))}"
                        data-marker-name="${escapeHtml(encodedName)}"
                        data-marker-type="${escapeHtml(encodedType)}"
                    >${escapeHtml(labels.set_end || "Set as end")}</button>
                </div>
            `
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
                    ${routeActionsBlock}
                    ${sectionBlocks}
                </div>
                ${closeButtonBlock}
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

    function parseMarkerButtonData(button) {
        const lat = Number(button.dataset.markerLat);
        const lon = Number(button.dataset.markerLon);
        if (!Number.isFinite(lat) || !Number.isFinite(lon)) {
            return null;
        }
        const markerName = button.dataset.markerName ? decodeURIComponent(button.dataset.markerName) : "";
        const markerType = button.dataset.markerType ? decodeURIComponent(button.dataset.markerType) : "";
        return {
            latitude: lat,
            longitude: lon,
            name: markerName,
            objectType: markerType,
        };
    }

    function buildDirectionsUrl(start, end) {
        return `https://www.google.com/maps/dir/?api=1&origin=${encodeURIComponent(`${start.latitude},${start.longitude}`)}&destination=${encodeURIComponent(`${end.latitude},${end.longitude}`)}&travelmode=driving`;
    }

    function renderRoutePoint(point, notSetLabel) {
        if (!point) {
            return notSetLabel;
        }
        return `${point.name} (${point.latitude.toFixed(6)}, ${point.longitude.toFixed(6)})`;
    }

    function formatDistance(distance, unit) {
        if (!Number.isFinite(distance)) {
            return "-";
        }
        const rounded = distance >= 100 ? distance.toFixed(0) : distance.toFixed(1);
        return `${rounded} ${unit || "km"}`;
    }

    function formatDuration(minutes) {
        if (!Number.isFinite(minutes)) {
            return "-";
        }
        const total = Math.max(0, Math.round(minutes));
        const hours = Math.floor(total / 60);
        const remaining = total % 60;
        if (hours > 0) {
            return `${hours} h ${remaining} min`;
        }
        return `${remaining} min`;
    }

    function addSiteMarkers(map, config, routeApi) {
        const markers = Array.isArray(config.site_markers) ? config.site_markers : [];
        const bounds = [];

        markers.forEach(function (marker) {
            const latLng = [marker.latitude, marker.longitude];
            const leafletMarker = window.L.marker(latLng, {
                icon: createSiteMarkerIcon(marker.marker_style || {}),
            });
            leafletMarker.bindPopup(buildSitePopup(marker, config.ui || {}));
            leafletMarker.bindTooltip(escapeHtml(marker.name), {
                permanent: true,
                direction: "top",
                offset: [0, -32],
                className: "geoview-marker-label",
            });
            leafletMarker.addTo(map);
            bounds.push(latLng);
        });

        map.on("popupopen", function (event) {
            const popupElement = event.popup.getElement();
            if (!popupElement) {
                return;
            }
            popupElement.querySelectorAll("[data-route-point]").forEach(function (button) {
                button.addEventListener("click", function () {
                    if (!routeApi || typeof routeApi.setPoint !== "function") {
                        return;
                    }
                    const pointType = button.dataset.routePoint;
                    const markerData = parseMarkerButtonData(button);
                    if (!markerData || !pointType) {
                        return;
                    }
                    routeApi.setPoint(pointType, markerData);
                });
            });
            popupElement.querySelectorAll("[data-popup-close]").forEach(function (button) {
                button.addEventListener("click", function () {
                    map.closePopup(event.popup);
                });
            });
        });

        fitMapToBounds(map, bounds, config);
        return bounds;
    }

    function renderMap(element) {
        element.dataset.geoviewRendered = "0";

        if (!window.L) {
            element.dataset.geoviewRenderReason = "leaflet-missing";
            return;
        }

        const config = getMapConfig(element);

        if (!config || !Array.isArray(config.tile_layers) || config.tile_layers.length === 0) {
            element.dataset.geoviewRenderReason = "config-invalid";
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

        const routeContainer = element.closest("[data-geoview-route-panel]");
        const routingConfig = config.routing && typeof config.routing === "object" ? config.routing : {};
        const fallbackCostingOptions = ["auto", "bicycle", "pedestrian"];
        const costingOptions = Array.isArray(routingConfig.costing_options) && routingConfig.costing_options.length > 0
            ? routingConfig.costing_options
            : fallbackCostingOptions;
        const defaultCostingLabels = {
            auto: "Car",
            bicycle: "Bicycle",
            pedestrian: "Walking",
        };
        const costingLabels = routingConfig.costing_labels && typeof routingConfig.costing_labels === "object"
            ? { ...defaultCostingLabels, ...routingConfig.costing_labels }
            : defaultCostingLabels;
        const routingEnabled = Boolean(routingConfig.endpoint && (routingConfig.enabled !== false));
        const defaultCosting = costingOptions.includes(routingConfig.default_costing)
            ? routingConfig.default_costing
            : (costingOptions[0] || "auto");
        const routeState = {
            start: null,
            end: null,
            line: null,
            alternativeLines: [],
            isCalculating: false,
            panelCollapsed: false,
        };
        const routeUi = {
            container: routeContainer,
            panel: routeContainer ? routeContainer.querySelector("[data-route-panel]") : null,
            toggle: routeContainer ? routeContainer.querySelector("[data-route-toggle]") : null,
            start: routeContainer ? routeContainer.querySelector("[data-route-start]") : null,
            end: routeContainer ? routeContainer.querySelector("[data-route-end]") : null,
            open: routeContainer ? routeContainer.querySelector("[data-route-open]") : null,
            clear: routeContainer ? routeContainer.querySelector("[data-route-clear]") : null,
            costing: routeContainer ? routeContainer.querySelector("[data-route-costing]") : null,
            error: routeContainer ? routeContainer.querySelector("[data-route-error]") : null,
            summary: routeContainer ? routeContainer.querySelector("[data-route-summary]") : null,
            alternatives: routeContainer ? routeContainer.querySelector("[data-route-alternatives]") : null,
            notSetLabel: routeContainer ? (routeContainer.dataset.labelNotSet || "Not set") : "Not set",
            calculateLabel: routeContainer ? (routeContainer.dataset.labelCalculateRoute || "Calculate route") : "Calculate route",
            calculatingLabel: routeContainer ? (routeContainer.dataset.labelCalculatingRoute || "Calculating route...") : "Calculating route...",
            clearLabel: routeContainer ? (routeContainer.dataset.labelClearRoute || "Clear") : "Clear",
            noRouteLabel: routeContainer ? (routeContainer.dataset.labelNoRoute || "No route calculated yet.") : "No route calculated yet.",
            routeErrorLabel: routeContainer ? (routeContainer.dataset.labelRouteError || "Route could not be calculated.") : "Route could not be calculated.",
            distanceLabel: routeContainer ? (routeContainer.dataset.labelDistance || "Distance") : "Distance",
            durationLabel: routeContainer ? (routeContainer.dataset.labelDuration || "Duration") : "Duration",
            modeLabel: routeContainer ? (routeContainer.dataset.labelMode || "Mode") : "Mode",
            alternativeLabel: routeContainer ? (routeContainer.dataset.labelAlternative || "Alternative") : "Alternative",
            collapsePanelLabel: routeContainer ? (routeContainer.dataset.labelCollapseRoutePanel || "Collapse route panel") : "Collapse route panel",
            expandPanelLabel: routeContainer ? (routeContainer.dataset.labelExpandRoutePanel || "Expand route panel") : "Expand route panel",
        };

        function clearRouteLines() {
            if (routeState.line) {
                map.removeLayer(routeState.line);
                routeState.line = null;
            }
            routeState.alternativeLines.forEach(function (line) {
                map.removeLayer(line);
            });
            routeState.alternativeLines = [];
        }

        function updateRouteLine() {
            clearRouteLines();
            if (!routeState.start || !routeState.end) {
                return;
            }
            routeState.line = window.L.polyline(
                [
                    [routeState.start.latitude, routeState.start.longitude],
                    [routeState.end.latitude, routeState.end.longitude],
                ],
                {
                    color: "#0d6efd",
                    weight: 4,
                    opacity: 0.85,
                    dashArray: "10 8",
                }
            ).addTo(map);
        }

        function setRouteError(message) {
            if (!routeUi.error) {
                return;
            }
            if (message) {
                routeUi.error.textContent = message;
                routeUi.error.classList.remove("d-none");
                return;
            }
            routeUi.error.textContent = "";
            routeUi.error.classList.add("d-none");
        }

        function setRouteSummary(route, costing) {
            if (!routeUi.summary) {
                return;
            }
            if (!route) {
                routeUi.summary.innerHTML = escapeHtml(routeUi.noRouteLabel);
                return;
            }
            routeUi.summary.innerHTML = `
                <div class="geoview-route-panel__summary-row">
                    <span>${escapeHtml(routeUi.modeLabel)}</span>
                    <strong>${escapeHtml(costingLabels[costing] || costing)}</strong>
                </div>
                <div class="geoview-route-panel__summary-row">
                    <span>${escapeHtml(routeUi.distanceLabel)}</span>
                    <strong>${escapeHtml(formatDistance(Number(route.distance), route.distance_unit))}</strong>
                </div>
                <div class="geoview-route-panel__summary-row">
                    <span>${escapeHtml(routeUi.durationLabel)}</span>
                    <strong>${escapeHtml(formatDuration(Number(route.duration_minutes)))}</strong>
                </div>
            `;
        }

        function setAlternativeSummary(alternatives) {
            if (!routeUi.alternatives) {
                return;
            }
            const entries = Array.isArray(alternatives) ? alternatives : [];
            if (entries.length === 0) {
                routeUi.alternatives.innerHTML = "";
                return;
            }
            routeUi.alternatives.innerHTML = entries.map(function (route, index) {
                return `
                    <div class="geoview-route-panel__alternative">
                        <div class="geoview-route-panel__alternative-title">${escapeHtml(routeUi.alternativeLabel)} ${index + 1}</div>
                        <div>${escapeHtml(routeUi.distanceLabel)}: ${escapeHtml(formatDistance(Number(route.distance), route.distance_unit))}</div>
                        <div>${escapeHtml(routeUi.durationLabel)}: ${escapeHtml(formatDuration(Number(route.duration_minutes)))}</div>
                    </div>
                `;
            }).join("");
        }

        function drawValhallaRoute(route, alternatives) {
            clearRouteLines();
            if (!route || !Array.isArray(route.geometry) || route.geometry.length === 0) {
                return;
            }
            routeState.line = window.L.polyline(route.geometry, {
                color: "#0d6efd",
                weight: 5,
                opacity: 0.9,
            }).addTo(map);
            const bounds = window.L.latLngBounds(route.geometry);
            const alternativeSet = Array.isArray(alternatives) ? alternatives : [];
            alternativeSet.forEach(function (alternative) {
                if (!Array.isArray(alternative.geometry) || alternative.geometry.length === 0) {
                    return;
                }
                const line = window.L.polyline(alternative.geometry, {
                    color: "#6c757d",
                    weight: 4,
                    opacity: 0.75,
                    dashArray: "10 8",
                }).addTo(map);
                routeState.alternativeLines.push(line);
                bounds.extend(line.getBounds());
            });
            if (bounds.isValid()) {
                map.fitBounds(bounds.pad(0.15), {
                    maxZoom: Math.max(config.zoom, 12),
                });
            }
        }

        function updatePanelToggleButton() {
            if (!routeUi.toggle) {
                return;
            }
            const icon = routeUi.toggle.querySelector("i");
            const isCollapsed = routeState.panelCollapsed;
            if (icon) {
                icon.classList.remove("mdi-chevron-left", "mdi-chevron-right");
                icon.classList.add(isCollapsed ? "mdi-chevron-right" : "mdi-chevron-left");
            }
            const label = isCollapsed ? routeUi.expandPanelLabel : routeUi.collapsePanelLabel;
            routeUi.toggle.setAttribute("aria-label", label);
            routeUi.toggle.setAttribute("title", label);
            routeUi.toggle.setAttribute("aria-expanded", isCollapsed ? "false" : "true");
        }

        function setPanelVisibility() {
            const isVisible = Boolean(routeState.start || routeState.end);
            if (routeUi.panel) {
                routeUi.panel.classList.toggle("is-hidden", !isVisible);
                routeUi.panel.classList.toggle("is-collapsed", isVisible && routeState.panelCollapsed);
            }
            if (routeUi.container) {
                routeUi.container.classList.toggle("geoview-map-layout--panel-hidden", !isVisible);
                routeUi.container.classList.toggle(
                    "geoview-map-layout--panel-collapsed",
                    isVisible && routeState.panelCollapsed
                );
            }
            if (!isVisible) {
                routeState.panelCollapsed = false;
            }
            updatePanelToggleButton();
            window.requestAnimationFrame(function () {
                map.invalidateSize();
            });
        }

        function updateRouteButtons() {
            if (routeUi.open) {
                const canCalculate = Boolean(routeState.start && routeState.end);
                routeUi.open.disabled = !canCalculate || routeState.isCalculating;
                routeUi.open.textContent = routeState.isCalculating
                    ? routeUi.calculatingLabel
                    : (routingEnabled ? routeUi.calculateLabel : (config.ui && config.ui.open_google_maps ? config.ui.open_google_maps : routeUi.calculateLabel));
            }
            if (routeUi.clear) {
                routeUi.clear.textContent = routeUi.clearLabel;
            }
            if (routeUi.costing) {
                routeUi.costing.disabled = !routingEnabled || routeState.isCalculating;
            }
        }

        function updateRoutePanel() {
            if (routeUi.start) {
                routeUi.start.textContent = renderRoutePoint(routeState.start, routeUi.notSetLabel);
            }
            if (routeUi.end) {
                routeUi.end.textContent = renderRoutePoint(routeState.end, routeUi.notSetLabel);
            }
            setPanelVisibility();
            updateRouteButtons();
        }

        function resetRouteOutput() {
            setRouteError("");
            setRouteSummary(null, defaultCosting);
            setAlternativeSummary([]);
            if (routingEnabled) {
                clearRouteLines();
            } else {
                updateRouteLine();
            }
        }

        function setRoutePoint(pointType, markerData) {
            if (pointType !== "start" && pointType !== "end") {
                return;
            }
            routeState[pointType] = markerData;
            resetRouteOutput();
            updateRoutePanel();
        }

        function clearRoute() {
            routeState.start = null;
            routeState.end = null;
            resetRouteOutput();
            updateRoutePanel();
        }

        function openRouteInGoogleMaps() {
            if (!routeState.start || !routeState.end) {
                return;
            }
            window.open(buildDirectionsUrl(routeState.start, routeState.end), "_blank", "noopener,noreferrer");
        }

        function setCostingOptions() {
            if (!routeUi.costing) {
                return;
            }
            routeUi.costing.innerHTML = "";
            if (!routingEnabled || costingOptions.length === 0) {
                routeUi.costing.disabled = true;
                return;
            }
            costingOptions.forEach(function (option) {
                const item = document.createElement("option");
                item.value = option;
                item.textContent = costingLabels[option] || option;
                routeUi.costing.appendChild(item);
            });
            routeUi.costing.value = defaultCosting;
            routeUi.costing.disabled = false;
        }

        async function calculateRoute() {
            if (!routeState.start || !routeState.end) {
                return;
            }
            if (!routingEnabled) {
                openRouteInGoogleMaps();
                return;
            }
            const costing = routeUi.costing ? routeUi.costing.value || defaultCosting : defaultCosting;
            const params = new URLSearchParams({
                start_lat: String(routeState.start.latitude),
                start_lon: String(routeState.start.longitude),
                end_lat: String(routeState.end.latitude),
                end_lon: String(routeState.end.longitude),
                costing: costing,
            });
            routeState.isCalculating = true;
            updateRouteButtons();
            setRouteError("");
            try {
                const response = await fetch(`${routingConfig.endpoint}?${params.toString()}`, {
                    method: "GET",
                    headers: {
                        Accept: "application/json",
                    },
                    credentials: "same-origin",
                });
                const payload = await response.json();
                if (!response.ok || !payload || !payload.success) {
                    throw new Error(payload && payload.error ? payload.error : routeUi.routeErrorLabel);
                }
                setRouteSummary(payload.route, payload.costing || costing);
                setAlternativeSummary(payload.alternatives || []);
                drawValhallaRoute(payload.route, payload.alternatives || []);
            } catch (error) {
                setRouteError(error && error.message ? error.message : routeUi.routeErrorLabel);
                clearRouteLines();
                setRouteSummary(null, defaultCosting);
                setAlternativeSummary([]);
            } finally {
                routeState.isCalculating = false;
                updateRouteButtons();
            }
        }

        if (routeUi.open) {
            routeUi.open.addEventListener("click", function () {
                calculateRoute();
            });
        }
        if (routeUi.clear) {
            routeUi.clear.addEventListener("click", clearRoute);
        }
        if (routeUi.toggle) {
            routeUi.toggle.addEventListener("click", function () {
                if (!(routeState.start || routeState.end)) {
                    return;
                }
                routeState.panelCollapsed = !routeState.panelCollapsed;
                setPanelVisibility();
            });
        }

        window.L.control.layers(baseLayers, {}, {
            collapsed: true,
            position: "topright",
        }).addTo(map);

        const markerBounds = addSiteMarkers(map, config, { setPoint: setRoutePoint });
        addRecenterControl(map, config, markerBounds);
        setCostingOptions();
        setRouteSummary(null, defaultCosting);
        updatePanelToggleButton();
        updateRoutePanel();
        element.dataset.geoviewRenderReason = "";
        element.dataset.geoviewRendered = "1";
    }

    document.addEventListener("DOMContentLoaded", function () {
        document.querySelectorAll("[data-geoview-map]").forEach(function (element) {
            try {
                renderMap(element);
            } catch (error) {
                element.dataset.geoviewRenderReason = "render-error";
                element.dataset.geoviewRendered = "0";
                if (window.console && typeof window.console.error === "function") {
                    window.console.error("GeoView map initialization failed", error);
                }
            }
        });
    });
}());
