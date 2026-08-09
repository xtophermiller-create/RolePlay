/**
 * Мои сценарии: create-popup + delete-confirm + inline rename.
 */
(() => {
  const root = document.querySelector("[data-scenarios]");
  if (!root || !window.LifeCorePopup || !window.LifeCoreAsync) return;

  const { postJson, toast } = window.LifeCoreAsync;
  const grid = root.querySelector("[data-scenarios-grid]");
  const createUrl = root.getAttribute("data-api-create") || "";
  const renameTpl = root.getAttribute("data-api-rename") || "";
  const deleteTpl = root.getAttribute("data-api-delete") || "";
  const editTpl = root.getAttribute("data-api-edit") || "";
  const avatarUrl = root.getAttribute("data-avatar-url") || "";

  const popup = document.querySelector("[data-scenario-create-popup]");
  const openBtn = root.querySelector("[data-scenario-create-open]");
  const createInput = popup?.querySelector("[data-scenario-create-input]");
  const splashEl = popup?.querySelector("[data-scenario-create-splash]");
  const emptyBtn = popup?.querySelector("[data-scenario-create-empty]");
  const continueBtn = popup?.querySelector("[data-scenario-create-continue]");

  const deletePopup = document.querySelector("[data-scenario-delete-popup]");
  const deleteNameEl = deletePopup?.querySelector("[data-scenario-delete-name]");
  const deleteConfirmBtn = deletePopup?.querySelector("[data-scenario-delete-confirm]");

  const DELETE_ICON = `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2zm1 6h2v10h-2V9zm4 0h2v10h-2V9zM7 9h2v10H7V9z"/></svg>`;

  const SPLASHES = [
    "Давай создадим новый шедевр, который мы между собой упрощённо называем “сценарий”. Всё почти готово — осталось только дать ему имя и наполнить смыслом. Сущие пустяки ❤️",
    "Ложь ходит быстрее правды. (Томас Шелби)\n\nХороший сценарий 🚬\nИ у тебя крутой получится... продуманный 💪",
    "Сегодня родится не просто диалог, а маленькая дуэль смыслов... И премия 👀",
    "Некоторые мысли невозможно выразить без мата — особенно в хорошем сценарии.",
    "Тут не слова важны, а то, что между ними... и пробелы 🧐",
    "Лучший диалог — тот, где оба говорят, но каждый слышит своё... если только не у тебя в голове 😖",
    "Слабый сценарий объясняет всё заранее. Сильный — заставляет выяснять (отношения).",
    "Создано не для галочки. ✅ < Она у нас уже есть.",
  ];

  const renameUrl = (id) => renameTpl.replace("{id}", String(id));
  const deleteUrl = (id) => deleteTpl.replace("{id}", String(id));
  const editUrl = (id) => editTpl.replace("{id}", String(id));

  const displayTitle = (title) => {
    const t = String(title || "").trim();
    return t || "Без названия";
  };

  const titleButton = (title) => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scenario-card__title";
    btn.dataset.scenarioTitle = "";
    btn.title = "Изменить название";
    const span = document.createElement("span");
    span.className = "scenario-card__title-text";
    span.textContent = displayTitle(title);
    btn.appendChild(span);
    return btn;
  };

  const removeEmptyHint = () => {
    grid?.querySelector("[data-scenarios-empty]")?.remove();
  };

  const ensureEmptyHint = () => {
    if (!grid || grid.querySelector("[data-scenario-card]")) return;
    if (grid.querySelector("[data-scenarios-empty]")) return;
    const empty = document.createElement("div");
    empty.className = "scenarios-empty";
    empty.dataset.scenariosEmpty = "";
    empty.innerHTML =
      `<p class="scenarios-empty__title">Пока пусто</p>` +
      `<p class="scenarios-empty__text">Создай первый сценарий — и библиотека оживёт.</p>`;
    grid.appendChild(empty);
  };

  const buildDeleteButton = () => {
    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "scenario-card__delete";
    btn.dataset.scenarioDelete = "";
    btn.title = "Удалить сценарий";
    btn.setAttribute("aria-label", "Удалить сценарий");
    btn.innerHTML = DELETE_ICON;
    return btn;
  };

  const buildCard = ({ scenario_id, title }) => {
    const card = document.createElement("article");
    card.className = "scenario-card";
    card.dataset.scenarioCard = "";
    card.dataset.scenarioId = String(scenario_id);

    const cover = document.createElement("div");
    cover.className = "scenario-card__cover";
    const img = document.createElement("img");
    img.className = "scenario-card__avatar";
    img.src = avatarUrl;
    img.alt = "";
    img.width = 200;
    img.height = 200;
    img.draggable = false;
    cover.append(img, buildDeleteButton());

    card.append(cover, titleButton(title));
    return card;
  };

  const pickSplash = () => SPLASHES[Math.floor(Math.random() * SPLASHES.length)];

  /* ——— Create popup ——— */

  let createBusy = false;

  const createScenario = async (title, { openEditor = false } = {}) => {
    if (createBusy) return null;
    createBusy = true;
    try {
      const data = await postJson(createUrl, { title: title || "" });
      if (openEditor && data.edit_url) {
        location.href = data.edit_url;
        return data.scenario;
      }
      removeEmptyHint();
      const card = buildCard(data.scenario);
      grid?.prepend(card);
      return data.scenario;
    } catch (err) {
      toast(err.message || "Не удалось создать сценарий", "error");
      return null;
    } finally {
      createBusy = false;
    }
  };

  const openCreate = () => {
    if (!popup || !createInput) return;
    createInput.value = "";
    if (splashEl) splashEl.textContent = pickSplash();
    window.LifeCorePopup.open(popup);
    requestAnimationFrame(() => {
      createInput.focus();
    });
  };

  const closeCreateOnly = () => {
    if (!popup) return;
    window.LifeCorePopup.close(popup);
  };

  /** Закрытие: с названием — создать; без — просто закрыть. */
  const closeCreateAndMaybeSave = async () => {
    if (!popup || !createInput || createBusy) return;
    const title = createInput.value.trim();
    closeCreateOnly();
    if (!title) return;
    await createScenario(title);
  };

  openBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    openCreate();
  });

  popup?.querySelectorAll("[data-scenario-create-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      closeCreateAndMaybeSave();
    });
  });

  emptyBtn?.addEventListener("click", async (event) => {
    event.preventDefault();
    if (createBusy || !createInput) return;
    const title = createInput.value.trim();
    closeCreateOnly();
    await createScenario(title);
  });

  continueBtn?.addEventListener("click", async (event) => {
    event.preventDefault();
    if (createBusy || !createInput) return;
    const title = createInput.value.trim();
    closeCreateOnly();
    await createScenario(title, { openEditor: true });
  });

  createInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      closeCreateAndMaybeSave();
    }
  });

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Escape") return;
      if (deletePopup?.classList.contains("is-open")) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closeDeleteConfirm();
        return;
      }
      if (!popup?.classList.contains("is-open")) return;
      event.preventDefault();
      event.stopImmediatePropagation();
      closeCreateAndMaybeSave();
    },
    true
  );

  /* ——— Delete confirm ——— */

  let pendingDelete = null;
  let deleteBusy = false;

  const openDeleteConfirm = (card) => {
    if (!deletePopup || !card) return;
    const id = card.getAttribute("data-scenario-id");
    if (!id) return;
    const titleText =
      card.querySelector(".scenario-card__title-text")?.textContent?.trim() ||
      "Без названия";
    pendingDelete = { id, card, title: titleText };
    if (deleteNameEl) deleteNameEl.textContent = `«${titleText}»`;
    window.LifeCorePopup.open(deletePopup);
    requestAnimationFrame(() => {
      deleteConfirmBtn?.focus();
    });
  };

  const closeDeleteConfirm = () => {
    if (!deletePopup) return;
    window.LifeCorePopup.close(deletePopup);
    pendingDelete = null;
  };

  const confirmDelete = async () => {
    if (deleteBusy || !pendingDelete || !deleteTpl) return;
    const { id, card } = pendingDelete;
    deleteBusy = true;
    deleteConfirmBtn?.setAttribute("disabled", "true");
    try {
      await postJson(deleteUrl(id), {});
      closeDeleteConfirm();
      card.remove();
      ensureEmptyHint();
      toast("Сценарий удалён", "success");
    } catch (err) {
      toast(err.message || "Не удалось удалить", "error");
    } finally {
      deleteBusy = false;
      deleteConfirmBtn?.removeAttribute("disabled");
    }
  };

  deletePopup?.querySelectorAll("[data-scenario-delete-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      if (deleteBusy) return;
      closeDeleteConfirm();
    });
  });

  deleteConfirmBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    void confirmDelete();
  });

  /* ——— Inline rename ——— */

  const startRename = (titleBtn) => {
    const card = titleBtn.closest("[data-scenario-card]");
    if (!card || card.classList.contains("is-editing")) return;

    const scenarioId = card.getAttribute("data-scenario-id");
    const textEl = titleBtn.querySelector(".scenario-card__title-text") || titleBtn;
    const prev = textEl.textContent.trim();
    const rawPrev = prev === "Без названия" ? "" : prev;

    card.classList.add("is-editing");

    const input = document.createElement("input");
    input.className = "scenario-card__title-input";
    input.type = "text";
    input.maxLength = 200;
    input.value = rawPrev;
    input.setAttribute("aria-label", "Название сценария");
    input.autocomplete = "off";
    input.spellcheck = false;

    titleBtn.replaceWith(input);
    input.focus();
    input.select();

    let finished = false;

    const restore = (text) => {
      input.replaceWith(titleButton(text));
      card.classList.remove("is-editing");
    };

    const finish = async (commit) => {
      if (finished) return;
      finished = true;

      const next = input.value.trim();
      if (!commit || !next || next === rawPrev) {
        restore(rawPrev || prev);
        return;
      }

      restore(next);
      try {
        const data = await postJson(renameUrl(scenarioId), { title: next });
        const btn = card.querySelector("[data-scenario-title]");
        const span = btn?.querySelector(".scenario-card__title-text");
        if (span && data.title) span.textContent = displayTitle(data.title);
      } catch (err) {
        const btn = card.querySelector("[data-scenario-title]");
        const span = btn?.querySelector(".scenario-card__title-text");
        if (span) span.textContent = displayTitle(rawPrev || prev);
        toast(err.message || "Не удалось переименовать", "error");
      }
    };

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        input.blur();
      } else if (event.key === "Escape") {
        event.preventDefault();
        finished = true;
        restore(rawPrev || prev);
      }
    });

    input.addEventListener("blur", () => {
      finish(true);
    });
  };

  grid?.addEventListener("click", (event) => {
    const deleteBtn = event.target.closest("[data-scenario-delete]");
    if (deleteBtn && grid.contains(deleteBtn)) {
      event.preventDefault();
      event.stopPropagation();
      const card = deleteBtn.closest("[data-scenario-card]");
      openDeleteConfirm(card);
      return;
    }

    const titleBtn = event.target.closest("[data-scenario-title]");
    if (titleBtn && grid.contains(titleBtn)) {
      event.preventDefault();
      startRename(titleBtn);
      return;
    }

    const card = event.target.closest("[data-scenario-card]");
    if (!card || !grid.contains(card) || card.classList.contains("is-editing")) return;
    const id = card.getAttribute("data-scenario-id");
    if (!id || !editTpl) return;
    location.href = editUrl(id);
  });
})();
