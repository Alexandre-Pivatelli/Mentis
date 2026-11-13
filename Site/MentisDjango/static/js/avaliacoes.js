// Alterna as avaliações carregadas na página e controla quando a rotação automática pode ocorrer.
// Rotação das avaliações da página atual, sem alterar o formulário ou a paginação.
(() => {
  const root = document.querySelector('[data-review-carousel]');
  if (!root) return;
  const slides = [...root.querySelectorAll('.site-review')];
  if (slides.length < 2) return;
  const controls = root.querySelector('[data-review-controls]');
  const position = root.querySelector('[data-review-position]');
  const pause = root.querySelector('[data-review-pause]');
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let current = 0;
  let paused = motion.matches;
  let visible = false;
  let hovering = false;
  let timer;
  let animation;

  // A troca circular permite voltar da última avaliação para a primeira.
  function show(index, animate = true) {
    animation?.cancel();
    // O resto da divisão mantém o índice entre o primeiro e o último cartão.
    current = (index + slides.length) % slides.length;
    slides.forEach((slide, i) => {
      slide.hidden = i !== current;
      slide.setAttribute('role', 'group');
      slide.setAttribute('aria-label', `Avaliação ${i + 1} de ${slides.length}`);
      // Os leitores de tela recebem apenas a avaliação ativa, mesmo com espaço reservado para as demais.
      slide.setAttribute('aria-hidden', String(i !== current));
    });
    position.textContent = `${current + 1} de ${slides.length}`;
    if (animate && !motion.matches && slides[current].animate) {
      animation = slides[current].animate([
        { opacity: 0, transform: 'translateX(16px)' },
        { opacity: 1, transform: 'none' },
      ], { duration: 550, easing: 'ease-out' });
    }
  }

  // Recalcula o temporizador quando a seção perde visibilidade ou recebe interação.
  function schedule() {
    // Cancela o agendamento anterior para evitar duas trocas simultâneas.
    clearTimeout(timer);
    pause.textContent = paused ? 'Reproduzir avaliações' : 'Pausar avaliações';
    if (paused || !visible || hovering || document.hidden || root.contains(document.activeElement)) return;
    timer = setTimeout(() => { show(current + 1); schedule(); }, 6000);
  }

  root.classList.add('is-carousel');
  // As avaliações ocultas reservam a altura da maior, evitando saltos na página.
  const empty = root.querySelector('.site-reviews__empty');
  if (empty) empty.hidden = true;
  controls.hidden = false;
  show(0, false);
  root.querySelector('[data-review-prev]').addEventListener('click', () => { show(current - 1); schedule(); });
  root.querySelector('[data-review-next]').addEventListener('click', () => { show(current + 1); schedule(); });
  pause.addEventListener('click', () => { paused = !paused; schedule(); });
  root.addEventListener('mouseenter', () => { hovering = true; schedule(); });
  root.addEventListener('mouseleave', () => { hovering = false; schedule(); });
  root.addEventListener('focusin', schedule);
  root.addEventListener('focusout', () => setTimeout(schedule, 0));
  document.addEventListener('visibilitychange', schedule);
  motion.addEventListener('change', event => {
    if (event.matches) { paused = true; animation?.cancel(); }
    schedule();
  });
  if ('IntersectionObserver' in window) {
    // A rotação só é agendada enquanto a seção intercepta a área visível.
    new IntersectionObserver(entries => {
      visible = entries[0].isIntersecting;
      schedule();
    }, { threshold: 0.15 }).observe(root);
  } else {
    visible = true;
    schedule();
  }
})();
