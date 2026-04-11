function getCsrfToken() {
    return document.querySelector("[name=csrfmiddlewaretoken]")?.value || "";
}

document.body.addEventListener("htmx:configRequest", (event) => {
    const token = getCsrfToken();
    if (token) {
        event.detail.headers["X-CSRFToken"] = token;
    }
});

function initSortables(root = document) {
    root.querySelectorAll("[data-sortable-url]").forEach((element) => {
        if (element.dataset.sortableReady === "1") {
            return;
        }

        Sortable.create(element, {
            animation: 150,
            handle: "[data-drag-handle]",
            onEnd: async () => {
                const order = Array.from(element.querySelectorAll("[data-sortable-id]")).map((item) =>
                    item.getAttribute("data-sortable-id")
                );

                await fetch(element.dataset.sortableUrl, {
                    method: "POST",
                    headers: {
                        "Content-Type": "application/json",
                        "X-CSRFToken": getCsrfToken(),
                    },
                    body: JSON.stringify({ order }),
                });

                if (element.dataset.sortableRefreshUrl && element.dataset.sortableRefreshTarget && window.htmx) {
                    htmx.ajax("GET", element.dataset.sortableRefreshUrl, {
                        target: element.dataset.sortableRefreshTarget,
                        swap: "outerHTML",
                    });
                }
            },
        });

        element.dataset.sortableReady = "1";
    });
}

function syncThemeIcon() {
    const themeIcon = document.querySelector("[data-theme-icon]");
    if (themeIcon) {
        themeIcon.textContent = document.documentElement.classList.contains("dark") ? "☾" : "◐";
    }
}

function initThemeToggle() {
    const themeToggleButton = document.querySelector("[data-theme-toggle]");
    if (!themeToggleButton || themeToggleButton.dataset.themeReady === "1") {
        syncThemeIcon();
        return;
    }

    syncThemeIcon();
    themeToggleButton.addEventListener("click", () => {
        const isDark = document.documentElement.classList.toggle("dark");
        localStorage.setItem("mycourse-theme", isDark ? "dark" : "light");
        syncThemeIcon();
    });
    themeToggleButton.dataset.themeReady = "1";
}

function syncBlockTypeFields(container) {
    const select = container.querySelector('select[name$="block_type"]');
    const currentType = (select?.value || container.dataset.currentBlockType || "").toLowerCase();

    container.querySelectorAll("[data-block-visible-for]").forEach((element) => {
        const allowedTypes = (element.dataset.blockVisibleFor || "")
            .split(",")
            .map((value) => value.trim().toLowerCase())
            .filter(Boolean);

        if (!currentType || allowedTypes.includes(currentType)) {
            element.hidden = false;
        } else {
            element.hidden = true;
        }
    });
}

function initBlockTypeForms(root = document) {
    root.querySelectorAll("[data-block-type-form]").forEach((container) => {
        if (container.dataset.blockTypeReady === "1") {
            syncBlockTypeFields(container);
            return;
        }

        const select = container.querySelector('select[name$="block_type"]');
        if (select) {
            select.addEventListener("change", () => syncBlockTypeFields(container));
        }
        syncBlockTypeFields(container);
        container.dataset.blockTypeReady = "1";
    });
}

function initUi(root = document) {
    initSortables(root);
    initThemeToggle();
    initBlockTypeForms(root);
}

document.addEventListener("DOMContentLoaded", () => initUi(document));
document.body.addEventListener("htmx:afterSwap", (event) => initUi(event.target));
