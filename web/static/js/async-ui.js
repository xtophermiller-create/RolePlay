/**
 * Неблокирующий UI: toast + optimistic / fire-and-forget.
 * window.LifeCoreAsync.toast(msg, kind?)
 * window.LifeCoreAsync.runOptimistic({ apply, rollback, request })
 * window.LifeCoreAsync.postJson(url, body?)
 */
(() => {
  const csrfToken = () =>
    document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";
  const toast = (message, kind = "") => {
    const text = String(message || "").trim();
    if (!text) return;
    let host = document.querySelector("[data-app-toasts]");
    if (!host) {
      host = document.createElement("div");
      host.className = "app-toasts";
      host.setAttribute("data-app-toasts", "");
      document.body.appendChild(host);
    }
    const el = document.createElement("div");
    el.className = "app-toast" + (kind ? ` app-toast--${kind}` : "");
    el.textContent = text;
    host.appendChild(el);
    requestAnimationFrame(() => el.classList.add("is-on"));
    window.setTimeout(() => {
      el.classList.remove("is-on");
      window.setTimeout(() => el.remove(), 280);
    }, 3400);
  };

  const postJson = async (url, body) => {
    const opts = {
      method: "POST",
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() },
    };
    if (body !== undefined) {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
    const res = await fetch(url, opts);
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      const err = new Error(data.message || data.error || `Ошибка ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  };

  const getJson = async (url) => {
    const res = await fetch(url, {
      method: "GET",
      credentials: "same-origin",
      headers: { Accept: "application/json", "X-CSRFToken": csrfToken() },
    });
    const data = await res.json().catch(() => ({}));
    if (!res.ok || data.ok === false) {
      const err = new Error(data.message || data.error || `Ошибка ${res.status}`);
      err.status = res.status;
      err.data = data;
      throw err;
    }
    return data;
  };

  /**
   * apply() сразу; request() в фоне; при ошибке rollback() + toast.
   * request может вернуть Promise или быть async.
   */
  const runOptimistic = ({ apply, rollback, request, errorMessage }) => {
    try {
      apply?.();
    } catch (err) {
      toast(err.message || "Ошибка UI", "error");
      return Promise.resolve({ ok: false });
    }

    return Promise.resolve()
      .then(() => request())
      .then((data) => ({ ok: true, data }))
      .catch((err) => {
        try {
          rollback?.();
        } catch (_) {
          /* ignore */
        }
        toast(err.message || errorMessage || "Не удалось выполнить", "error");
        return { ok: false, error: err };
      });
  };

  window.LifeCoreAsync = { toast, postJson, getJson, runOptimistic };
})();
