/**
 * Активный бой: брифинг → отыгрыш → итог.
 */
(() => {
  const root = document.querySelector("[data-session-play]");
  const bootEl = document.getElementById("session-play-bootstrap");
  if (!root || !bootEl || !window.LifeCoreAsync) return;

  const { postJson, getJson, toast } = window.LifeCoreAsync;
  const bodyEl = root.querySelector("[data-play-body]");
  const actionsEl = root.querySelector("[data-play-actions]");
  const stageEl = root.querySelector("[data-play-stage]");
  const titleEl = root.querySelector("[data-play-title]");
  const backLink = root.querySelector("[data-play-back]");
  const completePopup = document.querySelector("[data-play-complete-popup]");

  const playUrl = root.getAttribute("data-api-play") || "";
  const pingUrl = root.getAttribute("data-api-ping") || "";
  const awayUrl = root.getAttribute("data-api-away") || "";
  const readyUrl = root.getAttribute("data-api-ready") || "";
  const completeUrl = root.getAttribute("data-api-complete") || "";
  const homeUrl = root.getAttribute("data-api-home") || "/home/";
  const currentUserId = Number(root.getAttribute("data-current-user-id"));
  const isGuest = root.getAttribute("data-is-guest") === "1";
  const defaultAvatar = root.getAttribute("data-default-avatar") || "";

  let departed = false;

  const bounceGuest = () => {
    departed = true;
    location.href = homeUrl.includes("join") ? homeUrl : "/sessions/join";
  };

  const PING_MS = 3000;
  const POLL_MS = 2500;

  let finishing = false;
  let state = {
    session: null,
    my_role: null,
    my_ready: false,
    actors_ready: false,
    document: null,
    history: null,
  };

  try {
    const boot = JSON.parse(bootEl.textContent || "{}");
    state.session = boot.session || null;
  } catch (_) {
    toast("Не удалось загрузить сессию", "error");
    return;
  }

  const roleLabels = {
    actor1: root.getAttribute("data-role-actor1") || "Роль 1",
    actor2: root.getAttribute("data-role-actor2") || "Роль 2",
    observer: root.getAttribute("data-role-observer") || "Наблюдатель",
  };

  const escapeHtml = (value) =>
    String(value ?? "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;")
      .replace(/"/g, "&quot;");

  const csrfToken = () =>
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

  /** Жёсткий уход: страница умирает (навигация / закрытие). Больше не пингуем. */
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
      const body = new Blob([JSON.stringify({})], { type: "application/json" });
      navigator.sendBeacon?.(url, body);
    } catch (_) {
      /* ignore */
    }
  };

  const goHome = (message = "", kind = "info") => {
    if (departed && !finishing) return;
    departed = true;
    if (message) toast(message, kind);
    window.setTimeout(() => {
      location.href = homeUrl;
    }, 700);
  };

  backLink?.addEventListener("click", (event) => {
    event.preventDefault();
    if (departed || finishing) return;
    postKeepalive(awayUrl);
    location.href = homeUrl;
  });

  /** TipTap JSON → простой HTML (только безопасные узлы). */
  const renderTipTap = (node) => {
    if (!node || typeof node !== "object") return "";
    if (node.type === "text") {
      let text = escapeHtml(node.text || "");
      const marks = Array.isArray(node.marks) ? node.marks : [];
      for (const mark of marks) {
        if (mark.type === "bold") text = `<strong>${text}</strong>`;
        else if (mark.type === "italic") text = `<em>${text}</em>`;
        else if (mark.type === "underline") text = `<u>${text}</u>`;
        else if (mark.type === "strike") text = `<s>${text}</s>`;
        else if (mark.type === "code") text = `<code>${text}</code>`;
      }
      return text;
    }
    const kids = Array.isArray(node.content)
      ? node.content.map(renderTipTap).join("")
      : "";
    switch (node.type) {
      case "doc":
        return kids;
      case "paragraph":
        return `<p>${kids || "<br>"}</p>`;
      case "heading": {
        const level = Math.min(3, Math.max(1, Number(node.attrs?.level) || 2));
        return `<h${level}>${kids}</h${level}>`;
      }
      case "bulletList":
        return `<ul>${kids}</ul>`;
      case "orderedList":
        return `<ol>${kids}</ol>`;
      case "listItem":
        return `<li>${kids}</li>`;
      case "blockquote":
        return `<blockquote>${kids}</blockquote>`;
      case "codeBlock":
        return `<pre><code>${kids}</code></pre>`;
      case "callout":
        // В редакторе — рамка; для ролей — свёрнутая «Подсказка».
        return `
          <details class="play-hint">
            <summary class="play-hint__toggle">
              <span class="play-hint__icon" aria-hidden="true">!</span>
              <span class="play-hint__label">Подсказка</span>
              <span class="play-hint__chevron" aria-hidden="true"></span>
            </summary>
            <div class="play-hint__body">${kids}</div>
          </details>
        `;
      case "hardBreak":
        return "<br>";
      case "horizontalRule":
        return "<hr>";
      default:
        return kids;
    }
  };

  const roleBlock = (doc, key) => {
    const roles = doc?.roles || {};
    return roles[key] && typeof roles[key] === "object" ? roles[key] : {};
  };

  const participants = () => state.session?.participants || [];

  const actorReadyMap = () => {
    const map = { actor1: false, actor2: false };
    for (const p of participants()) {
      if (p.role === "actor1" || p.role === "actor2") {
        map[p.role] = Boolean(p.is_ready);
      }
    }
    return map;
  };

  const isObserver = () => state.my_role === "observer";
  const isActor = () => state.my_role === "actor1" || state.my_role === "actor2";

  const stage = () => {
    if (state.history || state.session?.status === "finished") return "results";
    if (state.actors_ready) return "play";
    return "brief";
  };

  const roleMeta = (roleKey) => {
    const index = roleKey === "actor2" ? "02" : "01";
    const badge = roleKey === "actor2" ? "Роль 2" : "Роль 1";
    return { index, badge };
  };

  const renderRoleCard = (roleKey, { compact = false } = {}) => {
    const role = roleBlock(state.document, roleKey);
    const { index, badge } = roleMeta(roleKey);
    const label = role.label || roleLabels[roleKey] || roleKey;
    const goal = (role.goal || "").trim();
    const context = (role.context || "").trim();
    const bodyHtml = renderTipTap(role.body);
    const hasMeta = Boolean(goal || context);
    const hasBody = Boolean(bodyHtml);

    return `
      <article class="play-role${compact ? " play-role--compact" : ""}" data-play-role="${escapeHtml(roleKey)}">
        <header class="play-role__head">
          <span class="play-role__index" aria-hidden="true">${index}</span>
          <div class="play-role__identity">
            <span class="play-role__badge">${badge}</span>
            <h2 class="play-role__title">${escapeHtml(label)}</h2>
          </div>
        </header>
        ${
          hasMeta
            ? `<div class="play-role__meta">
                ${
                  goal
                    ? `<section class="play-role__field">
                        <span class="lc-label">Цель</span>
                        <div class="play-role__field-body">${escapeHtml(goal).replace(/\n/g, "<br>")}</div>
                      </section>`
                    : ""
                }
                ${
                  context
                    ? `<section class="play-role__field">
                        <span class="lc-label">Контекст</span>
                        <div class="play-role__field-body">${escapeHtml(context).replace(/\n/g, "<br>")}</div>
                      </section>`
                    : ""
                }
              </div>`
            : ""
        }
        ${
          hasBody
            ? `<section class="play-role__body-wrap">
                <div class="play-role__body-label"><span class="lc-label">Информация</span></div>
                <div class="play-prose">${bodyHtml}</div>
              </section>`
            : ""
        }
        ${
          !hasMeta && !hasBody
            ? `<p class="play-role__empty">Нет данных для этой роли</p>`
            : ""
        }
      </article>
    `;
  };

  const renderResults = () => {
    const history = state.history || {};
    const people = Array.isArray(history.participants) ? history.participants : participants();
    const byRole = {};
    const observers = [];
    for (const p of people) {
      if (p.role === "actor1" || p.role === "actor2") byRole[p.role] = p;
      else if (p.role === "observer") observers.push(p);
    }

    const personCard = (roleKey) => {
      const p = byRole[roleKey];
      const name = p?.nickname || p?.login || roleLabels[roleKey];
      const avatar = p?.avatar_url || defaultAvatar;
      return `
        <article class="play-result__card">
          <img class="play-result__avatar" src="${escapeHtml(avatar)}" alt="" width="64" height="64" draggable="false">
          <div class="play-result__meta">
            <p class="play-result__role">${escapeHtml(roleLabels[roleKey])}</p>
            <p class="play-result__name">${escapeHtml(name)}</p>
          </div>
        </article>
      `;
    };

    const observerLine = observers.length
      ? `<p class="play-result__observers">Наблюдатели: ${observers
          .map((p) => escapeHtml(p.nickname || p.login || "Гость"))
          .join(", ")}</p>`
      : "";

    return `
      <div class="play-result" data-play-result>
        <p class="play-result__eyebrow">Итог</p>
        <h2 class="play-result__title">Ролевка завершена</h2>
        <div class="play-result__grid">
          ${personCard("actor1")}
          ${personCard("actor2")}
        </div>
        ${observerLine}
      </div>
    `;
  };

  let paintedBodyKey = "";
  let paintedActionsKey = "";

  const bodyKey = () =>
    [
      stage(),
      state.my_role || "",
      state.session?.status || "",
      state.history ? "done" : "",
      state.document ? "doc" : "",
    ].join("|");

  const actionsKey = () => {
    const readyMap = actorReadyMap();
    return [
      stage(),
      state.my_role || "",
      state.my_ready ? "1" : "0",
      state.actors_ready ? "1" : "0",
      readyMap.actor1 ? "1" : "0",
      readyMap.actor2 ? "1" : "0",
    ].join("|");
  };

  const renderActions = ({ force = false } = {}) => {
    if (!actionsEl) return;
    const key = actionsKey();
    if (!force && key === paintedActionsKey) return;
    paintedActionsKey = key;

    const s = stage();
    actionsEl.hidden = false;
    actionsEl.replaceChildren();

    if (s === "results") {
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--accent btn--pill";
      btn.textContent = "Выйти";
      btn.addEventListener("click", () => {
        departed = true;
        location.href = homeUrl;
      });
      actionsEl.appendChild(btn);
      return;
    }

    if (isActor()) {
      const ready = state.my_ready || actorReadyMap()[state.my_role];
      if (s === "play" || ready) {
        actionsEl.hidden = true;
        return;
      }
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--accent btn--pill";
      btn.textContent = "Готов";
      btn.addEventListener("click", async () => {
        btn.disabled = true;
        try {
          const data = await postJson(readyUrl, {});
          state.session = data.session || state.session;
          state.actors_ready = Boolean(data.actors_ready);
          state.my_ready = true;
          render({ force: true });
        } catch (err) {
          btn.disabled = false;
          toast(err.message || "Не удалось подтвердить", "error");
        }
      });
      actionsEl.appendChild(btn);
      return;
    }

    if (isObserver()) {
      // Гость не может complete (API: guests_forbidden) — кнопку не показываем.
      if (isGuest) {
        actionsEl.hidden = true;
        return;
      }
      const btn = document.createElement("button");
      btn.type = "button";
      btn.className = "btn btn--accent btn--pill";
      btn.textContent = "Завершить ролевку";
      btn.disabled = s !== "play";
      btn.title = s === "play" ? "Завершить сессию" : "Ждём готовности ролей 1 и 2";
      btn.addEventListener("click", () => {
        if (btn.disabled) return;
        window.LifeCorePopup?.open(completePopup);
      });
      actionsEl.appendChild(btn);
    }
  };

  const renderBody = () => {
    if (!bodyEl) return;
    const s = stage();

    if (s === "results") {
      bodyEl.innerHTML = renderResults();
      return;
    }

    if (isObserver()) {
      bodyEl.innerHTML = `
        <div class="session-play__observer">
          <div class="session-play__briefs">
            ${renderRoleCard("actor1")}
            ${renderRoleCard("actor2")}
          </div>
        </div>
      `;
      return;
    }

    if (isActor()) {
      bodyEl.innerHTML = `<div class="session-play__actor">${renderRoleCard(state.my_role)}</div>`;
      return;
    }

    bodyEl.innerHTML = `<p class="session-play__loading">Роль не назначена</p>`;
  };

  const render = ({ force = false } = {}) => {
    if (!bodyEl) return;
    if (titleEl && state.session?.scenario_title) {
      titleEl.textContent = state.session.scenario_title;
    }

    const s = stage();
    if (stageEl) {
      stageEl.textContent =
        s === "brief" ? "Подготовка" : s === "play" ? "Ролевка" : "Итог";
    }

    const nextBody = bodyKey();
    if (force || nextBody !== paintedBodyKey) {
      paintedBodyKey = nextBody;
      renderBody();
    }
    renderActions({ force });
  };

  const ingestSession = (session) => {
    if (!session) return false;
    state.session = session;
    const ready = actorReadyMap();
    state.actors_ready = Boolean(ready.actor1 && ready.actor2);
    if (state.my_role && ready[state.my_role]) state.my_ready = true;

    if (session.status === "cancelled") {
      goHome("Сессия отменена", "error");
      return true;
    }
    if (session.status === "finished" && !state.history) {
      state.history = {
        actor1_percent: session.actor1_percent,
        actor2_percent: session.actor2_percent,
        overall_percent: session.overall_percent,
        participants: session.participants,
        scenario_title: session.scenario_title,
      };
    }
    return false;
  };

  const applyPlayPayload = (data) => {
    if (!data) return;
    state.my_role = data.my_role ?? state.my_role;
    if (data.my_ready) state.my_ready = true;
    if (data.actors_ready) state.actors_ready = true;
    if (data.document) state.document = data.document;
    if (ingestSession(data.session || state.session)) return;
    render();
  };

  const refresh = async () => {
    if (!playUrl || departed || finishing) return;
    try {
      const data = await getJson(playUrl);
      applyPlayPayload(data);
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      if (err.status === 403 || err.status === 404) {
        goHome(err.message || "Сессия недоступна", "error");
        return;
      }
      if (err.data?.error === "not_started" || err.data?.error === "session_closed") {
        goHome("Сессия завершена", "error");
      }
    }
  };

  /** Если ping сказал «закрыто» — пробуем play: finished → итоги, иначе домой. */
  const recoverAfterClose = async () => {
    if (!playUrl || departed || finishing) return;
    try {
      const data = await getJson(playUrl);
      applyPlayPayload(data);
      if (stage() !== "results") {
        goHome("Сессия завершена", "error");
      }
    } catch (_) {
      goHome("Сессия завершена", "error");
    }
  };

  const ping = async () => {
    if (!pingUrl || departed || finishing) return;
    try {
      const data = await postJson(pingUrl, {});
      if (!data.session) return;
      if (ingestSession(data.session)) return;
      render();
    } catch (err) {
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      if (err.data?.error === "session_closed") {
        await recoverAfterClose();
        return;
      }
      if (err.status === 403 || err.status === 404) {
        goHome(err.message || "Сессия завершена", "error");
      }
    }
  };

  const confirmComplete = async () => {
    if (isGuest || finishing || !completeUrl) return;
    finishing = true;
    const confirmBtn = completePopup?.querySelector("[data-play-complete-confirm]");
    if (confirmBtn) confirmBtn.disabled = true;
    try {
      const data = await postJson(completeUrl, {});
      window.LifeCorePopup?.close(completePopup);
      state.history = data.history || null;
      state.session = {
        ...(state.session || {}),
        status: "finished",
        actor1_percent: data.history?.actor1_percent,
        actor2_percent: data.history?.actor2_percent,
        overall_percent: data.history?.overall_percent,
      };
      departed = true;
      paintedBodyKey = "";
      paintedActionsKey = "";
      render({ force: true });
      toast("Результат сохранён", "success");
    } catch (err) {
      finishing = false;
      if (confirmBtn) confirmBtn.disabled = false;
      if (err.data?.error === "guests_forbidden") {
        bounceGuest();
        return;
      }
      toast(err.message || "Не удалось завершить", "error");
    }
  };

  completePopup?.querySelectorAll("[data-play-complete-close]").forEach((el) => {
    el.addEventListener("click", () => window.LifeCorePopup?.close(completePopup));
  });
  completePopup
    ?.querySelector("[data-play-complete-confirm]")
    ?.addEventListener("click", () => void confirmComplete());

  /**
   * Реальный уход: закрытие вкладки / переход на другой URL.
   * visibilitychange намеренно не трогаем — браузер может скрыть вкладку
   * при Alt+Tab / сворачивании, а ping в фоне throttling'ится → ложный away.
   */
  backLink?.addEventListener("click", (event) => {
    event.preventDefault();
    postKeepalive(awayUrl);
    location.href = homeUrl;
  });

  // Реальный уход со страницы: другой URL сайта или закрытие вкладки/браузера.
  window.addEventListener("pagehide", () => {
    if (!finishing) postKeepalive(awayUrl);
  });
  window.addEventListener("beforeunload", () => {
    if (!finishing) postKeepalive(awayUrl);
  });

  void refresh().then(() => {
    window.setInterval(() => void ping(), PING_MS);
    window.setInterval(() => void refresh(), POLL_MS);
  });
})();
