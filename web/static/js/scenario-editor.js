/**
 * Редактор сценария: Role 1 / Role 2 + TipTap body + autosave.
 * Формат v2: actor1/actor2; body — paragraph/heading/lists/section/image.
 */
import { Editor, Extension, Node, mergeAttributes } from "@tiptap/core";
import StarterKit from "@tiptap/starter-kit";
import Underline from "@tiptap/extension-underline";
import Placeholder from "@tiptap/extension-placeholder";
import Image from "@tiptap/extension-image";

const IMAGE_SRC_MAX = 2048;
const SECTION_TITLE_DEFAULT = "Вложение";
const SECTION_TITLE_MAX = 128;

const csrfToken = () =>
  document.querySelector('meta[name="csrf-token"]')?.getAttribute("content") || "";

const normalizeSectionTitle = (value) => {
  const text = String(value ?? "")
    .replace(/\s+/g, " ")
    .trim()
    .slice(0, SECTION_TITLE_MAX);
  return text || SECTION_TITLE_DEFAULT;
};

/**
 * Вложение (section): обычный TipTap NodeView.
 * Шапка contentEditable=false + stopEvent только на шапке.
 * Тело — contentDOM, Enter/Shift+Enter оставляет ProseMirror.
 */
const Section = Node.create({
  name: "section",
  group: "block",
  content: "block+",
  defining: true,

  addAttributes() {
    return {
      title: {
        default: SECTION_TITLE_DEFAULT,
        parseHTML: (element) =>
          normalizeSectionTitle(
            element.getAttribute("data-title") || SECTION_TITLE_DEFAULT
          ),
        renderHTML: (attributes) => ({
          "data-title": normalizeSectionTitle(attributes.title),
        }),
      },
    };
  },

  parseHTML() {
    return [{ tag: "div[data-rp-section]" }];
  },

  renderHTML({ HTMLAttributes }) {
    return [
      "div",
      mergeAttributes(HTMLAttributes, {
        "data-rp-section": "",
        class: "rp-section",
      }),
      0,
    ];
  },

  addCommands() {
    return {
      insertSection:
        (attrs = {}) =>
        ({ chain }) =>
          chain()
            .focus()
            .insertContent({
              type: this.name,
              attrs: {
                title: normalizeSectionTitle(
                  attrs.title ?? SECTION_TITLE_DEFAULT
                ),
              },
              content: [{ type: "paragraph" }],
            })
            .run(),
    };
  },

  addNodeView() {
    return ({ node, getPos, editor }) => {
      const dom = document.createElement("div");
      dom.className = "rp-section";
      dom.setAttribute("data-rp-section", "");

      const head = document.createElement("div");
      head.className = "rp-section__head";
      head.contentEditable = "false";

      const titleEl = document.createElement("input");
      titleEl.type = "text";
      titleEl.className = "rp-section__title";
      titleEl.value = normalizeSectionTitle(node.attrs.title);
      titleEl.maxLength = SECTION_TITLE_MAX;
      titleEl.spellcheck = false;
      titleEl.autocomplete = "off";
      titleEl.setAttribute("aria-label", "Название вложения");

      const removeBtn = document.createElement("button");
      removeBtn.type = "button";
      removeBtn.className = "rp-section__remove";
      removeBtn.title = "Убрать вложение";
      removeBtn.setAttribute("aria-label", "Убрать вложение, оставить содержимое");
      removeBtn.innerHTML = `
        <svg viewBox="0 0 24 24" width="14" height="14" aria-hidden="true">
          <path fill="currentColor" d="M9 3h6l1 2h4v2H4V5h4l1-2Zm1 6h2v9h-2V9Zm4 0h2v9h-2V9ZM7 9h2v9H7V9Zm-1 12h12V8H6v13Z"/>
        </svg>
      `;

      const body = document.createElement("div");
      body.className = "rp-section__body";

      head.append(titleEl, removeBtn);
      dom.append(head, body);

      let editing = false;

      const syncTitle = (finalize) => {
        if (typeof getPos !== "function") return;
        const pos = getPos();
        if (typeof pos !== "number") return;
        const current = editor.state.doc.nodeAt(pos);
        if (!current || current.type.name !== "section") return;
        const next = finalize
          ? normalizeSectionTitle(titleEl.value)
          : String(titleEl.value ?? "")
              .replace(/\s+/g, " ")
              .slice(0, SECTION_TITLE_MAX);
        if (finalize) titleEl.value = next;
        if (current.attrs.title === next) return;
        editor.view.dispatch(
          editor.state.tr
            .setNodeMarkup(pos, undefined, { ...current.attrs, title: next })
            .setMeta("addToHistory", !finalize ? false : true)
        );
      };

      titleEl.addEventListener("focus", () => {
        editing = true;
      });
      titleEl.addEventListener("input", () => {
        editing = true;
        syncTitle(false);
      });
      titleEl.addEventListener("keydown", (event) => {
        if (event.key === "Enter") {
          event.preventDefault();
          titleEl.blur();
        }
      });
      titleEl.addEventListener("blur", () => {
        syncTitle(true);
        editing = false;
      });

      removeBtn.addEventListener("mousedown", (event) => {
        event.preventDefault();
      });
      removeBtn.addEventListener("click", () => {
        if (typeof getPos !== "function") return;
        const pos = getPos();
        if (typeof pos !== "number") return;
        const current = editor.state.doc.nodeAt(pos);
        if (!current || current.type.name !== "section") return;
        editing = false;
        editor.view.dispatch(
          editor.state.tr.replaceWith(pos, pos + current.nodeSize, current.content)
        );
        editor.commands.focus();
      });

      return {
        dom,
        contentDOM: body,
        update: (updated) => {
          if (updated.type.name !== "section") return false;
          if (!editing && document.activeElement !== titleEl) {
            titleEl.value = normalizeSectionTitle(updated.attrs.title);
          }
          return true;
        },
        ignoreMutation: (mutation) =>
          head.contains(mutation.target) || mutation.target === head,
        // Канон TipTap: события шапки не для ProseMirror; тело — как обычно.
        stopEvent: (event) => head.contains(event.target),
      };
    };
  },
});

