/**
 * Присоединение к сессии по ключу.
 */
(() => {
  const root = document.querySelector("[data-session-join]");
  if (!root || !window.LifeCoreAsync) return;

  const { postJson, toast } = window.LifeCoreAsync;
  const joinUrl = root.getAttribute("data-api-join") || "";
  const lobbyTpl = root.getAttribute("data-api-lobby") || "";

  const codeInput = root.querySelector("[data-session-join-code]");
  const submitBtn = root.querySelector("[data-session-join-submit]");

  const lobbyUrl = (id) => lobbyTpl.replace("{id}", String(id));

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
    joinByCode();
  });

  codeInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      joinByCode();
    }
  });
})();
