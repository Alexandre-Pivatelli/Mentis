// Melhoria progressiva: cadastro e login funcionam também sem JavaScript.
(() => {
  document.querySelectorAll('[data-password]').forEach(button => {
    const input = document.getElementById(button.dataset.password);
    if (!input) return;
    button.hidden = false;
    button.addEventListener('click', () => {
      const visible = input.type === 'password';
      input.type = visible ? 'text' : 'password';
      button.textContent = visible ? 'Ocultar' : 'Mostrar';
      button.setAttribute('aria-pressed', String(visible));
    });
  });
  const roles = [...document.querySelectorAll('input[name="user_type"]')];
  const updateRole = () => {
    const selected = roles.find(input => input.checked)?.value;
    document.querySelectorAll('[data-profile]').forEach(section => {
      const active = section.dataset.profile === selected;
      section.hidden = !active;
      section.querySelectorAll('input, select').forEach(input => {
        input.disabled = !active;
        if (section.dataset.profile === 'professor') input.required = active;
      });
    });
  };
  if (roles.length) {
    roles.forEach(input => input.addEventListener('change', updateRole));
    updateRole();
  }
  document.querySelectorAll('[data-auth-form]').forEach(form => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('[type="submit"]');
      if (button.disabled) return;
      button.disabled = true;
      button.textContent = button.dataset.loading;
    });
  });
  window.addEventListener('pageshow', () => document.querySelectorAll('[data-loading]').forEach(button => {
    button.disabled = false;
    button.textContent = button.dataset.label;
  }));
  const summary = document.querySelector('[data-error-summary]');
  if (summary) summary.focus();
})();
