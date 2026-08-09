/**
 * Цифровая маска ввода (паттерн с blank-слотами).
 * window.LifeCoreDigitMask.bindDigitMask(input, pattern, blank, allowedAt?)
 */
(() => {
  const slotCount = (pattern, blank) =>
    [...pattern].filter((ch) => ch === blank).length;

  const applyDigitMask = (pattern, digits, blank) => {
    const chars = pattern.split("");
    let di = 0;
    for (let i = 0; i < chars.length; i += 1) {
      if (chars[i] === blank) {
        chars[i] = di < digits.length ? digits[di] : blank;
        di += 1;
      }
    }
    return chars.join("");
  };

  const caretForDigitIndex = (pattern, digitIndex, blank) => {
    let seen = 0;
    for (let i = 0; i < pattern.length; i += 1) {
      if (pattern[i] === blank) {
        if (seen === digitIndex) return i;
        seen += 1;
      }
    }
    return pattern.length;
  };

  const filterDigits = (raw, maxDigits, allowedAt) => {
    let cleaned = String(raw || "").replace(/\D/g, "").slice(0, maxDigits);
    if (!allowedAt) return cleaned;
    let ok = "";
    for (let i = 0; i < cleaned.length; i += 1) {
      if (!allowedAt(i, cleaned[i], ok)) break;
      ok += cleaned[i];
    }
    return ok;
  };

  const bindDigitMask = (input, pattern, blank, allowedAt = null) => {
    let maxDigits = slotCount(pattern, blank);
    let digits = "";
    let caretDigit = 0;

    const paint = () => {
      input.value = applyDigitMask(pattern, digits, blank);
      const pos = caretForDigitIndex(pattern, caretDigit, blank);
      requestAnimationFrame(() => input.setSelectionRange(pos, pos));
    };

    const canInsert = (index, ch, prefixDigits = null) => {
      if (!allowedAt) return true;
      const prefix = prefixDigits != null ? prefixDigits : digits.slice(0, index);
      return allowedAt(index, ch, prefix);
    };

    paint();

    input.addEventListener("focus", () => {
      caretDigit = Math.min(digits.length, maxDigits);
      paint();
    });

    input.addEventListener("click", (event) => {
      event.preventDefault();
      caretDigit = Math.min(digits.length, maxDigits);
      paint();
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Backspace") {
        event.preventDefault();
        if (caretDigit === 0) return;
        digits = digits.slice(0, caretDigit - 1) + digits.slice(caretDigit);
        caretDigit -= 1;
        paint();
        input.dispatchEvent(new Event("maskchange", { bubbles: true }));
        return;
      }
      if (event.key === "Delete") {
        event.preventDefault();
        digits = digits.slice(0, caretDigit) + digits.slice(caretDigit + 1);
        paint();
        input.dispatchEvent(new Event("maskchange", { bubbles: true }));
        return;
      }
      if (event.key === "ArrowLeft") {
        event.preventDefault();
        caretDigit = Math.max(0, caretDigit - 1);
        paint();
        return;
      }
      if (event.key === "ArrowRight") {
        event.preventDefault();
        caretDigit = Math.min(digits.length, caretDigit + 1);
        paint();
        return;
      }
      if (event.key === "Home") {
        event.preventDefault();
        caretDigit = 0;
        paint();
        return;
      }
      if (event.key === "End") {
        event.preventDefault();
        caretDigit = digits.length;
        paint();
        return;
      }
      if (event.key.length === 1 && !event.ctrlKey && !event.metaKey && !event.altKey) {
        event.preventDefault();
        if (!/\d/.test(event.key)) return;
        if (caretDigit >= maxDigits) return;
        if (!canInsert(caretDigit, event.key, digits.slice(0, caretDigit))) return;
        digits = (
          digits.slice(0, caretDigit) +
          event.key +
          digits.slice(caretDigit)
        ).slice(0, maxDigits);
        if (allowedAt) {
          digits = filterDigits(digits, maxDigits, allowedAt);
        }
        caretDigit = Math.min(caretDigit + 1, digits.length);
        paint();
        input.dispatchEvent(new Event("maskchange", { bubbles: true }));
      }
    });

    input.addEventListener("beforeinput", (event) => {
      if (event.inputType === "insertFromPaste") {
        event.preventDefault();
        const pasted = (event.data || "").replace(/\D/g, "");
        if (!pasted) return;
        let next = "";
        for (let i = 0; i < pasted.length && next.length < maxDigits; i += 1) {
          const ch = pasted[i];
          if (!canInsert(next.length, ch, next)) {
            if (allowedAt) break;
            continue;
          }
          next += ch;
        }
        digits = next;
        caretDigit = digits.length;
        paint();
        input.dispatchEvent(new Event("maskchange", { bubbles: true }));
      }
    });

    input.addEventListener("keypress", (event) => {
      if (event.key.length === 1 && !/\d/.test(event.key)) event.preventDefault();
    });

    return {
      reset(nextPattern, nextBlank) {
        pattern = nextPattern;
        blank = nextBlank;
        maxDigits = slotCount(pattern, blank);
        digits = "";
        caretDigit = 0;
        paint();
      },
      getDigits: () => digits,
      setDigits(next) {
        digits = filterDigits(next, maxDigits, allowedAt);
        caretDigit = digits.length;
        paint();
      },
      clear() {
        digits = "";
        caretDigit = 0;
        paint();
      },
      isComplete() {
        return digits.length === maxDigits && !/^0+$/.test(digits);
      },
      hasAny() {
        return digits.length > 0 && !/^0+$/.test(digits);
      },
      maxDigits: () => maxDigits,
    };
  };

  window.LifeCoreDigitMask = { bindDigitMask };
})();
