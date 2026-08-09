/**
 * Панель выбора смайликов для текстовых полей.
 * window.LifeCoreEmojiPicker.bind(trigger, input)
 * window.LifeCoreEmojiPicker.bindAll(root?)
 */
(() => {
  const EMOJIS = [
    "😀", "😃", "😄", "😁", "😆", "😅", "😂", "🤣", "😊", "😇",
    "🙂", "😉", "😌", "😍", "🥰", "😘", "😗", "😙", "😚", "😋",
    "😛", "😜", "🤪", "😝", "🤑", "🤗", "🤭", "🤫", "🤔", "🤐",
    "🤨", "😐", "😑", "😶", "😏", "😒", "🙄", "😬", "😮‍💨", "🤥",
    "😌", "😔", "😪", "🤤", "😴", "😷", "🤒", "🤕", "🤢", "🤮",
    "🥵", "🥶", "🥴", "😵", "🤯", "🤠", "🥳", "😎", "🤓", "🧐",
    "👍", "👎", "👏", "🙌", "🤝", "✌️", "🤞", "🤟", "🤘", "👌",
    "💪", "🙏", "💯", "🔥", "⭐", "🌟", "✨", "💫", "🎉", "🎊",
    "❤️", "🧡", "💛", "💚", "💙", "💜", "🖤", "🤍", "💔", "❣️",
    "💕", "💞", "💓", "💗", "💖", "💘", "💝", "🏠", "🏢", "🏫",
    "💼", "💻", "📱", "☎️", "📧", "📝", "📌", "📍", "🗂️", "📁",
    "📂", "🏷️", "🔑", "🔒", "🔓", "🛠️", "⚙️", "🧭", "🎯", "🚀",
    "✈️", "🚗", "🏃", "☕", "🍕", "🍔", "🍎", "🎂", "🎁", "🛒",
    "💰", "💳", "📈", "📉", "🔔", "🔕", "💡", "✅", "❌", "⚠️",
    "❓", "❗", "💬", "💭", "🕒", "📅", "🗓️", "👪", "👥", "👤",
  ];

  let openPanel = null;
  let openTrigger = null;

  const closeOpen = () => {
    if (openPanel) {
      openPanel.hidden = true;
      openPanel = null;
    }
    if (openTrigger) {
      openTrigger.setAttribute("aria-expanded", "false");
      openTrigger = null;
    }
  };

  const insertAtCursor = (input, text) => {
    const start = input.selectionStart ?? input.value.length;
    const end = input.selectionEnd ?? input.value.length;
    const value = input.value;
    input.value = value.slice(0, start) + text + value.slice(end);
    const pos = start + [...text].length;
    try {
      input.setSelectionRange(pos, pos);
    } catch (_) {
      /* ignore */
    }
    input.dispatchEvent(new Event("input", { bubbles: true }));
    input.focus();
  };

  /** Хост с position:relative — combo целиком, не __field (у compact там overflow clip). */
  const panelHost = (trigger) =>
    trigger.closest(".task-contact-combo") || trigger.parentElement;

  const ensurePanel = (trigger) => {
    const host = panelHost(trigger);
    let panel = host?.querySelector(":scope > .emoji-picker");
    if (panel) return panel;

    panel = document.createElement("div");
    panel.className = "emoji-picker";
    panel.hidden = true;
    panel.setAttribute("role", "listbox");
    panel.setAttribute("aria-label", "Смайлики");

    const grid = document.createElement("div");
    grid.className = "emoji-picker__grid";
    EMOJIS.forEach((emoji) => {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "emoji-picker__btn";
      btn.textContent = emoji;
      btn.setAttribute("aria-label", emoji);
      btn.addEventListener("mousedown", (event) => {
        event.preventDefault();
        event.stopPropagation();
      });
      btn.addEventListener("click", (event) => {
        event.preventDefault();
        event.stopPropagation();
        const input = trigger._emojiInput;
        if (input) insertAtCursor(input, emoji);
        closeOpen();
      });
      grid.appendChild(btn);
    });
    panel.appendChild(grid);

    if (host) {
      if (getComputedStyle(host).position === "static") {
        host.style.position = "relative";
      }
      host.appendChild(panel);
    }
    return panel;
  };

  const bind = (trigger, input) => {
    if (!trigger || !input || trigger.dataset.emojiBound === "1") return null;
    trigger.dataset.emojiBound = "1";
    trigger._emojiInput = input;
    trigger.setAttribute("aria-haspopup", "dialog");
    trigger.setAttribute("aria-expanded", "false");

    trigger.addEventListener("mousedown", (event) => {
      event.preventDefault();
      event.stopPropagation();
    });

    trigger.addEventListener("click", (event) => {
      event.preventDefault();
      event.stopPropagation();
      const panel = ensurePanel(trigger);
      const willOpen = panel.hidden;
      closeOpen();
      if (!willOpen) return;
      panel.hidden = false;
      openPanel = panel;
      openTrigger = trigger;
      trigger.setAttribute("aria-expanded", "true");
    });

    return { close: closeOpen };
  };

  const bindAll = (root = document) => {
    root.querySelectorAll("[data-emoji-trigger]").forEach((trigger) => {
      if (trigger.dataset.emojiBound === "1") return;
      const field =
        trigger.closest(".task-contact-combo__field") || trigger.parentElement;
      const input =
        field?.querySelector(
          "[data-emoji-target], .task-contact-combo__search, input[type='text']"
        ) || null;
      if (input) bind(trigger, input);
    });
  };

  document.addEventListener("click", (event) => {
    if (!openPanel) return;
    if (event.target.closest(".emoji-picker")) return;
    if (event.target.closest("[data-emoji-trigger]")) return;
    closeOpen();
  });

  document.addEventListener("keydown", (event) => {
    if (event.key === "Escape") closeOpen();
  });

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", () => bindAll());
  } else {
    bindAll();
  }

  window.LifeCoreEmojiPicker = { bind, bindAll, close: closeOpen };
})();
