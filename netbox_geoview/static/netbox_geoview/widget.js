(function () {
    if (window.GeoViewWidgets) {
        window.GeoViewWidgets.init(document);
        return;
    }
    const instances = new WeakMap();
    let assets;

    function script(src) {
        return new Promise(function (resolve, reject) {
            const element = document.createElement("script");
            element.src = src;
            element.onload = resolve;
            element.onerror = reject;
            document.head.appendChild(element);
        });
    }

    function loadAssets(root) {
        if (!assets) {
            assets = (async function () {
                const styles = [];
                for (const href of [root.dataset.leafletCss, root.dataset.geoviewCss]) {
                    if (!Array.from(document.querySelectorAll('link[rel="stylesheet"]')).some(link => link.href === new URL(href, location.href).href)) {
                        const link = document.createElement("link");
                        link.rel = "stylesheet";
                        link.href = href;
                        styles.push(new Promise(function (resolve, reject) {
                            link.onload = resolve;
                            link.onerror = reject;
                        }));
                        document.head.appendChild(link);
                    }
                }
                await Promise.all(styles);
                if (!window.L) await script(root.dataset.leafletJs);
                if (!window.GeoView) await script(root.dataset.geoviewJs);
            }()).catch(function (error) { assets = null; throw error; });
        }
        return assets;
    }

    function init(context) {
        const roots = Array.from(context.querySelectorAll("[data-geoview-widget]"));
        if (context.matches && context.matches("[data-geoview-widget]")) roots.unshift(context);
        roots.forEach(function (root) {
            if (instances.has(root)) return;
            const status = root.querySelector("[data-geoview-status]");
            const element = root.querySelector("[data-geoview-widget-map]");
            const open = root.querySelector("[data-geoview-open]");
            const refresh = root.querySelector("[data-geoview-refresh]");
            const state = {controller: null};
            instances.set(root, state);

            async function load() {
                if (state.controller) state.controller.abort();
                const controller = new AbortController();
                state.controller = controller;
                status.textContent = root.dataset.loading;
                refresh.disabled = true;
                open.classList.add("d-none");
                if (window.GeoView) window.GeoView.destroy(element);
                delete element.dataset.geoviewMap;
                delete element.dataset.configId;
                element.replaceChildren();
                const configId = "geoview-widget-config-" + root.dataset.geoviewWidget;
                const previousConfig = document.getElementById(configId);
                if (previousConfig) previousConfig.remove();
                try {
                    await loadAssets(root);
                    const response = await fetch(root.dataset.url, {credentials: "same-origin", cache: "no-store", signal: controller.signal});
                    if (!response.ok || response.redirected) throw new Error("Map unavailable");
                    const data = await response.json();
                    if (controller.signal.aborted || !root.isConnected) return;
                    const config = document.createElement("script");
                    config.type = "application/json";
                    config.id = configId;
                    config.textContent = JSON.stringify(data.config);
                    root.appendChild(config);
                    element.dataset.geoviewMap = "";
                    element.dataset.configId = configId;
                    window.GeoView.init(element);
                    if (element.dataset.geoviewRendered !== "1") throw new Error("Map initialization failed");
                    status.textContent = data.config.site_markers.length ? "" : root.dataset.empty;
                    open.href = data.map_url;
                    open.classList.remove("d-none");
                } catch (error) {
                    if (!controller.signal.aborted) status.textContent = root.dataset.error;
                } finally {
                    if (state.controller === controller) refresh.disabled = false;
                }
            }
            refresh.addEventListener("click", load);
            load();
        });
    }

    window.GeoViewWidgets = {init: init};
    document.addEventListener("htmx:load", event => init(event.detail.elt));
    document.addEventListener("htmx:beforeCleanupElement", function (event) {
        const context = event.detail.elt;
        const roots = Array.from(context.querySelectorAll("[data-geoview-widget]"));
        if (context.matches("[data-geoview-widget]")) roots.push(context);
        roots.forEach(function (root) {
            const state = instances.get(root);
            if (state && state.controller) state.controller.abort();
            instances.delete(root);
        });
    });
    if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", () => init(document));
    else init(document);
}());
