// Liga os controles de autenticação aos formulários e às opções de visibilidade da senha.
// Melhoria progressiva: cadastro e login funcionam também sem JavaScript.
(() => {
  document.querySelectorAll('[data-password]').forEach((button) => {
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

  // ===== Troca Estudante / Professor no cadastro =====
  // O tipo escolhido fica guardado no input hidden "user_type" (#userTypeInput)
  // e é alterado pelos botões #btnEstudante e #btnProfessor.
  // Antes, o script procurava um radio "marcado" (input.checked); como o campo
  // é um input hidden, nunca havia nada marcado e TODOS os blocos
  // [data-profile] ficavam escondidos e desabilitados (não eram enviados).
  const userTypeInput = document.getElementById('userTypeInput');
  const btnEstudante = document.getElementById('btnEstudante');
  const btnProfessor = document.getElementById('btnProfessor');

  const updateRole = (selected) => {
    userTypeInput.value = selected;

    // Atualiza o visual dos botões do seletor
    const ehProfessor = selected === 'professor';
    btnEstudante.classList.toggle('active', !ehProfessor);
    btnProfessor.classList.toggle('active', ehProfessor);
    btnEstudante.setAttribute('aria-pressed', String(!ehProfessor));
    btnProfessor.setAttribute('aria-pressed', String(ehProfessor));

    // Mostra só os campos do perfil escolhido e desabilita os do outro perfil
    document.querySelectorAll('[data-profile]').forEach((section) => {
      const active = section.dataset.profile === selected;
      section.hidden = !active;

      section.querySelectorAll('input, select').forEach((input) => {
        input.disabled = !active;
      });
    });

    // Campos obrigatórios de cada perfil (escola é opcional)
    ['id_formacao', 'id_valor_hora', 'id_modalidade'].forEach((id) => {
      const campo = document.getElementById(id);
      if (campo) campo.required = ehProfessor;
    });

    ['id_nivel_estudo', 'id_serie'].forEach((id) => {
      const campo = document.getElementById(id);
      if (campo) campo.required = !ehProfessor;
    });
  };

  if (userTypeInput && btnEstudante && btnProfessor) {
    btnEstudante.addEventListener('click', () => updateRole('estudante'));
    btnProfessor.addEventListener('click', () => updateRole('professor'));
    updateRole(userTypeInput.value === 'professor' ? 'professor' : 'estudante');
  }

  document.querySelectorAll('[data-auth-form]').forEach((form) => {
    form.addEventListener('submit', () => {
      const button = form.querySelector('[type="submit"]');
      if (button.disabled) return;

      button.disabled = true;
      button.textContent = button.dataset.loading;
    });
  });

  window.addEventListener('pageshow', () => {
    document.querySelectorAll('[data-loading]').forEach((button) => {
      button.disabled = false;
      button.textContent = button.dataset.label;
    });
  });

  const summary = document.querySelector('[data-error-summary]');
  if (summary) {
    summary.focus();
  }
})();