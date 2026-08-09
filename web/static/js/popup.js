/**
 * Единый open/close для модалок Life Core.
 * window.LifeCorePopup.open(el) / .close(el) / .snapClose(el)
 *
 * Разметка: корень .lc-popup (+ модификаторы), внутри *__backdrop / *__panel.
 * Анимация: класс .is-open (см. app.css).
 */
(() => {
  const CLOSING = new WeakSet();

  const durationMs = () => {
    const raw = getComputedStyle(document.documentElement)
      .getPropertyValue("--dur-ui")
      .trim();
    const m = raw.match(/^([\d.]+)(ms|s)?$/);
    if (!m) return 200;
    const n = parseFloat(m[1]);
    return m[2] === "ms" ? n : n * 1000;
  };

  const syncBodyLock = () => {
    const anyOpen = document.querySelector(".lc-popup.is-open");
    document.body.style.overflow = anyOpen ? "hidden" : "";
  };

  const open = (el) => {
    if (!el) return;
    CLOSING.delete(el);
    el.hidden = false;
    el.setAttribute("aria-hidden", "false");
    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        el.classList.add("is-open");
        syncBodyLock();
      });
    });
  };

  /** Мгновенно без анимации (смена view↔edit). */
  const snapClose = (el) => {
    if (!el) return;
    CLOSING.delete(el);
    el.classList.remove("is-open");
    el.hidden = true;
    el.setAttribute("aria-hidden", "true");
    syncBodyLock();
  };

  const close = (el) => {
    if (!el || CLOSING.has(el)) return;
    if (el.hidden && !el.classList.contains("is-open")) return;

    CLOSING.add(el);
    el.classList.remove("is-open");
    el.setAttribute("aria-hidden", "true");
    syncBodyLock();

    const finish = () => {
      if (!CLOSING.has(el)) return;
      CLOSING.delete(el);
      el.hidden = true;
      syncBodyLock();
    };

    const panel =
      el.querySelector(".lc-popup__panel") ||
      el.querySelector("[class$='__panel']") ||
      el;
    let done = false;
    const onEnd = (event) => {
      if (event.target !== panel && event.target !== el) return;
      if (done) return;
      done = true;
      panel.removeEventListener("transitionend", onEnd);
      finish();
    };
    panel.addEventListener("transitionend", onEnd);
    window.setTimeout(() => {
      if (done) return;
      done = true;
      panel.removeEventListener("transitionend", onEnd);
      finish();
    }, durationMs() + 80);
  };

  document.addEventListener("keydown", (event) => {
    if (event.key !== "Escape") return;
    const openPopups = [...document.querySelectorAll(".lc-popup.is-open")];
    if (!openPopups.length) return;
    event.stopPropagation();
    close(openPopups[openPopups.length - 1]);
  });

  window.LifeCorePopup = { open, close, snapClose, syncBodyLock };
})();
