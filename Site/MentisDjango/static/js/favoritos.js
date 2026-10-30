(() => {
  const forms = document.querySelectorAll('[data-favorite-form]');
  if (!forms.length || !window.fetch) return;
  const status = document.createElement('p');
  status.className = 'favorite-feedback';
  status.setAttribute('role', 'status');
  status.setAttribute('aria-live', 'polite');
  document.body.append(status);
  let timeout;
  forms.forEach(form => form.addEventListener('submit', async event => {
    event.preventDefault();
    const related = [...forms].filter(item => item.dataset.professorId === form.dataset.professorId);
    if (related.some(item => item.querySelector('button').disabled)) return;
    related.forEach(item => { item.querySelector('button').disabled = true; });
    const error = form.querySelector('.favorite-error');
    error.hidden = true;
    form.setAttribute('aria-busy', 'true');
    const controller = new AbortController();
    const requestTimeout = setTimeout(() => controller.abort(), 10000);
    try {
      const response = await fetch(form.action, {
        method: 'POST', body: new FormData(form), credentials: 'same-origin', signal: controller.signal,
        headers: { Accept: 'application/json' },
      });
      if (!response.ok || response.redirected || !response.headers.get('Content-Type')?.includes('application/json')) {
        throw new Error('Não foi possível salvar. Atualize a página e tente novamente.');
      }
      const data = await response.json();
      if (document.querySelector('[data-favorites-page]')) {
        // Recarrega para manter contagem, filtros, paginação e estado vazio consistentes.
        window.location.reload();
        return;
      }
      related.forEach(item => {
        const button = item.querySelector('button');
        item.elements.acao.value = data.favorito ? 'remover' : 'adicionar';
        button.setAttribute('aria-pressed', String(data.favorito));
        button.setAttribute('aria-label', data.favorito ? `Remover ${button.dataset.favoriteName} dos favoritos` : `Favoritar ${button.dataset.favoriteName}`);
        item.querySelector('[data-favorite-label]').textContent = data.favorito ? 'Favoritado' : 'Favoritar';
      });
      status.textContent = data.mensagem;
      clearTimeout(timeout);
      timeout = setTimeout(() => { status.textContent = ''; }, 5000);
    } catch (failure) {
      error.textContent = 'Não foi possível salvar. Verifique sua conexão, atualize a página e tente novamente.';
      error.hidden = false;
    } finally {
      clearTimeout(requestTimeout);
      form.removeAttribute('aria-busy');
      related.forEach(item => { item.querySelector('button').disabled = false; });
    }
  }));
})();
