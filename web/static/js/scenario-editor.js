/**
 * Редактор сценария: Role 1 / Role 2 + TipTap body + autosave.
 * Формат v2: только actor1/actor2 (без observer / fields / callout).
 */
import { Editor, Extension } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Placeholder from "@tiptap/extension-placeholder";

const DisableTab = Extension.create({
  name: "disableTab",
  addKeyboardShortcuts() {
    return {
      Tab: () => true,
    };
  },
});

const root = document.querySelector("[data-scenario-editor]");
const docEl = document.getElementById("scenario-document");
if (!root || !docEl || !window.LifeCoreAsync) {
  console.error("scenario-editor: missing root or document");
} else {
  const { postJson, toast } = window.LifeCoreAsync;
  const saveUrl = root.getAttribute("data-api-save") || "";
  const statusEl = root.querySelector("[data-editor-status]");

  let documentState;
  try {
    documentState = JSON.parse(docEl.textContent || "{}");
  } catch (err) {
    console.error(err);
    documentState = null;
  }

  if (!documentState?.roles) {
    toast("Не удалось загрузить сценарий", "error");
  } else {
    const editors = new Map();
    let saveTimer = null;
    let saveSeq = 0;
    let dirty = false;
    let saving = false;

    const setStatus = (text, kind = "") => {
      if (!statusEl) return;
      const textEl = statusEl.querySelector("[data-editor-status-text]");
      if (textEl) textEl.textContent = text;
      else statusEl.textContent = text;
      statusEl.classList.remove("is-dirty", "is-saving", "is-error");
      if (kind) statusEl.classList.add(kind);
    };

    const normalizeBody = (body) => {
      if (body && body.type === "doc" && Array.isArray(body.content) && body.content.length) {
        return body;
      }
      return { type: "doc", content: [{ type: "paragraph" }] };
    };

    const collectDocument = () => {
      const next = structuredClone(documentState);
      // Документ v2 — только две роли-актёра.
      delete next.roles?.observer;
      if (next.meta && typeof next.meta === "object") {
        // title живёт в корне; meta больше не контракт.
        if (!next.title && typeof next.meta.title === "string") {
          next.title = next.meta.title;
        }
        delete next.meta;
      }
      next.format = next.format || "roleplay-scenario";
      next.version = 2;
      if (typeof next.title !== "string") next.title = "";

      root.querySelectorAll("[data-role-pane]").forEach((pane) => {
        const key = pane.getAttribute("data-role-key");
        if (!key || !next.roles?.[key]) return;
        const role = next.roles[key];
        role.label = pane.querySelector("[data-role-label]")?.value || "";
        role.goal = pane.querySelector("[data-role-goal]")?.value || "";
        role.context = pane.querySelector("[data-role-context]")?.value || "";
        const editor = editors.get(key);
        if (editor) role.body = editor.getJSON();
      });
      documentState = next;
      return next;
    };

    const scheduleSave = () => {
      dirty = true;
      setStatus("Изменения", "is-dirty");
      window.clearTimeout(saveTimer);
      saveTimer = window.setTimeout(() => {
        void persist();
      }, 700);
    };

    const persist = async () => {
      if (!saveUrl) return;
      const seq = ++saveSeq;
      saving = true;
      setStatus("Сохранение", "is-saving");
      const payload = collectDocument();
      try {
        await postJson(saveUrl, { document: payload });
        if (seq !== saveSeq) return;
        dirty = false;
        saving = false;
        setStatus("Сохранено");
      } catch (err) {
        if (seq !== saveSeq) return;
        saving = false;
        setStatus("Ошибка", "is-error");
        toast(err.message || "Не удалось сохранить", "error");
      }
    };

    const syncToolbar = (pane, editor) => {
      pane.querySelectorAll("[data-cmd]").forEach((btn) => {
        const cmd = btn.getAttribute("data-cmd");
        let active = false;
        if (cmd === "bold") active = editor.isActive("bold");
        else if (cmd === "italic") active = editor.isActive("italic");
        else if (cmd === "underline") active = editor.isActive("underline");
        else if (cmd === "heading") active = editor.isActive("heading", { level: 2 });
        else if (cmd === "bulletList") active = editor.isActive("bulletList");
        else if (cmd === "orderedList") active = editor.isActive("orderedList");
        btn.classList.toggle("is-active", active);
      });
    };

    const mountRole = (pane) => {
      const key = pane.getAttribute("data-role-key");
      const role = documentState.roles[key];
      if (!role) return;

      const mount = pane.querySelector("[data-role-editor]");
      if (!mount) return;

      const editor = new Editor({
        element: mount,
        extensions: [
          StarterKit.configure({
            heading: { levels: [2] },
            codeBlock: false,
            code: false,
            blockquote: false,
            horizontalRule: false,
          }),
          Underline,
          Placeholder.configure({
            placeholder: "Характер, мотивы, что говорить…",
          }),
          DisableTab,
        ],
        content: normalizeBody(role.body),
        editorProps: {
          attributes: {
            class: "tiptap",
            "aria-label": `Свободное поле — ${key}`,
          },
        },
        onUpdate: () => {
          scheduleSave();
          syncToolbar(pane, editor);
        },
        onSelectionUpdate: () => syncToolbar(pane, editor),
      });

      editors.set(key, editor);

      pane.querySelector("[data-role-toolbar]")?.addEventListener("click", (event) => {
        const btn = event.target.closest("[data-cmd]");
        if (!btn || !pane.contains(btn)) return;
        event.preventDefault();
        const cmd = btn.getAttribute("data-cmd");
        const chain = editor.chain().focus();
        if (cmd === "bold") chain.toggleBold().run();
        else if (cmd === "italic") chain.toggleItalic().run();
        else if (cmd === "underline") chain.toggleUnderline().run();
        else if (cmd === "heading") chain.toggleHeading({ level: 2 }).run();
        else if (cmd === "bulletList") chain.toggleBulletList().run();
        else if (cmd === "orderedList") chain.toggleOrderedList().run();
        syncToolbar(pane, editor);
      });

      pane.querySelector("[data-role-label]")?.addEventListener("input", scheduleSave);
      ["data-role-goal", "data-role-context"].forEach((sel) => {
        pane.querySelector(`[${sel}]`)?.addEventListener("input", scheduleSave);
      });

      syncToolbar(pane, editor);
    };

    root.querySelectorAll("[data-role-pane]").forEach(mountRole);

    window.addEventListener("beforeunload", (event) => {
      if (!dirty && !saving) return;
      event.preventDefault();
      event.returnValue = "";
    });

    document.addEventListener("visibilitychange", () => {
      if (document.visibilityState === "hidden" && dirty) {
        window.clearTimeout(saveTimer);
        void persist();
      }
    });
  }
}
