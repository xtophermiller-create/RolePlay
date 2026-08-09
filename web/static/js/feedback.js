(() => {
  const popup = document.querySelector("[data-feedback-popup]");
  const openBtn = document.querySelector("[data-feedback-open]");
  if (!popup || !openBtn || !window.LifeCorePopup) return;

  const setOpen = (open) => {
    if (open) window.LifeCorePopup.open(popup);
    else window.LifeCorePopup.close(popup);
    openBtn.setAttribute("aria-expanded", open ? "true" : "false");
  };

  openBtn.setAttribute("aria-expanded", "false");

  openBtn.addEventListener("click", (event) => {
    event.preventDefault();
    setOpen(true);
  });

  popup.querySelectorAll("[data-feedback-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      setOpen(false);
    });
  });
})();
