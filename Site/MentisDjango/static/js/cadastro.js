// Coordena as etapas do cadastro, a validação no navegador e os campos de cada perfil.
// ==========================================================================
//  Fluxo guiado de cadastro (Etapas 1 a 4 do Figma) + melhorias de UX
//  - Navegação passo a passo com validação antes de avançar
//  - Textos adaptados conforme o perfil ("Quero aprender" / "Quero ensinar")
//  - Série / período filtrados conforme o nível de estudo
//  - Botão de ícone de olho para mostrar/ocultar a senha + sincronização
//    automática da confirmação de senha no fluxo guiado
//  - Sugestão automática de nome de usuário a partir do nome completo
//  - Contador de caracteres (0 / 300) no resumo/apresentação
// ==========================================================================
(() => {
  const form = document.querySelector('.wizard-form');
  if (!form) return;

  const userTypeInput = document.getElementById('userTypeInput');
  const btnEstudante = document.getElementById('btnEstudante');
  const btnProfessor = document.getElementById('btnProfessor');
  const topbar = document.getElementById('wizardTopbar');
  const backBtn = document.getElementById('wizardBackBtn');
  const progressBar = form.querySelector('.wizard-progress');
  const stepSections = [...form.querySelectorAll('[data-wizard-step]')];
  const stepDots = [...form.querySelectorAll('[data-step-dot]')];

  let currentStep = 1;
  let usernameTouched = false;


  // ------------------------------------------------------------------------
  //  Utilitário: mostra/limpa mensagem de erro logo abaixo de um campo
  // ------------------------------------------------------------------------
  const setLiveError = (input, message) => {
    const group = input.closest('.input-group');
    if (!group) return;

    let box = group.querySelector('.field-live-error');
    if (!box) {
      box = document.createElement('p');
      box.className = 'field-live-error';
      box.id = `${input.id}_liveerror`;
      box.setAttribute('aria-live', 'polite');
      group.appendChild(box);

      const describedBy = input.getAttribute('aria-describedby');
      input.setAttribute('aria-describedby', describedBy ? `${describedBy} ${box.id}` : box.id);
    }

    box.textContent = message;
    box.hidden = !message;

    if (message) {
      input.setAttribute('aria-invalid', 'true');
    } else {
      input.removeAttribute('aria-invalid');
    }
  };


  // ------------------------------------------------------------------------
  //  1) Textos dinâmicos conforme o perfil (Estudante vs Professor)
  // ------------------------------------------------------------------------
  const bioInput = document.getElementById('id_bio');
  const bioLabel = document.querySelector('label[for="id_bio"]');
  const bioHelp = document.getElementById('id_bio_helptext');

  const atualizarTextosPerfil = (tipo) => {
    const ehProfessor = tipo === 'professor';
    const attr = ehProfessor ? 'data-copy-professor' : 'data-copy-estudante';

    form.querySelectorAll(`[${attr}]`).forEach((el) => {
      const texto = el.getAttribute(attr);
      if (!texto) return;

      // Suporta quebra de linha nos títulos (\n -> <br>)
      if (texto.includes('\n')) {
        el.innerHTML = texto
          .split('\n')
          .map((linha) => linha.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;'))
          .join('<br>');
      } else {
        el.textContent = texto;
      }
    });

    if (bioLabel) {
      bioLabel.textContent = ehProfessor
        ? 'Sua apresentação (opcional)'
        : 'Seu resumo (opcional)';
    }

    if (bioInput) {
      bioInput.placeholder = ehProfessor
        ? 'Sou professora de Matemática e gosto de explicar com exemplos do dia a dia. Adapto as aulas ao ritmo de cada aluno, com espaço para perguntas e prática.'
        : 'Estou no 2º ano do ensino médio e quero melhorar em Matemática. Aprendo melhor com exemplos práticos e exercícios passo a passo. Meu objetivo é me preparar para o Enem.';
    }

    if (bioHelp) {
      bioHelp.textContent = ehProfessor
        ? 'Conte sua experiência e como costuma conduzir as aulas.'
        : 'O que você quer aprender? Como gosta de estudar?';
    }
  };


  // ------------------------------------------------------------------------
  //  2) Série / período dependente do nível de estudo (Etapa 3A)
  // ------------------------------------------------------------------------
  const nivel = document.getElementById('id_nivel_estudo');
  const serie = document.getElementById('id_serie');

  if (nivel && serie) {
    const grupos = [...serie.querySelectorAll('optgroup')].map((grupo) =>
      [...grupo.children].map((opcao) => ({ value: opcao.value, text: opcao.textContent }))
    );

    const indicePorNivel = { FUNDAMENTAL: 0, MEDIO: 1, GRADUACAO: 2 };
    const serieLabel = document.querySelector('label[for="id_serie"]');

    const atualizarSeries = () => {
      const anterior = serie.value;
      const indice = indicePorNivel[nivel.value];
      const ehGraduacao = nivel.value === 'GRADUACAO';

      let textoInicial = 'Escolha primeiro o nível de estudo';
      if (indice !== undefined) {
        textoInicial = ehGraduacao ? 'Selecione seu período' : 'Selecione sua série ou etapa';
      }

      serie.replaceChildren(new Option(textoInicial, ''));

      if (indice !== undefined && grupos[indice]) {
        grupos[indice].forEach((opcao) => serie.add(new Option(opcao.text, opcao.value)));
      }

      const aindaExiste = [...serie.options].some((opcao) => opcao.value === anterior);
      serie.value = aindaExiste ? anterior : '';

      if (serieLabel) {
        serieLabel.textContent = ehGraduacao ? 'Período' : 'Série ou etapa';
      }
    };

    nivel.addEventListener('change', atualizarSeries);
    atualizarSeries();
  }


  // ------------------------------------------------------------------------
  //  3) Campo de senha único com ícone de olho (Etapa 2 do Figma)
  // ------------------------------------------------------------------------
  const senha1 = document.getElementById('id_password1');
  const senha2 = document.getElementById('id_password2');
  const confirmGroup = form.querySelector('[data-confirm-password-group]');

  // No modo guiado com JS, o campo "Confirmar senha" fica oculto e sincronizado
  // com a senha principal, pois o usuário confere pelo ícone de olho (como no Figma).
  if (confirmGroup && senha1 && senha2) {
    confirmGroup.hidden = true;
    senha2.required = false;
    const sincronizarSenha = () => {
      senha2.value = senha1.value;
    };
    senha1.addEventListener('input', sincronizarSenha);
    sincronizarSenha();
  }

  const iconeOlhoAberto = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M2 12s3.6-7 10-7 10 7 10 7-3.6 7-10 7-10-7-10-7Z"/>
      <circle cx="12" cy="12" r="3"/>
    </svg>
  `;

  const iconeOlhoFechado = `
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
      <path d="M17.94 17.94A10.4 10.4 0 0 1 12 19c-6.4 0-10-7-10-7a18.4 18.4 0 0 1 5.06-5.94"/>
      <path d="M9.9 4.24A9.1 9.1 0 0 1 12 4c6.4 0 10 7 10 7a18.5 18.5 0 0 1-2.16 3.19"/>
      <path d="M1 1l22 22"/>
    </svg>
  `;

  if (senha1) {
    const wrapper = document.createElement('div');
    wrapper.className = 'password-wrapper';
    senha1.parentNode.insertBefore(wrapper, senha1);
    wrapper.appendChild(senha1);

    const botaoOlho = document.createElement('button');
    botaoOlho.type = 'button';
    botaoOlho.className = 'password-toggle';
    botaoOlho.innerHTML = iconeOlhoAberto;
    botaoOlho.setAttribute('aria-pressed', 'false');
    botaoOlho.setAttribute('aria-controls', senha1.id);
    botaoOlho.setAttribute('aria-label', 'Mostrar senha');
    wrapper.appendChild(botaoOlho);

    botaoOlho.addEventListener('click', () => {
      const mostrar = senha1.type === 'password';
      senha1.type = mostrar ? 'text' : 'password';
      botaoOlho.innerHTML = mostrar ? iconeOlhoFechado : iconeOlhoAberto;
      botaoOlho.setAttribute('aria-pressed', String(mostrar));
      botaoOlho.setAttribute('aria-label', mostrar ? 'Ocultar senha' : 'Mostrar senha');
    });
  }


  // ------------------------------------------------------------------------
  //  4) Sugestão automática de nome de usuário a partir do nome completo
  // ------------------------------------------------------------------------
  const nomeInput = document.getElementById('id_nome');
  const usernameInput = document.getElementById('id_username');

  const gerarSugestaoUsername = (nomeCompleto) => {
    const limpo = nomeCompleto
      .normalize('NFD')
      .replace(/[\u0300-\u036f]/g, '')
      .toLowerCase()
      .replace(/[^a-z0-9\s]/g, ' ')
      .trim();

    if (!limpo) return '';
    const partes = limpo.split(/\s+/).filter(Boolean);
    if (partes.length === 1) return partes[0].slice(0, 30);
    return `${partes[0]}.${partes[partes.length - 1]}`.slice(0, 30);
  };

  if (usernameInput) {
    if (usernameInput.value.trim()) {
      usernameTouched = true;
    }
    usernameInput.addEventListener('input', () => {
      usernameTouched = usernameInput.value.trim().length > 0;
    });
  }

  if (nomeInput && usernameInput) {
    nomeInput.addEventListener('input', () => {
      if (!usernameTouched) {
        usernameInput.value = gerarSugestaoUsername(nomeInput.value);
      }
    });
  }


  // ------------------------------------------------------------------------
  //  5) Contador de caracteres do resumo / apresentação (0 / 300)
  // ------------------------------------------------------------------------
  const bioCounter = document.getElementById('bioCharCounter');

  if (bioInput && bioCounter) {
    const atualizarContador = () => {
      const tamanho = bioInput.value.length;
      bioCounter.textContent = `${tamanho} / 300`;
    };
    bioInput.addEventListener('input', atualizarContador);
    atualizarContador();
  }


  // ------------------------------------------------------------------------
  //  6) Validação de campos e de cada etapa antes de avançar
  // ------------------------------------------------------------------------
  const mensagemPara = (input) => {
    if (input.disabled) return '';
    const valor = input.value.trim();

    if (input.required && !valor) {
      return 'Preencha este campo para continuar.';
    }
    if (input.type === 'email' && valor && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(valor)) {
      return 'Digite um e-mail válido, como voce@exemplo.com.';
    }
    if (input === senha1 && valor) {
      if (valor.length < 8) return 'A senha precisa ter pelo menos 8 caracteres.';
      if (/^\d+$/.test(valor)) return 'Evite uma senha composta apenas por números.';
    }
    if (input.id === 'id_valor_hora' && valor) {
      const numero = Number(valor);
      if (Number.isNaN(numero) || numero <= 0) {
        return 'Informe um valor por hora maior que zero.';
      }
    }
    if (input === usernameInput && valor && !/^[\w.@+-]+$/.test(valor)) {
      return 'Use apenas letras, números e os caracteres . _ @ + - (sem espaços).';
    }
    return '';
  };

  const validarEtapa = (numeroEtapa) => {
    const secao = form.querySelector(`[data-wizard-step="${numeroEtapa}"]`);
    if (!secao) return true;

    const campos = [...secao.querySelectorAll('input:not([type="hidden"]):not([type="file"]), select, textarea')];
    let primeiroInvalido = null;

    campos.forEach((campo) => {
      if (campo.disabled || campo.closest('[hidden]')) return;
      const erro = mensagemPara(campo);
      setLiveError(campo, erro);
      if (erro && !primeiroInvalido) {
        primeiroInvalido = campo;
      }
    });

    if (primeiroInvalido) {
      primeiroInvalido.focus();
      return false;
    }
    return true;
  };

  // Limpa erros ao vivo conforme a pessoa digita ou seleciona
  form.querySelectorAll('input:not([type="hidden"]):not([type="file"]), select, textarea').forEach((input) => {
    const evento = input.tagName === 'SELECT' ? 'change' : 'input';
    input.addEventListener(evento, () => {
      if (input.getAttribute('aria-invalid') === 'true') {
        setLiveError(input, mensagemPara(input));
      }
    });
  });


  // ------------------------------------------------------------------------
  //  7) Controle de navegação entre as 4 etapas
  // ------------------------------------------------------------------------
  const irParaEtapa = (numero, focarTitulo = true) => {
    currentStep = numero;

    stepSections.forEach((secao) => {
      const ativa = Number(secao.dataset.wizardStep) === numero;
      secao.hidden = !ativa;
    });

    if (topbar) {
      topbar.hidden = numero === 1;
    }

    if (progressBar) {
      progressBar.setAttribute('aria-valuenow', String(numero));
    }

    stepDots.forEach((dot) => {
      const passoDot = Number(dot.dataset.stepDot);
      dot.classList.toggle('is-active', passoDot === numero);
      dot.classList.toggle('is-done', passoDot < numero);
    });

    // Quando entrar na etapa 4, garante que a sugestão de usuário esteja preenchida
    if (numero === 4 && nomeInput && usernameInput && !usernameInput.value.trim()) {
      usernameInput.value = gerarSugestaoUsername(nomeInput.value);
    }

    window.scrollTo({ top: 0, behavior: 'smooth' });

    if (focarTitulo) {
      const titulo = form.querySelector(`[data-wizard-step="${numero}"] .wizard-title`);
      if (titulo) {
        titulo.setAttribute('tabindex', '-1');
        titulo.focus({ preventScroll: true });
      }
    }
  };

  // Clique nos cards da Etapa 1 ("Quero aprender" / "Quero ensinar")
  const escolherPerfilEAvancar = (tipo) => {
    atualizarTextosPerfil(tipo);
    irParaEtapa(2);
  };

  if (btnEstudante) {
    btnEstudante.addEventListener('click', () => escolherPerfilEAvancar('estudante'));
  }
  if (btnProfessor) {
    btnProfessor.addEventListener('click', () => escolherPerfilEAvancar('professor'));
  }

  // Botões "Continuar" (Etapas 2 e 3)
  form.querySelectorAll('[data-wizard-next]').forEach((botao) => {
    botao.addEventListener('click', () => {
      const destino = Number(botao.dataset.wizardNext);
      if (validarEtapa(currentStep)) {
        irParaEtapa(destino);
      }
    });
  });

  // Botão "Voltar"
  if (backBtn) {
    backBtn.addEventListener('click', () => {
      if (currentStep > 1) {
        irParaEtapa(currentStep - 1);
      }
    });
  }

  // Enter dentro das etapas 2 e 3 avança para a próxima etapa em vez de enviar antes da hora
  form.addEventListener('keydown', (evento) => {
    if (evento.key !== 'Enter') return;
    if (evento.target.tagName === 'TEXTAREA' || evento.target.tagName === 'BUTTON') return;

    if (currentStep === 2 || currentStep === 3) {
      evento.preventDefault();
      if (validarEtapa(currentStep)) {
        irParaEtapa(currentStep + 1);
      }
    }
  });


  // ------------------------------------------------------------------------
  //  8) Envio final (Etapa 4) e restauração de etapa quando o servidor aponta erro
  // ------------------------------------------------------------------------
  const submitBtn = document.getElementById('wizardSubmitBtn');
  const textoOriginalSubmit = submitBtn ? submitBtn.textContent : '';

  form.addEventListener('submit', (evento) => {
    if (senha1 && senha2) {
      senha2.value = senha1.value;
    }

    if (!validarEtapa(4)) {
      evento.preventDefault();
      return;
    }

    if (submitBtn) {
      submitBtn.disabled = true;
      submitBtn.classList.add('is-loading');
      submitBtn.textContent = 'Criando sua conta…';
    }
  });

  window.addEventListener('pageshow', () => {
    if (!submitBtn) return;
    submitBtn.disabled = false;
    submitBtn.classList.remove('is-loading');
    submitBtn.textContent = textoOriginalSubmit;
  });

  // Inicializa os textos de acordo com o perfil atual
  atualizarTextosPerfil(userTypeInput ? userTypeInput.value : 'estudante');

  // Se o servidor retornou erros de validação, abre diretamente a primeira etapa com erro
  if (form.dataset.hasErrors === 'true') {
    const etapaComErro = stepSections.find((secao) => secao.querySelector('.errorlist'));
    const numeroErro = etapaComErro ? Number(etapaComErro.dataset.wizardStep) : 2;
    irParaEtapa(numeroErro, false);
  } else if (form.dataset.initialRole === 'professor') {
    // Se a pessoa veio por /cadastro/?tipo=professor, já abre na Etapa 2 de professor
    atualizarTextosPerfil('professor');
    irParaEtapa(2, false);
  }
})();
