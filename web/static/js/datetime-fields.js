/**
 * Единые поля даты (ДД.ММ.ГГГГ) и времени (ЧЧ:ММ) с маской и native-пикером.
 * window.LifeCoreDateTime.bindDateField(input)
 * window.LifeCoreDateTime.bindTimeField(input)
 */
(() => {
  const { bindDigitMask } = window.LifeCoreDigitMask || {};
  if (!bindDigitMask) {
    console.error("LifeCoreDigitMask is required before datetime-fields.js");
    return;
  }

  /* ДД.ММ.ГГГГ:
     день: 1-я 0–3; 2-я 0–9 (если 1-я=3 → 0–1);
     месяц: 3-я 0–1; 4-я 0–9 (если 3-я=1 → 0–2);
     год: 0–9×4 */
  const dateAllowedAt = (index, ch, prefix) => {
    if (index === 0) return ch >= "0" && ch <= "3";
    if (index === 1) {
      if (prefix[0] === "3") return ch >= "0" && ch <= "1";
      return ch >= "0" && ch <= "9";
    }
    if (index === 2) return ch >= "0" && ch <= "1";
    if (index === 3) {
      if (prefix[2] === "1") return ch >= "0" && ch <= "2";
      return ch >= "0" && ch <= "9";
    }
    if (index >= 4 && index <= 7) return ch >= "0" && ch <= "9";
    return false;
  };

  /* ЧЧ:ММ — 1-я: 0–2; 2-я: 0–9 (если час=2 → 0–3); 3-я: 0–5; 4-я: 0–9 */
  const timeAllowedAt = (index, ch, prefix) => {
    if (index === 0) return ch >= "0" && ch <= "2";
    if (index === 1) {
      if (prefix[0] === "2") return ch >= "0" && ch <= "3";
      return ch >= "0" && ch <= "9";
    }
    if (index === 2) return ch >= "0" && ch <= "5";
    if (index === 3) return ch >= "0" && ch <= "9";
    return false;
  };

  const digitsToIsoDate = (digits) => {
    if (!digits || digits.length !== 8 || digits === "00000000") return "";
    const d = digits.slice(0, 2);
    const m = digits.slice(2, 4);
    const y = digits.slice(4, 8);
    return `${y}-${m}-${d}`;
  };

  const isoDateToDigits = (iso) => {
    if (!iso || String(iso).length < 10) return "";
    const [y, m, d] = String(iso).slice(0, 10).split("-");
    if (!y || !m || !d) return "";
    return `${d}${m}${y}`;
  };

  const digitsToTimeValue = (digits) => {
    if (!digits || digits.length !== 4) return "";
    return `${digits.slice(0, 2)}:${digits.slice(2, 4)}`;
  };

  const timeValueToDigits = (t) => String(t || "").replace(/\D/g, "").slice(0, 4);

  const ICONS = {
    date: `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M7 2h2v2h6V2h2v2h3a2 2 0 0 1 2 2v14a2 2 0 0 1-2 2H4a2 2 0 0 1-2-2V6a2 2 0 0 1 2-2h3V2zm13 8H4v10h16V10zm0-4H4v2h16V6z"/></svg>`,
    time: `<svg viewBox="0 0 24 24" width="16" height="16" aria-hidden="true"><path fill="currentColor" d="M12 2a10 10 0 1 1 0 20 10 10 0 0 1 0-20zm1 5h-2v6l5 3 1-1.7-4-2.3V7z"/></svg>`,
  };

  const openNativePicker = (native) => {
    if (typeof native.showPicker === "function") {
      try {
        native.showPicker();
        return;
      } catch (_) {
        /* fall through */
      }
    }
    native.focus();
    native.click();
  };

  const ensureShell = (input, kind) => {
    if (input.parentElement?.classList.contains("dt-field")) {
      return input.parentElement;
    }
    const wrap = document.createElement("div");
    wrap.className = "dt-field";
    wrap.dataset.dtKind = kind;
    input.parentNode.insertBefore(wrap, input);
    wrap.appendChild(input);
    input.classList.add("dt-field__input");

    const btn = document.createElement("button");
    btn.type = "button";
    btn.className = "dt-field__picker";
    btn.setAttribute("aria-label", kind === "date" ? "Выбрать дату" : "Выбрать время");
    btn.tabIndex = -1;
    btn.innerHTML = ICONS[kind];
    wrap.appendChild(btn);

    const native = document.createElement("input");
    native.type = kind === "date" ? "date" : "time";
    native.className = "dt-field__native";
    native.tabIndex = -1;
    native.setAttribute("aria-hidden", "true");
    if (kind === "time") native.step = "60";
    wrap.appendChild(native);

    return wrap;
  };

  const bindDateField = (input) => {
    if (!input) return null;
    const wrap = ensureShell(input, "date");
    const btn = wrap.querySelector(".dt-field__picker");
    const native = wrap.querySelector(".dt-field__native");
    const api = bindDigitMask(input, "00.00.0000", "0", dateAllowedAt);

    const syncNativeFromMask = () => {
      const iso = digitsToIsoDate(api.getDigits());
      native.value = iso || "";
    };

    btn.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });

    btn.addEventListener("click", (event) => {
      event.preventDefault();
      syncNativeFromMask();
      openNativePicker(native);
    });

    native.addEventListener("change", () => {
      const digits = isoDateToDigits(native.value);
      if (!digits) return;
      api.setDigits(digits);
      input.dispatchEvent(new Event("maskchange", { bubbles: true }));
    });

    input.addEventListener("maskchange", syncNativeFromMask);

    return api;
  };

  const bindTimeField = (input) => {
    if (!input) return null;
    const wrap = ensureShell(input, "time");
    const btn = wrap.querySelector(".dt-field__picker");
    const native = wrap.querySelector(".dt-field__native");
    const api = bindDigitMask(input, "00:00", "0", timeAllowedAt);

    const syncNativeFromMask = () => {
      const value = digitsToTimeValue(api.getDigits());
      native.value = value || "";
    };

    btn.addEventListener("mousedown", (event) => {
      event.preventDefault();
    });

    btn.addEventListener("click", (event) => {
      event.preventDefault();
      syncNativeFromMask();
      openNativePicker(native);
    });

    native.addEventListener("change", () => {
      const digits = timeValueToDigits(native.value);
      if (!digits) return;
      api.setDigits(digits);
      input.dispatchEvent(new Event("maskchange", { bubbles: true }));
    });

    input.addEventListener("maskchange", syncNativeFromMask);

    return api;
  };

  /** День и месяц без года: ДД.ММ (без native-пикера). */
  const bindDayMonthField = (input) => {
    if (!input) return null;
    return bindDigitMask(input, "00.00", "0", dateAllowedAt);
  };

  window.LifeCoreDateTime = {
    dateAllowedAt,
    timeAllowedAt,
    bindDateField,
    bindTimeField,
    bindDayMonthField,
    digitsToIsoDate,
    isoDateToDigits,
    digitsToTimeValue,
    timeValueToDigits,
  };
})();
