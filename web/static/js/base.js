(() => {
  const id = document.body.getAttribute("data-filter-nav") || location.pathname;
  window.addEventListener("pagehide", () => {
    try {
      sessionStorage.setItem("lc-filter-last-path", id);
    } catch (_) {
      // Storage may be unavailable in privacy modes.
    }
  });
})();
