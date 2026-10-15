// Carrossel de professores: scroll nativo + scroll-snap, sem dependências.
(() => {
  const root = document.querySelector('[data-carousel]');
  if (!root) return;

  const track = root.querySelector('[data-track]');
  const prev = root.querySelector('[data-prev]');
  const next = root.querySelector('[data-next]');
  const dotsWrap = document.querySelector('[data-dots]');
  const cards = track.querySelectorAll('.card');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  let pages = 1;
  let current = 0;
  let timer = null;

  const perView = () => {
    if (!cards.length) return 1;
    return Math.max(1, Math.round(track.clientWidth / cards[0].getBoundingClientRect().width));
  };

  const goTo = (page) => {
    current = (page + pages) % pages;
    track.scrollTo({ left: current * track.clientWidth, behavior: reduceMotion ? 'auto' : 'smooth' });
  };

  const buildDots = () => {
    pages = Math.max(1, Math.ceil(cards.length / perView()));
    root.classList.toggle('is-static', pages <= 1);
    dotsWrap.innerHTML = '';
    if (pages <= 1) return;
    for (let i = 0; i < pages; i++) {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'dot';
      dot.setAttribute('aria-label', `Ir para o grupo ${i + 1}`);
      dot.addEventListener('click', () => { goTo(i); restart(); });
      dotsWrap.appendChild(dot);
    }
    sync();
  };

  const sync = () => {
    current = Math.min(pages - 1, Math.round(track.scrollLeft / Math.max(1, track.clientWidth)));
    dotsWrap.querySelectorAll('.dot').forEach((d, i) => {
      d.classList.toggle('is-active', i === current);
      d.setAttribute('aria-current', i === current ? 'true' : 'false');
    });
  };

  const stop = () => { clearInterval(timer); timer = null; };
  const restart = () => {
    stop();
    if (!reduceMotion && pages > 1) timer = setInterval(() => goTo(current + 1), 6000);
  };

  prev.addEventListener('click', () => { goTo(current - 1); restart(); });
  next.addEventListener('click', () => { goTo(current + 1); restart(); });

  let ticking = false;
  track.addEventListener('scroll', () => {
    if (ticking) return;
    ticking = true;
    requestAnimationFrame(() => { sync(); ticking = false; });
  }, { passive: true });

  track.addEventListener('keydown', (e) => {
    if (e.key === 'ArrowRight') { e.preventDefault(); goTo(current + 1); restart(); }
    if (e.key === 'ArrowLeft') { e.preventDefault(); goTo(current - 1); restart(); }
  });

  root.addEventListener('mouseenter', stop);
  root.addEventListener('mouseleave', restart);
  root.addEventListener('focusin', stop);
  root.addEventListener('focusout', restart);
  document.addEventListener('visibilitychange', () => (document.hidden ? stop() : restart()));

  let resizeId;
  window.addEventListener('resize', () => {
    clearTimeout(resizeId);
    resizeId = setTimeout(() => { buildDots(); goTo(Math.min(current, pages - 1)); }, 150);
  }, { passive: true });

  buildDots();
  restart();
})();
