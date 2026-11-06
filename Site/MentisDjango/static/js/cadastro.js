// ==========================================================================
//  Melhorias de experiência (UX) do formulário de cadastro
//  - Série / período filtrados conforme o nível de estudo
//  - Botão "Mostrar / Ocultar" nas senhas
//  - Medidor de força da senha
//  - Aviso em tempo real se as senhas não coincidem
//  - Validação de cada campo ao sair dele (sem esperar o envio)
//  - Botão "Criar Conta" com estado de carregamento (evita clique duplo)
//
//  A troca Estudante / Professor continua em static/js/auth.js.
//  Tudo aqui é melhoria progressiva: sem JavaScript o cadastro continua
//  funcionando e o Django valida tudo no servidor.
// ==========================================================================
(() => {
  const form = document.querySelector('.register-form');
  if (!form) return;


  // ------------------------------------------------------------------------
  //  Utilitário: mostra/limpa uma mensagem de erro logo abaixo do campo
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

      // Liga a mensagem ao campo para leitores de tela
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
  //  1) Série / período dependente do nível de estudo
  // ------------------------------------------------------------------------
  const nivel = document.getElementById('id_nivel_estudo');
  const serie = document.getElementById('id_serie');

  if (nivel && serie) {
    // Guarda as opções originais (vindas dos <optgroup> do Django)
    const grupos = [...serie.querySelectorAll('optgroup')].map((grupo) =>
      [...grupo.children].map((opcao) => ({ value: opcao.value, text: opcao.textContent }))
    );

    const indicePorNivel = { FUNDAMENTAL: 0, MEDIO: 1, GRADUACAO: 2 };
    const serieLabel = document.querySelector('label[for="id_serie"]');

    const atualizarSeries = () => {
      const anterior = serie.value;
      const indice = indicePorNivel[nivel.value];
      const ehGraduacao = nivel.value === 'GRADUACAO';

      // Primeira opção explica o que fazer
      let textoInicial = 'Escolha primeiro o nível de estudo';
      if (indice !== undefined) {
        textoInicial = ehGraduacao ? 'Selecione seu período' : 'Selecione sua série';
      }

      serie.replaceChildren(new Option(textoInicial, ''));

      if (indice !== undefined) {
        grupos[indice].forEach((opcao) => serie.add(new Option(opcao.text, opcao.value)));
      }

      // Mantém a escolha anterior se ela ainda for válida
      const aindaExiste = [...serie.options].some((opcao) => opcao.value === anterior);
      serie.value = aindaExiste ? anterior : '';

      if (serieLabel) {
        serieLabel.textContent = ehGraduacao ? 'Período' : 'Série';
      }
    };

    nivel.addEventListener('change', atualizarSeries);
    atualizarSeries();
  }


  // ------------------------------------------------------------------------
  //  2) Botão "Mostrar / Ocultar" nos campos de senha
  // ------------------------------------------------------------------------
  form.querySelectorAll('input[type="password"]').forEach((input) => {
    const wrapper = document.createElement('div');
    wrapper.className = 'password-wrapper';
    input.parentNode.insertBefore(wrapper, input);
    wrapper.appendChild(input);

    const botao = document.createElement('button');
    botao.type = 'button';
    botao.className = 'password-toggle';
    botao.textContent = 'Mostrar';
    botao.setAttribute('aria-pressed', 'false');
    botao.setAttribute('aria-controls', input.id);
    botao.setAttribute('aria-label', 'Mostrar senha');
    wrapper.appendChild(botao);

    botao.addEventListener('click', () => {
      const mostrar = input.type === 'password';
      input.type = mostrar ? 'text' : 'password';
      botao.textContent = mostrar ? 'Ocultar' : 'Mostrar';
      botao.setAttribute('aria-pressed', String(mostrar));
      botao.setAttribute('aria-label', mostrar ? 'Ocultar senha' : 'Mostrar senha');
    });
  });


  // ------------------------------------------------------------------------
  //  3) Medidor de força da senha
  // ------------------------------------------------------------------------
  const senha1 = document.getElementById('id_password1');
  const senha2 = document.getElementById('id_password2');

  if (senha1) {
    const medidor = document.createElement('div');
    medidor.className = 'password-strength';
    medidor.innerHTML = `
      <div class="password-strength__bar"><span></span></div>
      <p class="password-strength__text" aria-live="polite"></p>
    `;
    senha1.closest('.password-wrapper').after(medidor);

    const barra = medidor.querySelector('span');
    const texto = medidor.querySelector('.password-strength__text');

    const niveis = [
      { classe: 'is-weak', texto: 'Senha fraca' },
      { classe: 'is-weak', texto: 'Senha fraca' },
      { classe: 'is-medium', texto: 'Senha razoável' },
      { classe: 'is-good', texto: 'Senha boa' },
      { classe: 'is-strong', texto: 'Senha forte' },
    ];

    const calcularForca = (valor) => {
      let pontos = 0;
      if (valor.length >= 8) pontos += 1;
      if (valor.length >= 12) pontos += 1;
      if (/[a-z]/.test(valor) && /[A-Z]/.test(valor)) pontos += 1;
      if (/\d/.test(valor)) pontos += 1;
      if (/[^A-Za-z0-9]/.test(valor)) pontos += 1;
      if (/^\d+$/.test(valor)) pontos = Math.min(pontos, 1); // só números = fraca
      return Math.min(pontos, 4);
    };

    senha1.addEventListener('input', () => {
      const valor = senha1.value;
      medidor.classList.remove('is-weak', 'is-medium', 'is-good', 'is-strong');

      if (!valor) {
        texto.textContent = '';
        barra.style.width = '0';
        return;
      }

      const forca = calcularForca(valor);
      const faltam = Math.max(0, 8 - valor.length);

      medidor.classList.add(niveis[forca].classe);
      barra.style.width = `${(forca + 1) * 20}%`;
      texto.textContent = faltam > 0
        ? `${niveis[forca].texto} · faltam ${faltam} caractere(s)`
        : niveis[forca].texto;
    });
  }


  // ------------------------------------------------------------------------
  //  4) Confirmação de senha em tempo real
  // ------------------------------------------------------------------------
  const conferirSenhas = () => {
    if (!senha1 || !senha2 || !senha2.value) {
      if (senha2) setLiveError(senha2, '');
      return;
    }

    const iguais = senha1.value === senha2.value;
    senha2.setCustomValidity(iguais ? '' : 'As senhas não coincidem.');
    setLiveError(senha2, iguais ? '' : 'As senhas não coincidem.');
  };

  if (senha1 && senha2) {
    senha1.addEventListener('input', conferirSenhas);
    senha2.addEventListener('input', conferirSenhas);
  }


  // ------------------------------------------------------------------------
  //  5) Validação de cada campo ao sair dele (blur)
  // ------------------------------------------------------------------------
  const mensagemPara = (input) => {
    const v = input.validity;
    if (v.valueMissing) return 'Preencha este campo.';
    if (v.typeMismatch && input.type === 'email') return 'Digite um e-mail válido, como nome@exemplo.com.';
    if (v.rangeUnderflow) return 'Digite um valor maior que zero.';
    if (v.stepMismatch) return 'Use no máximo 2 casas decimais.';
    if (v.customError) return input.validationMessage;
    return '';
  };

  form.querySelectorAll('input:not([type="hidden"]):not([type="file"]), select').forEach((input) => {
    // Valida ao sair do campo
    input.addEventListener('blur', () => {
      if (input.disabled || input === senha2) return;
      setLiveError(input, mensagemPara(input));
    });

    // Some com o erro assim que a pessoa corrige
    const evento = input.tagName === 'SELECT' ? 'change' : 'input';
    input.addEventListener(evento, () => {
      if (input.getAttribute('aria-invalid') === 'true' && input !== senha2) {
        setLiveError(input, mensagemPara(input));
      }
    });
  });


  // ------------------------------------------------------------------------
  //  6) Envio: leva até o primeiro erro ou mostra "Criando conta…"
  // ------------------------------------------------------------------------
  const botaoEnviar = form.querySelector('[type="submit"]');
  const textoOriginal = botaoEnviar ? botaoEnviar.textContent : '';

  // Quando o navegador bloqueia o envio, mostra a mensagem no próprio campo
  form.addEventListener('invalid', (evento) => {
    const input = evento.target;
    setLiveError(input, mensagemPara(input));
  }, true);

  form.addEventListener('submit', () => {
    if (!botaoEnviar) return;
    botaoEnviar.disabled = true;
    botaoEnviar.classList.add('is-loading');
    botaoEnviar.textContent = 'Criando conta…';
  });

  // Se a pessoa voltar para a página pelo histórico, reativa o botão
  window.addEventListener('pageshow', () => {
    if (!botaoEnviar) return;
    botaoEnviar.disabled = false;
    botaoEnviar.classList.remove('is-loading');
    botaoEnviar.textContent = textoOriginal;
  });
})();