/** Tab / Shift+Tab меняют уровень пункта списка; иначе Tab глушим. */
const ListTabKeys = Extension.create({
  name: "listTabKeys",
  addKeyboardShortcuts() {
    return {
      Tab: () => {
        if (this.editor.commands.sinkListItem("listItem")) return true;
        return true;
      },
      "Shift-Tab": () => {
        if (this.editor.commands.liftListItem("listItem")) return true;
        return true;
      },
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
  const imageUploadUrl = root.getAttribute("data-api-image") || "";
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
    let openListMenu = null;

    const setStatus = (text, kind = "") => {
      if (!statusEl) return;
      const textEl = statusEl.querySelector("[data-editor-status-text]");
      if (textEl) textEl.textContent = text;
      else statusEl.textContent = text;
      statusEl.classList.remove("is-dirty", "is-saving", "is-error");
      if (kind) statusEl.classList.add(kind);
    };

    const ensureBlocks = (node) => {
      if (!node || typeof node !== "object") return node;
      const next = { ...node };
      if (Array.isArray(node.content)) {
        next.content = node.content.map(ensureBlocks);
      }
      if (next.type === "section" && (!next.content || !next.content.length)) {
        next.content = [{ type: "paragraph" }];
      }
      return next;
    };

    const normalizeBody = (body) => {
      if (body && body.type === "doc" && Array.isArray(body.content) && body.content.length) {
        return ensureBlocks(body);
      }
      return { type: "doc", content: [{ type: "paragraph" }] };
    };

    const collectDocument = () => {
      const next = structuredClone(documentState);
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

    const closeListMenu = (menu) => {
      if (!menu) return;
      const panel = menu.querySelector("[data-list-menu-panel]");
      const toggle = menu.querySelector("[data-list-menu-toggle]");
      if (panel) panel.hidden = true;
      if (toggle) toggle.setAttribute("aria-expanded", "false");
      menu.classList.remove("is-open");
      if (openListMenu === menu) openListMenu = null;
    };

    const closeAllListMenus = () => {
      root.querySelectorAll("[data-list-menu]").forEach(closeListMenu);
    };

    const syncToolbar = (pane, editor) => {
      pane.querySelectorAll("[data-cmd]").forEach((btn) => {
        const cmd = btn.getAttribute("data-cmd");
        let active = false;
        let disabled = false;
        if (cmd === "bold") active = editor.isActive("bold");
        else if (cmd === "italic") active = editor.isActive("italic");
        else if (cmd === "underline") active = editor.isActive("underline");
        else if (cmd === "heading") active = editor.isActive("heading", { level: 2 });
        else if (cmd === "bulletList") active = editor.isActive("bulletList");
        else if (cmd === "orderedList") active = editor.isActive("orderedList");
        else if (cmd === "image") active = editor.isActive("image");
        else if (cmd === "section") {
          // Кнопка только вставляет — без «активного» состояния.
          active = false;
        } else if (cmd === "sinkList") {
          disabled = !editor.can().sinkListItem("listItem");
        } else if (cmd === "liftList") {
          disabled = !editor.can().liftListItem("listItem");
        }
        btn.classList.toggle("is-active", active);
        if (cmd === "sinkList" || cmd === "liftList") {
          btn.disabled = disabled;
        }
      });

      const listLabel = pane.querySelector("[data-list-menu-label]");
      const listToggle = pane.querySelector("[data-list-menu-toggle]");
      if (listLabel) {
        if (editor.isActive("orderedList")) listLabel.textContent = "1.";
        else if (editor.isActive("bulletList")) listLabel.textContent = "•";
        else listLabel.textContent = "•";
      }
      if (listToggle) {
        listToggle.classList.toggle(
          "is-active",
          editor.isActive("bulletList") || editor.isActive("orderedList")
        );
      }
    };

    const pickAndUploadImage = () =>
      new Promise((resolve) => {
        if (!imageUploadUrl) {
          toast("Загрузка изображений недоступна", "error");
          resolve(null);
          return;
        }
        const input = document.createElement("input");
        input.type = "file";
        // Явные MIME + расширения: на Windows `image/*` даёт кривой фильтр проводника.
        input.accept =
          "image/jpeg,image/png,image/webp,image/gif,image/bmp,.jpg,.jpeg,.png,.webp,.gif,.bmp";
        input.hidden = true;
        document.body.appendChild(input);
        const cleanup = () => {
          input.remove();
        };
        input.addEventListener("change", async () => {
          const file = input.files?.[0];
          cleanup();
          if (!file) {
            resolve(null);
            return;
          }
          try {
            const body = new FormData();
            body.append("image", file);
            const res = await fetch(imageUploadUrl, {
              method: "POST",
              credentials: "same-origin",
              headers: {
                Accept: "application/json",
                "X-CSRFToken": csrfToken(),
              },
              body,
            });
            const data = await res.json().catch(() => ({}));
            if (!res.ok || data.ok === false) {
              throw new Error(
                data.message || data.error || `Ошибка ${res.status}`
              );
            }
            const url = String(data.url || "").trim();
            if (!url) throw new Error("Сервер не вернул ссылку");
            if (url.length > IMAGE_SRC_MAX) {
              throw new Error("Ссылка слишком длинная");
            }
            resolve(url);
          } catch (err) {
            toast(err.message || "Не удалось загрузить изображение", "error");
            resolve(null);
          }
        });
        input.addEventListener("cancel", () => {
          cleanup();
          resolve(null);
        });
        input.click();
      });

    const runCommand = async (pane, editor, cmd) => {
      const chain = editor.chain().focus();
      if (cmd === "bold") chain.toggleBold().run();
      else if (cmd === "italic") chain.toggleItalic().run();
      else if (cmd === "underline") chain.toggleUnderline().run();
      else if (cmd === "heading") chain.toggleHeading({ level: 2 }).run();
      else if (cmd === "bulletList") {
        chain.toggleBulletList().run();
        closeAllListMenus();
      } else if (cmd === "orderedList") {
        chain.toggleOrderedList().run();
        closeAllListMenus();
      } else if (cmd === "sinkList") chain.sinkListItem("listItem").run();
      else if (cmd === "liftList") chain.liftListItem("listItem").run();
      else if (cmd === "section") {
        editor.chain().focus().insertSection().run();
      } else if (cmd === "image") {
        const src = await pickAndUploadImage();
        if (!src) return;
        editor.chain().focus().setImage({ src, alt: "", title: "" }).run();
      }
      syncToolbar(pane, editor);
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
          Image.configure({
            inline: false,
            allowBase64: true,
            HTMLAttributes: {
              class: "rp-image",
            },
          }),
          Section,
          Placeholder.configure({
            placeholder: "Характер, мотивы, что говорить…",
          }),
          ListTabKeys,
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

      const toolbar = pane.querySelector("[data-role-toolbar]");
      toolbar?.addEventListener("click", (event) => {
        const menuToggle = event.target.closest("[data-list-menu-toggle]");
        if (menuToggle && pane.contains(menuToggle)) {
          event.preventDefault();
          const menu = menuToggle.closest("[data-list-menu]");
          const panel = menu?.querySelector("[data-list-menu-panel]");
          if (!menu || !panel) return;
          const willOpen = panel.hidden;
          closeAllListMenus();
          if (willOpen) {
            panel.hidden = false;
            menu.classList.add("is-open");
            menuToggle.setAttribute("aria-expanded", "true");
            openListMenu = menu;
          }
          return;
        }

        const btn = event.target.closest("[data-cmd]");
        if (!btn || !pane.contains(btn) || btn.disabled) return;
        event.preventDefault();
        void runCommand(pane, editor, btn.getAttribute("data-cmd"));
      });

      pane.querySelector("[data-role-label]")?.addEventListener("input", scheduleSave);
      ["data-role-goal", "data-role-context"].forEach((sel) => {
        pane.querySelector(`[${sel}]`)?.addEventListener("input", scheduleSave);
      });

      syncToolbar(pane, editor);
    };

    root.querySelectorAll("[data-role-pane]").forEach(mountRole);

    document.addEventListener("pointerdown", (event) => {
      if (!openListMenu) return;
      if (openListMenu.contains(event.target)) return;
      closeAllListMenus();
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") closeAllListMenus();
    });

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
