// Coordena animações de entrada e de rolagem com suporte à preferência de movimento reduzido.
// Animações compartilhadas pela página principal e pela página de informações.
// Sem JavaScript ou suporte às APIs, todo o conteúdo continua visível.
(() => {
  const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');
  if (reducedMotion.matches || !Element.prototype.animate) return;

  const animations = new Set();
  const observers = new Set();
  const pending = new Map();
  const easing = 'cubic-bezier(0.22, 1, 0.36, 1)';

  function reveal(element, { from = 'translateY(28px)', duration = 750, delay = 0, paused = false } = {}) {
    const animation = element.animate([
      { opacity: 0, transform: from },
      { opacity: 1, transform: 'none' },
    ], { duration, delay, easing, fill: 'both' });

    animations.add(animation);
    if (paused) animation.pause();
    // Libera os estilos ao terminar para preservar hover e demais estilos da página.
    animation.onfinish = () => {
      animation.cancel();
      animations.delete(animation);
      pending.delete(element);
    };
    return animation;
  }

  function revealOnScroll(selector, interval = 220) {
    if (!('IntersectionObserver' in window)) return;
    const elements = [...document.querySelectorAll(selector)];
    if (!elements.length) return;

    const observer = new IntersectionObserver(entries => {
      // No desktop, cards da mesma linha entram em sequência. No celular,
      // cada card espera sua própria entrada na tela, sem acumular atrasos.
      const visible = entries.filter(entry => entry.isIntersecting)
        .sort((a, b) => elements.indexOf(a.target) - elements.indexOf(b.target));
      visible.forEach((entry, index) => {
        const animation = pending.get(entry.target);
        if (animation) {
          animation.effect.updateTiming({ delay: index * interval });
          animation.play();
          pending.delete(entry.target);
        }
        observer.unobserve(entry.target);
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -24px 0px' });

    observers.add(observer);
    elements.forEach(element => {
      pending.set(element, reveal(element, { paused: true }));
      observer.observe(element);
    });
  }

  // Cancela os efeitos pendentes e devolve a visibilidade original aos elementos.
  function showEverything() {
    observers.forEach(observer => observer.disconnect());
    animations.forEach(animation => animation.cancel());
    observers.clear();
    animations.clear();
    pending.clear();
  }

  try {
    if (document.body.classList.contains('principal-page')) {
      const title = document.querySelector('.hero h1');
      const subtitle = document.querySelector('.hero__subtitle');
      if (title && subtitle) {
        // O mesmo deslocamento e a mesma linha do tempo fazem os dois textos
        // descerem juntos, começando acima do topo da janela.
        const offset = Math.max(80, subtitle.getBoundingClientRect().bottom + 24);
        const options = { from: `translateY(-${offset}px)`, duration: 1000, paused: true };
        const entrance = [reveal(title, options), reveal(subtitle, options)];
        const start = document.timeline.currentTime;
        entrance.forEach(animation => {
          animation.play();
          if (start !== null) animation.startTime = start;
        });
      }
      revealOnScroll('.how .step');
    }

    if (document.body.classList.contains('sobre-page')) {
      // O texto surge por blocos, preservando o HTML e a leitura acessível.
      document.querySelectorAll('.sobre-badge, .sobre-hero__titulo, .sobre-hero__texto, .sobre-hero__acoes')
        .forEach((element, index) => reveal(element, { duration: 900, delay: index * 180 }));
      revealOnScroll('.sobre-publicos .sobre-publico');
      revealOnScroll('.sobre-passos .sobre-passo');
      revealOnScroll('.sobre-galeria .sobre-foto', 180);
    }
  } catch (error) {
    // Uma falha na animação nunca deve deixar o conteúdo invisível.
    showEverything();
  }

  reducedMotion.addEventListener('change', event => {
    if (event.matches) showEverything();
  });
  // Conteúdo alcançado pelo teclado aparece imediatamente, mesmo antes do observer.
  document.addEventListener('focusin', event => {
    for (const [element, animation] of pending) {
      if (element.contains(event.target)) {
        animation.cancel();
        animations.delete(animation);
        pending.delete(element);
      }
    }
  });
  window.addEventListener('beforeprint', showEverything);
})();
