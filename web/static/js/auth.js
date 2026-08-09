document.querySelectorAll(".auth__form").forEach((form) => {
  const fields = form.querySelectorAll("input[required], textarea[required]");

  const clearInvalid = (field) => {
    field.classList.remove("auth__input--invalid");
  };

  fields.forEach((field) => {
    field.addEventListener("input", () => clearInvalid(field));
  });

  form.addEventListener("submit", (event) => {
    let valid = true;

    fields.forEach((field) => {
      if (!field.value.trim()) {
        field.classList.add("auth__input--invalid");
        valid = false;
      } else {
        clearInvalid(field);
      }
    });

    if (!valid) {
      event.preventDefault();
    }
  });
});
