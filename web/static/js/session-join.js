/**
 * Присоединение по ключу + входящие приглашения.
 */
(() => {
  const root = document.querySelector("[data-session-join]");
  if (!root || !window.LifeCoreAsync) return;

  const { postJson, getJson, toast } = window.LifeCoreAsync;
  const isGuest = root.getAttribute("data-is-guest") === "1";
  const joinUrl = root.getAttribute("data-api-join") || "";
  const invitesUrl = root.getAttribute("data-api-invites") || "";
  const acceptTpl = root.getAttribute("data-api-accept") || "";
  const declineTpl = root.getAttribute("data-api-decline") || "";
  const lobbyTpl = root.getAttribute("data-api-lobby") || "";

  const codeInput = root.querySelector("[data-session-join-code]");
  const submitBtn = root.querySelector("[data-session-join-submit]");
  const list = root.querySelector("[data-session-invites]");

  const lobbyUrl = (id) => lobbyTpl.replace("{id}", String(id));
  const acceptUrl = (id) => acceptTpl.replace("{id}", String(id));
  const declineUrl = (id) => declineTpl.replace("{id}", String(id));

  let joinBusy = false;

  const goLobby = (data) => {
    const url = data.lobby_url || lobbyUrl(data.session?.session_id);
    if (!url) throw new Error("Не удалось открыть лобби");
    location.href = url;
  };

  const joinByCode = async () => {
    if (joinBusy || !joinUrl || !codeInput) return;
    const code = (codeInput.value || "").trim();
    if (!code) {
      toast("Введите ключ сессии", "error");
      return;
    }
    joinBusy = true;
    submitBtn?.setAttribute("disabled", "true");
    try {
      const data = await postJson(joinUrl, { code });
      goLobby(data);
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        location.href = "/sessions/join";
        return;
      }
      toast(err.message || "Не удалось присоединиться", "error");
      joinBusy = false;
      submitBtn?.removeAttribute("disabled");
    }
  };

  submitBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    void joinByCode();
  });

  codeInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void joinByCode();
    }
  });

  const deadlineMs = (inv) => {
    // Предпочитаем ttl_seconds с сервера — не зависит от часового пояса клиента.
    const ttl = Number(inv?.ttl_seconds);
    if (Number.isFinite(ttl) && ttl >= 0) {
      return Date.now() + ttl * 1000;
    }
    const raw = String(inv?.expires_at || "");
    if (!raw) return 0;
    const normalized = /Z$|[+-]\d{2}:?\d{2}$/.test(raw) ? raw : `${raw}Z`;
    const end = Date.parse(normalized);
    return Number.isFinite(end) ? end : 0;
  };

  const formatTtlFromDeadline = (deadline) => {
    const end = Number(deadline) || 0;
    if (!end) return "";
    const sec = Math.max(0, Math.ceil((end - Date.now()) / 1000));
    return `${sec}с`;
  };

  const ensureEmpty = () => {
    if (!list) return;
    if (list.querySelector("[data-session-invite]")) {
      list.querySelector("[data-session-invites-empty]")?.remove();
      return;
    }
    if (!list.querySelector("[data-session-invites-empty]")) {
      const empty = document.createElement("p");
      empty.className = "session-join__empty";
      empty.dataset.sessionInvitesEmpty = "";
      empty.textContent = "Активных приглашений нет";
      list.appendChild(empty);
    }
  };

  const renderInvite = (inv) => {
    const article = document.createElement("article");
    article.className = "session-invite";
    article.dataset.sessionInvite = "";
    article.dataset.inviteId = String(inv.invite_id);
    article.innerHTML = `
      <div class="session-invite__body">
        <p class="session-invite__from"></p>
        <p class="session-invite__meta">
          <span data-invite-scenario></span>
          <span class="session-invite__code" data-invite-code></span>
        </p>
        <p class="session-invite__ttl" data-invite-ttl></p>
      </div>
      <div class="session-invite__actions">
        <button type="button" class="btn btn--pill" data-invite-decline>Отклонить</button>
        <button type="button" class="btn btn--accent btn--pill" data-invite-accept>Принять</button>
      </div>
    `;
    article.querySelector(".session-invite__from").textContent = inv.from_nickname || "Игрок";
    article.querySelector("[data-invite-scenario]").textContent = inv.scenario_title || "Сценарий";
    article.querySelector("[data-invite-code]").textContent = inv.session_code || "";
    const ttlEl = article.querySelector("[data-invite-ttl]");
    const deadline = deadlineMs(inv);
    ttlEl.dataset.deadline = String(deadline);
    ttlEl.textContent = formatTtlFromDeadline(deadline);
    return article;
  };

  const syncInvites = async () => {
    if (isGuest || !invitesUrl || !list || !getJson) return;
    try {
      const data = await getJson(invitesUrl);
      const invites = Array.isArray(data.invites) ? data.invites : [];
      const prevFocus = document.activeElement?.getAttribute?.("data-invite-id");
      list.replaceChildren();
      if (!invites.length) {
        ensureEmpty();
        return;
      }
      invites.forEach((inv) => list.appendChild(renderInvite(inv)));
      if (prevFocus) {
        list.querySelector(`[data-invite-id="${prevFocus}"]`)?.querySelector("button")?.focus();
      }
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        location.href = "/sessions/join";
      }
    }
  };

  list?.addEventListener("click", async (event) => {
    const acceptBtn = event.target.closest("[data-invite-accept]");
    const declineBtn = event.target.closest("[data-invite-decline]");
    const card = event.target.closest("[data-session-invite]");
    if (!card) return;
    const id = card.getAttribute("data-invite-id");
    if (!id) return;

    if (acceptBtn) {
      event.preventDefault();
      acceptBtn.disabled = true;
      try {
        const data = await postJson(acceptUrl(id), {});
        goLobby(data);
      } catch (err) {
        toast(err.message || "Не удалось принять", "error");
        acceptBtn.disabled = false;
        void syncInvites();
      }
      return;
    }

    if (declineBtn) {
      event.preventDefault();
      declineBtn.disabled = true;
      try {
        await postJson(declineUrl(id), {});
        card.remove();
        ensureEmpty();
      } catch (err) {
        toast(err.message || "Не удалось отклонить", "error");
        declineBtn.disabled = false;
      }
    }
  });

  const tickTtl = () => {
    list?.querySelectorAll("[data-invite-ttl]").forEach((el) => {
      const text = formatTtlFromDeadline(el.dataset.deadline);
      el.textContent = text;
      if (text === "0с") el.closest("[data-session-invite]")?.remove();
    });
    ensureEmpty();
  };

  // SSR-карточки: зафиксировать deadline по ttl_seconds с сервера.
  list?.querySelectorAll("[data-invite-ttl]").forEach((el) => {
    if (el.dataset.deadline) return;
    const ttl = Number(el.dataset.ttlSeconds);
    if (Number.isFinite(ttl) && ttl >= 0) {
      el.dataset.deadline = String(Date.now() + ttl * 1000);
    }
  });

  if (!isGuest) {
    window.setInterval(tickTtl, 1000);
    window.setInterval(() => {
      void syncInvites();
    }, 4000);
  }
})();
