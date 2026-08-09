/**
 * Выбор сценария → создание сессии → лобби.
 */
(() => {
  const root = document.querySelector("[data-session-pick]");
  if (!root || !window.LifeCoreAsync) return;

  const { postJson, toast } = window.LifeCoreAsync;
  const createUrl = root.getAttribute("data-api-create") || "";
  const lobbyTpl = root.getAttribute("data-api-lobby") || "";
  const lobbyUrl = (id) => lobbyTpl.replace("{id}", String(id));

  let busy = false;

  root.querySelectorAll("[data-session-pick-card]").forEach((card) => {
    card.addEventListener("click", async (event) => {
      event.preventDefault();
      if (busy || !createUrl) return;
      const scenarioId = Number(card.getAttribute("data-scenario-id"));
      if (!scenarioId) return;

      busy = true;
      card.disabled = true;
      root.querySelectorAll("[data-session-pick-card]").forEach((el) => {
        if (el !== card) el.disabled = true;
      });

      try {
        const data = await postJson(createUrl, { scenario_id: scenarioId });
        const url = data.lobby_url || lobbyUrl(data.session?.session_id);
        if (!url) throw new Error("Не удалось открыть лобби");
        location.href = url;
      } catch (err) {
        toast(err.message || "Не удалось создать сессию", "error");
        busy = false;
        root.querySelectorAll("[data-session-pick-card]").forEach((el) => {
          el.disabled = false;
        });
      }
    });
  });
})();
