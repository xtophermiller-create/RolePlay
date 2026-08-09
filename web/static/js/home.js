/**
 * Главное меню: nickname, аватар, настройки аккаунта.
 */
(() => {
  const root = document.querySelector("[data-home-menu]");
  if (!root || !window.LifeCoreAsync) return;

  const { postJson, toast } = window.LifeCoreAsync;
  const Popup = window.LifeCorePopup;

  /* ——— Nickname ——— */

  const input = root.querySelector("[data-home-nickname]");
  const applyBtn = root.querySelector("[data-home-nickname-apply]");
  const nickUrl = root.getAttribute("data-api-nickname") || "";

  if (input && applyBtn && nickUrl) {
    let busy = false;
    let saved = (input.value || "").trim();

    const setApplied = (on) => {
      applyBtn.classList.toggle("is-applied", on);
    };

    const apply = async () => {
      if (busy) return;
      const nickname = (input.value || "").trim();
      if (nickname === saved) {
        setApplied(true);
        window.setTimeout(() => setApplied(false), 900);
        return;
      }

      busy = true;
      applyBtn.disabled = true;
      try {
        const data = await postJson(nickUrl, { nickname });
        saved = (data.nickname || "").trim();
        input.value = saved;
        setApplied(true);
        window.setTimeout(() => setApplied(false), 1100);
      } catch (err) {
        const msg =
          err?.data?.message || err.message || "Не удалось сохранить nickname";
        toast(msg, "error");
      } finally {
        busy = false;
        applyBtn.disabled = false;
      }
    };

    applyBtn.addEventListener("click", (event) => {
      event.preventDefault();
      void apply();
    });

    input.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void apply();
      }
    });

    input.addEventListener("input", () => {
      setApplied(false);
    });
  }

  /* ——— Avatar ——— */

  const avatarBtn = root.querySelector("[data-home-avatar]");
  const avatarImg = root.querySelector("[data-home-avatar-img]");
  const avatarFile = root.querySelector("[data-home-avatar-file]");
  const avatarUrl = root.getAttribute("data-api-avatar") || "";
  const defaultAvatar = root.getAttribute("data-default-avatar") || "";

  if (avatarBtn && avatarImg && avatarFile && avatarUrl) {
    let avatarBusy = false;

    const setAvatarSrc = (url) => {
      avatarImg.src = url || defaultAvatar;
    };

    avatarBtn.addEventListener("click", (event) => {
      event.preventDefault();
      if (avatarBusy) return;
      avatarFile.click();
    });

    avatarFile.addEventListener("change", async () => {
      const file = avatarFile.files?.[0];
      avatarFile.value = "";
      if (!file || avatarBusy) return;

      avatarBusy = true;
      avatarBtn.classList.add("is-busy");
      avatarBtn.disabled = true;

      try {
        const body = new FormData();
        body.append("avatar", file);
        const res = await fetch(avatarUrl, {
          method: "POST",
          credentials: "same-origin",
          headers: {
            Accept: "application/json",
            "X-CSRFToken":
              document.querySelector('meta[name="csrf-token"]')?.content || "",
          },
          body,
        });
        const data = await res.json().catch(() => ({}));
        if (!res.ok || data.ok === false) {
          throw new Error(data.error || `Ошибка ${res.status}`);
        }
        setAvatarSrc(data.avatar_url);
      } catch (err) {
        toast(err.message || "Не удалось загрузить аватар", "error");
      } finally {
        avatarBusy = false;
        avatarBtn.classList.remove("is-busy");
        avatarBtn.disabled = false;
      }
    });
  }

  /* ——— Account settings ——— */

  if (!Popup) return;

  const loginUrl = root.getAttribute("data-api-login") || "";
  const passwordUrl = root.getAttribute("data-api-password") || "";
  let currentLogin = root.getAttribute("data-current-login") || "";

  const accountPopup = document.querySelector("[data-home-account-popup]");
  const loginPopup = document.querySelector("[data-home-login-popup]");
  const passwordPopup = document.querySelector("[data-home-password-popup]");
  const accountOpenBtn = root.querySelector("[data-home-account-open]");
  const accountLoginEl = accountPopup?.querySelector("[data-home-account-login]");

  const loginInput = loginPopup?.querySelector("[data-home-login-input]");
  const loginPassword = loginPopup?.querySelector("[data-home-login-password]");
  const loginSaveBtn = loginPopup?.querySelector("[data-home-login-save]");

  const passwordOld = passwordPopup?.querySelector("[data-home-password-old]");
  const passwordNew = passwordPopup?.querySelector("[data-home-password-new]");
  const passwordConfirm = passwordPopup?.querySelector("[data-home-password-confirm]");
  const passwordSaveBtn = passwordPopup?.querySelector("[data-home-password-save]");

  const setLoginDisplay = (value) => {
    currentLogin = String(value || "").trim();
    root.setAttribute("data-current-login", currentLogin);
    if (accountLoginEl) accountLoginEl.textContent = currentLogin;
  };

  const openPopup = (el) => {
    if (!el) return;
    Popup.open(el);
  };

  const closePopup = (el) => {
    if (!el) return;
    Popup.close(el);
  };

  const snapClose = (el) => {
    if (!el) return;
    Popup.snapClose(el);
  };

  const openAccount = () => {
    if (accountLoginEl) accountLoginEl.textContent = currentLogin || "—";
    openPopup(accountPopup);
  };

  const openLogin = () => {
    snapClose(accountPopup);
    if (loginInput) loginInput.value = currentLogin;
    if (loginPassword) loginPassword.value = "";
    openPopup(loginPopup);
    requestAnimationFrame(() => {
      loginInput?.focus();
      loginInput?.select();
    });
  };

  const openPassword = () => {
    snapClose(accountPopup);
    if (passwordOld) passwordOld.value = "";
    if (passwordNew) passwordNew.value = "";
    if (passwordConfirm) passwordConfirm.value = "";
    openPopup(passwordPopup);
    requestAnimationFrame(() => {
      passwordOld?.focus();
    });
  };

  accountOpenBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    openAccount();
  });

  accountPopup?.querySelectorAll("[data-home-account-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      closePopup(accountPopup);
    });
  });

  accountPopup?.querySelector("[data-home-open-login]")?.addEventListener("click", (event) => {
    event.preventDefault();
    openLogin();
  });

  accountPopup?.querySelector("[data-home-open-password]")?.addEventListener("click", (event) => {
    event.preventDefault();
    openPassword();
  });

  loginPopup?.querySelectorAll("[data-home-login-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      closePopup(loginPopup);
    });
  });

  passwordPopup?.querySelectorAll("[data-home-password-close]").forEach((el) => {
    el.addEventListener("click", (event) => {
      event.preventDefault();
      closePopup(passwordPopup);
    });
  });

  let loginBusy = false;
  let passwordBusy = false;

  const saveLogin = async () => {
    if (loginBusy || !loginUrl || !loginInput) return;
    const login = (loginInput.value || "").trim();
    if (!login) {
      toast("Введите логин", "error");
      return;
    }
    if (login === currentLogin) {
      closePopup(loginPopup);
      return;
    }

    loginBusy = true;
    loginSaveBtn?.setAttribute("disabled", "true");
    try {
      const data = await postJson(loginUrl, {
        login,
        current_password: loginPassword?.value || "",
      });
      setLoginDisplay(data.login || login);
      closePopup(loginPopup);
      toast("Логин обновлён", "success");
    } catch (err) {
      toast(err.message || "Не удалось сменить логин", "error");
    } finally {
      loginBusy = false;
      loginSaveBtn?.removeAttribute("disabled");
    }
  };

  const savePassword = async () => {
    if (passwordBusy || !passwordUrl) return;
    const old_password = passwordOld?.value || "";
    const new_password = passwordNew?.value || "";
    const new_password_confirm = passwordConfirm?.value || "";

    if (!old_password.trim() || !new_password.trim() || !new_password_confirm.trim()) {
      toast("Заполните все поля пароля", "error");
      return;
    }
    if (new_password !== new_password_confirm) {
      toast("Новые пароли не совпадают", "error");
      return;
    }

    passwordBusy = true;
    passwordSaveBtn?.setAttribute("disabled", "true");
    try {
      await postJson(passwordUrl, {
        old_password,
        new_password,
        new_password_confirm,
      });
      closePopup(passwordPopup);
      toast("Пароль обновлён", "success");
    } catch (err) {
      toast(err.message || "Не удалось сменить пароль", "error");
    } finally {
      passwordBusy = false;
      passwordSaveBtn?.removeAttribute("disabled");
    }
  };

  loginSaveBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    void saveLogin();
  });

  passwordSaveBtn?.addEventListener("click", (event) => {
    event.preventDefault();
    void savePassword();
  });

  loginInput?.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      void saveLogin();
    }
  });

  [passwordOld, passwordNew, passwordConfirm].forEach((field) => {
    field?.addEventListener("keydown", (event) => {
      if (event.key === "Enter") {
        event.preventDefault();
        void savePassword();
      }
    });
  });

  document.addEventListener(
    "keydown",
    (event) => {
      if (event.key !== "Escape") return;
      if (passwordPopup?.classList.contains("is-open")) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!passwordBusy) closePopup(passwordPopup);
        return;
      }
      if (loginPopup?.classList.contains("is-open")) {
        event.preventDefault();
        event.stopImmediatePropagation();
        if (!loginBusy) closePopup(loginPopup);
        return;
      }
      if (accountPopup?.classList.contains("is-open")) {
        event.preventDefault();
        event.stopImmediatePropagation();
        closePopup(accountPopup);
      }
    },
    true,
  );
})();
