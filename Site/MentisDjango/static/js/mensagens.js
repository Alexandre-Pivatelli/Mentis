(() => {
  const search = document.querySelector('[data-contact-search]');
  const contacts = [...document.querySelectorAll('[data-contact]')];
  const norm = (s) =>
    s
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase();

  search?.addEventListener('input', () => {
    const term = norm(search.value);
    contacts.forEach((c) => {
      c.hidden = !norm(c.dataset.contact).includes(term);
    });

    const emptyMsg = document.querySelector('[data-search-empty]');
    if (emptyMsg) {
      emptyMsg.hidden = contacts.some((c) => !c.hidden) || !search.value;
    }
  });

  const history = document.querySelector('[data-history]');
  if (!history) return;

  history.scrollTop = history.scrollHeight;

  const input = document.querySelector('.message-composer textarea');
  input?.addEventListener('keydown', (e) => {
    if (e.key === 'Enter' && !e.shiftKey && !e.isComposing) {
      e.preventDefault();
      input.form?.requestSubmit();
    }
  });

  let running = false;

  async function poll() {
    if (document.hidden || running) return;
    running = true;

    const controller = new AbortController();
    const timeout = setTimeout(() => controller.abort(), 8000);

    try {
      const last = history.querySelector('[data-message-id]:last-child')?.dataset.messageId || 0;
      const r = await fetch(`${history.dataset.pollUrl}&apos=${last}`, {
        credentials: 'same-origin',
        cache: 'no-store',
        signal: controller.signal,
      });

      if (!r.ok || r.redirected) return;

      const data = await r.json();
      const isAtBottom = history.scrollHeight - history.scrollTop - history.clientHeight < 100;

      data.mensagens.forEach((m) => {
        if (history.querySelector(`[data-message-id="${m.id}"]`)) return;

        const item = document.createElement('article');
        item.className = 'message' + (m.minha ? ' message--own' : '');
        item.dataset.messageId = m.id;

        const text = document.createElement('p');
        text.textContent = m.texto;

        const time = document.createElement('time');
        time.textContent = m.hora;

        item.append(text, time);
        history.append(item);

        const emptyHistory = history.querySelector('[data-empty-history]');
        if (emptyHistory) {
          emptyHistory.hidden = true;
        }
      });

      if (isAtBottom) {
        history.scrollTop = history.scrollHeight;
      }
    } catch {
      // Ignora falhas temporárias de rede durante o polling
    } finally {
      clearTimeout(timeout);
      running = false;
    }
  }

  if (!history.dataset.pollUrl) return;

  const timer = setInterval(poll, 5000);
  window.addEventListener('pagehide', () => clearInterval(timer), { once: true });
  document.addEventListener('visibilitychange', () => {
    if (!document.hidden) poll();
  });
})();