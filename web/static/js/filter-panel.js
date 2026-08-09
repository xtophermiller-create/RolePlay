/**
 * Сворачиваемая панель фильтров.
 * Состояние open/closed статично в рамках страницы (sessionStorage):
 * переживает reload той же страницы; сбрасывается при уходе на другую.
 * window.LifeCoreFilterPanel.bind(root) → { open, close, setOpen, isOpen, setActive }
 */
(() => {
  const LAST_PATH_KEY = "lc-filter-last-path";

  const storageKey = (id) => `lc-filter-open:${id}`;

  const pageId = (root) =>
    root.getAttribute("data-filter-persist") ||
    document.body?.getAttribute("data-filter-nav") ||
    window.location.pathname ||
    "default";

  const readOpen = (id) => {
    try {
      return sessionStorage.getItem(storageKey(id)) === "1";
    } catch (_) {
      return false;
    }
  };

  const writeOpen = (id, open) => {
    try {
      sessionStorage.setItem(storageKey(id), open ? "1" : "0");
    } catch (_) {
      /* private mode / quota */
    }
  };

  /** Предыдущая страница записана в pagehide; reload → тот же id. */
  const stayedOnPage = (id) => {
    try {
      return sessionStorage.getItem(LAST_PATH_KEY) === id;
    } catch (_) {
      return false;
    }
  };

  const bind = (root) => {
    if (!root) return null;
    const toggle = root.querySelector("[data-filter-toggle]");
    const id = pageId(root);

    const setOpen = (open, { persist = true, animate = true } = {}) => {
      const next = Boolean(open);
      if (!animate) root.classList.add("is-static");
      root.classList.toggle("is-open", next);
      toggle?.setAttribute("aria-expanded", next ? "true" : "false");
      if (persist) writeOpen(id, next);
      if (!animate) {
        requestAnimationFrame(() => {
          requestAnimationFrame(() => root.classList.remove("is-static"));
        });
      }
    };

    const setActive = (active) => {
      root.classList.toggle("is-active", Boolean(active));
    };

    // Reload той же страницы → восстановить; переход с другой → закрыт.
    const samePage = stayedOnPage(id);
    const initialOpen = samePage ? readOpen(id) : false;
    if (!samePage) writeOpen(id, false);
    setOpen(initialOpen, { persist: true, animate: false });

    toggle?.addEventListener("click", () => {
      setOpen(!root.classList.contains("is-open"));
    });

    return {
      open: () => setOpen(true),
      close: () => setOpen(false),
      setOpen: (open) => setOpen(open),
      isOpen: () => root.classList.contains("is-open"),
      setActive,
    };
  };

  window.LifeCoreFilterPanel = { bind };
})();
