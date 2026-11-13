// Aplica o tema salvo ou a preferência do sistema e sincroniza os controles da interface.
(() => {
  const key = 'mentis-tema';
  const system = window.matchMedia('(prefers-color-scheme: dark)');
  let preference;
  // A leitura pode falhar em ambientes com armazenamento restrito.
  try { preference = localStorage.getItem(key); } catch (_) { /* Navegação com armazenamento restrito. */ }
  if (!['light', 'dark'].includes(preference)) preference = null;

  // Atualiza os atributos que as folhas de estilo e o controle de tema consultam.
  function apply(theme) {
    // O atributo data-theme na raiz ativa as regras de cor correspondentes.
    document.documentElement.dataset.theme = theme;
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      const dark = theme === 'dark';
      button.setAttribute('aria-pressed', String(dark));
      button.setAttribute('aria-label', `Ativar modo ${dark ? 'claro' : 'escuro'}`);
      button.title = `Ativar modo ${dark ? 'claro' : 'escuro'}`;
      button.querySelector('[data-theme-label]').textContent = dark ? 'Modo claro' : 'Modo escuro';
    });
    const meta = document.querySelector('meta[name="theme-color"]');
    if (meta) meta.content = theme === 'dark' ? '#17131f' : '#6430d8';
  }

  apply(preference || (system.matches ? 'dark' : 'light'));
  document.addEventListener('DOMContentLoaded', () => {
    apply(document.documentElement.dataset.theme);
    document.querySelectorAll('[data-theme-toggle]').forEach(button => {
      button.hidden = false;
      button.addEventListener('click', () => {
        preference = document.documentElement.dataset.theme === 'dark' ? 'light' : 'dark';
        try { localStorage.setItem(key, preference); } catch (_) { /* Mantém o tema nesta página. */ }
        apply(preference);
      });
    });
  });
  // Uma mudança no sistema é refletida se o usuário ainda não escolheu um tema manualmente.
  system.addEventListener('change', event => {
    if (!preference) apply(event.matches ? 'dark' : 'light');
  });
  // Propaga para esta aba uma preferência alterada em outra.
  window.addEventListener('storage', event => {
    if (event.key !== key && event.key !== null) return;
    preference = ['light', 'dark'].includes(event.newValue) ? event.newValue : null;
    apply(preference || (system.matches ? 'dark' : 'light'));
  });
})();
