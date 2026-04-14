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
    if (typeof Sortable === "undefined") {
        return;
    }

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

        element.hidden = !currentType || !allowedTypes.includes(currentType);
        if (!currentType || allowedTypes.includes(currentType)) {
            element.hidden = false;
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

function dismissToast(toast) {
    if (!toast || toast.dataset.dismissing === "1") {
        return;
    }
    toast.dataset.dismissing = "1";
    toast.classList.add("is-leaving");
    window.setTimeout(() => toast.remove(), 220);
}

function initToast(toast) {
    if (!toast || toast.dataset.toastReady === "1") {
        return;
    }

    if (!toast.dataset.toastKey) {
        const text = toast.querySelector(".toast__text")?.textContent?.trim() || "";
        const title = toast.querySelector(".toast__title")?.textContent?.trim() || "";
        toast.dataset.toastKey = `${title}:${text}`;
    }

    const timeout = Number.parseInt(toast.dataset.timeout || "4800", 10);
    const closeButton = toast.querySelector("[data-toast-close]");
    if (closeButton) {
        closeButton.addEventListener("click", () => dismissToast(toast));
    }

    if (timeout > 0) {
        window.setTimeout(() => dismissToast(toast), timeout);
    }

    toast.dataset.toastReady = "1";
}

function initToasts(root = document) {
    root.querySelectorAll("[data-toast]").forEach(initToast);
}

function parseHxTriggerHeader(value) {
    if (!value) {
        return [];
    }

    try {
        const parsed = JSON.parse(value);
        return extractToastMessages(parsed["ui:toast"]);
    } catch (error) {
        console.warn("Failed to parse HX-Trigger header", error);
        return [];
    }
}

function ensureToastContainer() {
    let container = document.querySelector("#toast-container");
    if (!container) {
        container = document.createElement("div");
        container.id = "toast-container";
        container.className = "toast-stack";
        container.dataset.ui = "toast-container";
        container.setAttribute("aria-live", "polite");
        container.setAttribute("aria-atomic", "false");
        document.body.appendChild(container);
    }
    return container;
}

function buildToastElement(message) {
    const toast = document.createElement("article");
    const tone = message.css_class || `alert-${message.tone || "info"}`;
    const titleMap = {
        success: "Готово",
        info: "Уведомление",
        warning: "Внимание",
        danger: "Ошибка",
        neutral: "Сообщение",
    };

    toast.className = `toast ${tone}`;
    toast.dataset.toast = "";
    toast.dataset.timeout = "4800";
    toast.dataset.toastKey = `${message.id || "toast"}:${message.tone || "info"}:${message.text || ""}`;
    toast.tabIndex = 0;
    toast.innerHTML = `
        <div class="toast__body">
            <p class="toast__title">${titleMap[message.tone] || titleMap.info}</p>
            <p class="toast__text"></p>
        </div>
        <button type="button" class="toast__close" data-toast-close aria-label="Закрыть уведомление">&times;</button>
    `;
    toast.querySelector(".toast__text").textContent = message.text || "";
    return toast;
}

function showToastMessages(messages) {
    if (!Array.isArray(messages) || messages.length === 0) {
        return;
    }

    const container = ensureToastContainer();
    messages.forEach((message) => {
        const toastKey = `${message.id || "toast"}:${message.tone || "info"}:${message.text || ""}`;
        if (container.querySelector(`[data-toast-key="${CSS.escape(toastKey)}"]`)) {
            return;
        }
        const toast = buildToastElement(message);
        container.appendChild(toast);
        initToast(toast);
    });
}

function extractToastMessages(detail) {
    if (!detail) {
        return [];
    }
    if (Array.isArray(detail.messages)) {
        return detail.messages;
    }
    if (Array.isArray(detail)) {
        return detail;
    }
    if (detail.text) {
        return [detail];
    }
    return [];
}

let aiDrawerLastTrigger = null;

function getAiDrawerElements() {
    return {
        root: document.querySelector("#ai-drawer-root"),
        panel: document.querySelector("#ai-drawer-root .ai-drawer__panel"),
        content: document.querySelector("#ai-drawer-content"),
        title: document.querySelector("#ai-drawer-title"),
    };
}

function focusAiDrawerField() {
    const { content } = getAiDrawerElements();
    const field = content?.querySelector("textarea, input");
    if (field) {
        field.focus();
    }
}

function scrollAiHistoryToEnd() {
    const history = document.querySelector("[data-ui='ai-chat-history']");
    if (history) {
        history.scrollTop = history.scrollHeight;
    }
}

function openAiDrawer(trigger) {
    const { root, panel, content, title } = getAiDrawerElements();
    if (!root || !panel || !content) {
        return;
    }

    aiDrawerLastTrigger = trigger || null;
    const url = trigger?.dataset.aiDrawerUrl;
    const panelTitle = trigger?.dataset.aiDrawerTitle || "Помощник по курсу";

    root.hidden = false;
    root.removeAttribute("hidden");
    root.setAttribute("aria-hidden", "false");
    root.classList.add("is-open");
    document.body.classList.add("drawer-open");

    if (title) {
        title.textContent = panelTitle;
    }

    if (url && window.htmx && !trigger?.hasAttribute("hx-get")) {
        content.innerHTML = `
            <div class="surface-muted ai-drawer__loading" data-ui="ai-drawer-loading">
                <p class="font-semibold">Подгружаем помощника…</p>
                <p class="muted-text mt-2">Собираем контекст курса и готовим панель вопросов.</p>
            </div>
        `;
        htmx.ajax("GET", url, {
            target: "#ai-drawer-content",
            swap: "innerHTML",
        });
    } else if (!window.htmx && url) {
        content.innerHTML = `
            <div class="alert alert-warning">
                <div>
                    <p class="font-semibold">Не удалось загрузить панель ИИ</p>
                    <p class="mt-2">В браузере не подключился HTMX, поэтому содержимое панели не подгрузилось.</p>
                </div>
            </div>
        `;
    }

    window.requestAnimationFrame(() => panel.focus());
}

function closeAiDrawer() {
    const { root } = getAiDrawerElements();
    if (!root) {
        return;
    }

    root.classList.remove("is-open");
    root.setAttribute("aria-hidden", "true");
    document.body.classList.remove("drawer-open");
    window.setTimeout(() => {
        if (!root.classList.contains("is-open")) {
            root.hidden = true;
        }
    }, 220);

    if (aiDrawerLastTrigger) {
        aiDrawerLastTrigger.focus();
    }
}

function initAiDrawer() {
    if (document.body.dataset.aiDrawerReady === "1") {
        return;
    }

    document.addEventListener("click", (event) => {
        const openButton = event.target.closest("[data-ai-drawer-open]");
        if (openButton) {
            event.preventDefault();
            openAiDrawer(openButton);
            return;
        }

        const closeButton = event.target.closest("[data-ai-drawer-close]");
        if (closeButton) {
            event.preventDefault();
            closeAiDrawer();
        }
    });

    document.addEventListener("keydown", (event) => {
        if (event.key === "Escape" && document.querySelector("#ai-drawer-root.is-open")) {
            closeAiDrawer();
        }
    });

    document.body.dataset.aiDrawerReady = "1";
}

function initToastObserver() {
    if (document.body.dataset.toastObserverReady === "1") {
        return;
    }

    const container = ensureToastContainer();
    const observer = new MutationObserver(() => {
        initToasts(container);
    });
    observer.observe(container, { childList: true, subtree: true });
    document.body.dataset.toastObserverReady = "1";
}

function initUi(root = document) {
    try {
        initSortables(root);
    } catch (error) {
        console.error("Sortable initialization failed", error);
    }
    try {
        initThemeToggle();
    } catch (error) {
        console.error("Theme toggle initialization failed", error);
    }
    try {
        initBlockTypeForms(root);
    } catch (error) {
        console.error("Block type form initialization failed", error);
    }
    try {
        initToasts(root);
    } catch (error) {
        console.error("Toast initialization failed", error);
    }
    try {
        initToastObserver();
    } catch (error) {
        console.error("Toast observer initialization failed", error);
    }
    try {
        initAiDrawer();
    } catch (error) {
        console.error("AI drawer initialization failed", error);
    }
}

window.MyCourseUI = {
    openAiDrawer,
    closeAiDrawer,
    showToastMessages,
};

if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => initUi(document));
} else {
    initUi(document);
}

document.body.addEventListener("htmx:afterSwap", (event) => {
    initUi(event.target);
    const target = event.detail.target;
    if (target?.id === "ai-drawer-content") {
        focusAiDrawerField();
        scrollAiHistoryToEnd();
    }
});

document.body.addEventListener("htmx:afterRequest", (event) => {
    const xhr = event.detail.xhr;
    if (!xhr) {
        return;
    }
    const headerMessages = [
        ...parseHxTriggerHeader(xhr.getResponseHeader("HX-Trigger")),
        ...parseHxTriggerHeader(xhr.getResponseHeader("HX-Trigger-After-Swap")),
        ...parseHxTriggerHeader(xhr.getResponseHeader("HX-Trigger-After-Settle")),
    ];
    if (headerMessages.length) {
        showToastMessages(headerMessages);
    }
});

document.addEventListener("ui:toast", (event) => {
    showToastMessages(extractToastMessages(event.detail));
});
