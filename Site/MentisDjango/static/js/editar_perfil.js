// Confirma a sessão atual antes de enviar um formulário aberto há algum tempo.
(() => {
  const form = document.querySelector('.edit-form[data-session-url]');
  if (!form) return;
  const button = form.querySelector('[type="submit"]');
  const message = form.querySelector('[data-session-message]');
  const label = button.textContent;
  let sending = false;
  const reset = () => {
    sending = false;
    button.disabled = false;
    button.textContent = label;
    form.removeAttribute('aria-busy');
  };
  window.addEventListener('pageshow', reset);
  form.addEventListener('submit', async event => {
    event.preventDefault();
    if (sending) return;
    sending = true;
    button.disabled = true;
    button.textContent = 'Salvando…';
    form.setAttribute('aria-busy', 'true');
    message.hidden = true;
    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 10000);
    let recovery = 'Não foi possível confirmar sua sessão. Confira a conexão e tente salvar novamente.';
    try {
      const response = await fetch(form.dataset.sessionUrl, {
        credentials: 'same-origin', cache: 'no-store', signal: controller.signal,
      });
      if (response.redirected || response.status === 401) {
        recovery = 'Sua sessão expirou. Entre novamente e recarregue esta página antes de salvar.';
        throw new Error();
      }
      if (!response.ok) throw new Error();
      const session = await response.json();
      if (String(session.userId) !== form.dataset.userId) {
        recovery = 'A conta conectada mudou em outra aba. Recarregue esta página antes de editar o perfil.';
        throw new Error();
      }
      if (typeof session.csrfToken !== 'string' || !session.csrfToken) throw new Error();
      form.querySelector('[name="csrfmiddlewaretoken"]').value = session.csrfToken;
      HTMLFormElement.prototype.submit.call(form);
    } catch {
      message.textContent = recovery;
      message.hidden = false;
      reset();
    } finally {
      clearTimeout(timeout);
    }
  });
})();
