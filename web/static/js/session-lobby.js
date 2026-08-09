/**
 * Лобби: карточки участников + компактный выбор ролей.
 */
(() => {
  const root = document.querySelector("[data-session-lobby]");
  const bootEl = document.getElementById("session-lobby-bootstrap");
  if (!root || !bootEl || !window.LifeCoreAsync) return;

  const { postJson, getJson, toast } = window.LifeCoreAsync;
  const seatsEl = root.querySelector("[data-lobby-seats]");
  const rolesEl = root.querySelector("[data-lobby-roles]");
  const codeEl = root.querySelector("[data-lobby-code]");
  const statusEl = root.querySelector("[data-lobby-status]");
  const titleEl = root.querySelector("[data-lobby-title]");
  const copyBtn = root.querySelector("[data-lobby-copy]");
  const startBtn = root.querySelector("[data-lobby-start]");

  const getUrl = root.getAttribute("data-api-get") || "";
  const pingUrl = root.getAttribute("data-api-ping") || "";
  const roleUrl = root.getAttribute("data-api-role") || "";
  const startUrl = root.getAttribute("data-api-start") || "";
  const playPageUrl = root.getAttribute("data-api-play-page") || "";
  const cancelUrl = root.getAttribute("data-api-cancel") || "";
  const leaveUrl = root.getAttribute("data-api-leave") || "";
  const homeUrl = root.getAttribute("data-api-home") || "/home/";
  const joinUrl = root.getAttribute("data-api-join") || "/sessions/join";
  const defaultAvatar = root.getAttribute("data-default-avatar") || "";
  const crownUrl = root.getAttribute("data-crown-url") || "";
  const currentUserId = Number(root.getAttribute("data-current-user-id"));
  const isHost = root.getAttribute("data-is-host") === "1";
  const isGuest = root.getAttribute("data-is-guest") === "1";
  const backLink = root.querySelector("[data-lobby-back]");

  const bounceGuest = () => {
    departed = true;
    location.href = joinUrl || homeUrl;
  };

  const ROLE_ORDER = ["actor1", "actor2", "observer"];
  const ACTOR_ROLES = new Set(["actor1", "actor2"]);
  const PING_MS = 4000;

  let departed = false;
  let state;
  try {
    state = JSON.parse(bootEl.textContent || "{}");
  } catch (_) {
    toast("Не удалось загрузить лобби", "error");
    return;
  }

  const roleLabels = {
    actor1: root.getAttribute("data-role-actor1") || state.role_labels?.actor1 || "Роль 1",
    actor2: root.getAttribute("data-role-actor2") || state.role_labels?.actor2 || "Роль 2",
    observer: root.getAttribute("data-role-observer") || state.role_labels?.observer || "Наблюдатель",
  };

  const STATUS_LABEL = {
    lobby: "Лобби",
    started: "Подготовка",
    active: "Подготовка",
    ready: "Идёт",
    finished: "Завершена",
    cancelled: "Отменена",
  };

  const escapeHtml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const displayName = (p) => p?.nickname || p?.login || "Игрок";

  const participants = (session) =>
    Array.isArray(session?.participants) ? session.participants : [];

  const me = (session) =>
    participants(session).find((p) => p.user_id === currentUserId) || null;

  const rolesReady = (session) => {
    const counts = { actor1: 0, actor2: 0 };
    participants(session).forEach((p) => {
      if (p.role in counts) counts[p.role] += 1;
    });
    return counts.actor1 === 1 && counts.actor2 === 1;
  };

  const buildPeople = (session) => {
    const list = participants(session).slice().sort((a, b) => {
      const aHost = a.user_id === session.host_user_id ? 0 : 1;
      const bHost = b.user_id === session.host_user_id ? 0 : 1;
      if (aHost !== bHost) return aHost - bHost;
      return String(a.joined_at || "").localeCompare(String(b.joined_at || ""));
    });
    return list.map((p) => ({
      key: String(p.user_id),
      participant: p,
      host: p.user_id === session.host_user_id,
    }));
  };

  const renderPerson = (seat) => {
    const el = document.createElement("article");
    el.className = "session-seat" + (seat.host ? " session-seat--host" : "");
    el.dataset.seat = seat.key;
    const p = seat.participant;
    const name = displayName(p);
    const avatar = p.avatar_url || defaultAvatar;
    const roleHint = p.role ? roleLabels[p.role] || p.role : "Наблюдатель";

    el.innerHTML = `
      ${seat.host && crownUrl ? `<img class="session-seat__crown" src="${escapeHtml(crownUrl)}" alt="" width="42" height="24" draggable="false">` : ""}
      <div class="session-seat__avatar-wrap">
        <img class="session-seat__avatar" src="${escapeHtml(avatar)}" alt="" width="88" height="88" draggable="false">
      </div>
      <p class="session-seat__name" title="${escapeHtml(name)}">${escapeHtml(name)}</p>
      <p class="session-seat__hint">${escapeHtml(roleHint)}</p>
    `;
    return el;
  };

  const renderRoleCard = (roleKey, session) => {
    const el = document.createElement("article");
    el.className = "session-role";
    el.dataset.roleCard = roleKey;

    const chosen = participants(session).filter((p) => p.role === roleKey);
    const self = me(session);
    const mine = self?.role === roleKey;
    const open = session.status === "lobby";
    const isActorSlot = ACTOR_ROLES.has(roleKey);
    const takenByOther = isActorSlot && chosen.some((p) => p.user_id !== currentUserId);
    const canTake = open && self && !mine && !takenByOther;

    const avatars = chosen
      .map((p) => {
        const src = escapeHtml(p.avatar_url || defaultAvatar);
        const title = escapeHtml(displayName(p));
        return `<img class="session-role__avatar${p.user_id === currentUserId ? " is-me" : ""}" src="${src}" alt="" title="${title}" width="36" height="36" draggable="false">`;
      })
      .join("");

    const countHint =
      roleKey === "observer" && chosen.length
        ? `<span class="session-role__count">${chosen.length}</span>`
        : "";

    el.innerHTML = `
      <p class="session-role__name">${escapeHtml(roleLabels[roleKey] || roleKey)}${countHint}</p>
      <div class="session-role__avatars" data-role-avatars>
        ${avatars || `<span class="session-role__empty">Никого</span>`}
      </div>
      <button
        type="button"
        class="btn btn--pill session-role__take${mine ? " is-current" : ""}"
        data-take-role="${roleKey}"
        ${canTake || mine ? "" : "disabled"}
        ${mine ? "disabled" : ""}
      >${mine ? "Выбрано" : takenByOther ? "Занято" : "Занять"}</button>
    `;

    if (isActorSlot && chosen.length === 1) el.classList.add("is-ready");
    if (isActorSlot && chosen.length > 1) el.classList.add("is-conflict");
    if (!isActorSlot && chosen.length) el.classList.add("is-ready");
    return el;
  };

  const render = () => {
    const session = state.session;
    if (!session) return;

    if (titleEl) titleEl.textContent = session.scenario_title || "Сессия";
    if (codeEl) codeEl.textContent = session.code || "";
    if (statusEl) statusEl.textContent = STATUS_LABEL[session.status] || session.status;

    if (seatsEl) {
      seatsEl.replaceChildren();
      buildPeople(session).forEach((seat) => seatsEl.appendChild(renderPerson(seat)));
    }

    if (rolesEl) {
      rolesEl.replaceChildren();
      ROLE_ORDER.forEach((roleKey) => rolesEl.appendChild(renderRoleCard(roleKey, session)));
    }

    if (startBtn) {
      if (isGuest) {
        startBtn.hidden = true;
        startBtn.disabled = true;
      } else {
        const ready = rolesReady(session) && session.status === "lobby";
        startBtn.disabled = !ready;
        startBtn.title = ready
          ? "Начать сессию"
          : "Нужно по одному игроку в роли 1 и роли 2";
      }
    }

    if (session.status === "cancelled" || session.status === "finished") {
      if (startBtn) startBtn.disabled = true;
    }
  };

  const goPlay = (url) => {
    const target = url || playPageUrl;
    if (!target || departed) return;
    departed = true;
    location.href = target;
  };

  const applySessionPayload = (data) => {
    if (!data?.session) return;
    state.session = data.session;
    state.free_roles = data.free_roles || [];
    render();
    if (
      data.session.status === "started" ||
      data.session.status === "active" ||
      data.session.status === "ready"
    ) {
      goPlay(playPageUrl);
      return;
    }
    if (data.session.status === "cancelled") {
      departed = true;
      toast("Сессия отменена", "error");
      window.setTimeout(() => {
        location.href = homeUrl;
      }, 900);
    }
  };

  const refresh = async () => {
    if (!getUrl || !getJson || departed) return;
    try {
      const data = await getJson(getUrl);
      applySessionPayload(data);
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      if (err.status === 403 || err.status === 404) {
        departed = true;
        toast(err.message || "Сессия недоступна", "error");
        window.setTimeout(() => {
          location.href = homeUrl;
        }, 900);
      }
    }
  };

  const ping = async () => {
    // Ping и при Alt+Tab / свёрнутом окне: document.hidden здесь нельзя
    // учитывать — иначе ложное «отключение» без ухода со страницы.
    if (!pingUrl || departed) return;
    try {
      const data = await postJson(pingUrl, {});
      applySessionPayload(data);
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      if (err.status === 403 || err.status === 404 || err.data?.error === "session_closed") {
        departed = true;
        toast(err.message || "Сессия недоступна", "error");
        window.setTimeout(() => {
          location.href = homeUrl;
        }, 900);
      }
    }
  };

  const copyText = async (text) => {
    if (navigator.clipboard?.writeText && window.isSecureContext) {
      await navigator.clipboard.writeText(text);
      return;
    }
    const ta = document.createElement("textarea");
    ta.value = text;
    ta.setAttribute("readonly", "");
    ta.style.cssText = "position:fixed;left:-9999px;top:0";
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    const ok = document.execCommand("copy");
    ta.remove();
    if (!ok) throw new Error("copy_failed");
  };

  copyBtn?.addEventListener("click", async (event) => {
    event.preventDefault();
    const code = (state.session?.code || codeEl?.textContent || "").trim();
    if (!code) return;
    try {
      await copyText(code);
      copyBtn.classList.add("is-copied");
      toast("Ключ скопирован", "success");
      window.setTimeout(() => copyBtn.classList.remove("is-copied"), 1200);
    } catch (_) {
      toast("Не удалось скопировать", "error");
    }
  });

  rolesEl?.addEventListener("click", async (event) => {
    const btn = event.target.closest("[data-take-role]");
    if (!btn || !roleUrl || btn.disabled) return;
    event.preventDefault();
    const role = btn.getAttribute("data-take-role");
    btn.disabled = true;
    try {
      await postJson(roleUrl, { role });
      await refresh();
    } catch (err) {
      toast(err.message || "Не удалось выбрать роль", "error");
      btn.disabled = false;
    }
  });

  startBtn?.addEventListener("click", async (event) => {
    event.preventDefault();
    if (isGuest || !startUrl || startBtn.disabled) return;
    startBtn.disabled = true;
    try {
      const data = await postJson(startUrl, {});
      state.session = data.session;
      goPlay(data.play_url || playPageUrl);
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      startBtn.disabled = false;
      toast(err.message || "Не удалось начать", "error");
      void refresh();
    }
  });

  const csrfToken = () =>
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

  const sessionOpen = () => {
    const status = state.session?.status;
    return (
      status === "lobby" ||
      status === "started" ||
      status === "active" ||
      status === "ready"
    );
  };

  /** Уход без ожидания ответа (закрытие вкладки) — fetch keepalive + sendBeacon. */
  const postKeepalive = (url) => {
    if (!url || departed) return;
    departed = true;
    const token = csrfToken();
    try {
      fetch(url, {
        method: "POST",
        credentials: "same-origin",
        keepalive: true,
        headers: {
          Accept: "application/json",
          "Content-Type": "application/json",
          "X-CSRFToken": token,
        },
        body: "{}",
      });
    } catch (_) {
      /* ignore */
    }
    try {
      if (navigator.sendBeacon) {
        const fd = new FormData();
        fd.append("csrf_token", token);
        navigator.sendBeacon(url, fd);
      }
    } catch (_) {
      /* ignore */
    }
  };

  /** Хост → cancel, гость → leave. */
  const exitSession = async ({ navigate = true } = {}) => {
    if (departed) {
      if (navigate) location.href = homeUrl;
      return;
    }
    if (!sessionOpen()) {
      departed = true;
      if (navigate) location.href = homeUrl;
      return;
    }
    const url = isHost ? cancelUrl : leaveUrl;
    if (!url) {
      departed = true;
      if (navigate) location.href = homeUrl;
      return;
    }
    departed = true;
    try {
      await postJson(url, {});
    } catch (err) {
      departed = false;
      toast(err.message || (isHost ? "Не удалось отменить" : "Не удалось выйти"), "error");
      return;
    }
    if (navigate) location.href = homeUrl;
  };

  backLink?.addEventListener("click", (event) => {
    event.preventDefault();
    void exitSession({ navigate: true });
  });

  root.querySelector("[data-lobby-cancel]")?.addEventListener("click", async (event) => {
    event.preventDefault();
    void exitSession({ navigate: true });
  });

  root.querySelector("[data-lobby-leave]")?.addEventListener("click", async (event) => {
    event.preventDefault();
    void exitSession({ navigate: true });
  });

  // Только реальный уход со страницы (другой URL / закрытие вкладки).
  // visibilitychange / Alt+Tab сюда не входят — ping продолжает работать.
  window.addEventListener("pagehide", () => {
    if (departed || !sessionOpen()) return;
    postKeepalive(isHost ? cancelUrl : leaveUrl);
  });

  render();
  void ping();
  window.setInterval(() => {
    void ping();
  }, PING_MS);
  window.setInterval(() => {
    void refresh();
  }, 8000);
})();
