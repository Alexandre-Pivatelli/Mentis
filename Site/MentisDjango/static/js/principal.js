// Carrossel manual: teclado, rolagem nativa e controles com limites visíveis.
(() => {
  const root = document.querySelector('[data-carousel]');
  if (!root) return;
  const track = root.querySelector('[data-track]');
  const prev = root.querySelector('[data-prev]');
  const next = root.querySelector('[data-next]');
  const dots = document.querySelector('[data-dots]');
  if (!track || !prev || !next || !dots) return;
  const cards = [...track.querySelectorAll('.card')];
  const motion = window.matchMedia('(prefers-reduced-motion: reduce)');
  let offsets = [0];
  let current = 0;
  const sync = () => {
    current = offsets.reduce((best, offset, index) =>
      Math.abs(offset - track.scrollLeft) < Math.abs(offsets[best] - track.scrollLeft) ? index : best, 0);
    prev.disabled = track.scrollLeft < 2;
    next.disabled = track.scrollLeft >= track.scrollWidth - track.clientWidth - 2;
    [...dots.children].forEach((dot, index) => {
      if (dot.classList.contains('carousel__status')) {
        dot.textContent = `${current + 1} de ${offsets.length}`;
        return;
      }
      dot.classList.toggle('is-active', index === current);
      if (index === current) dot.setAttribute('aria-current', 'true');
      else dot.removeAttribute('aria-current');
    });
  };
  const goTo = (index) => {
    const target = Math.max(0, Math.min(index, offsets.length - 1));
    track.scrollTo({ left: offsets[target], behavior: motion.matches ? 'instant' : 'smooth' });
  };
  const layout = () => {
    const limit = Math.max(0, track.scrollWidth - track.clientWidth);
    const gap = parseFloat(getComputedStyle(track).columnGap) || 0;
    const width = cards[0]?.getBoundingClientRect().width || track.clientWidth;
    const visible = Math.max(1, Math.floor((track.clientWidth + gap + 1) / (width + gap)));
    offsets = [0];
    for (let index = visible; index < cards.length; index += visible) {
      const left = Math.min(cards[index].offsetLeft - cards[0].offsetLeft, limit);
      if (left > offsets.at(-1) + 2) offsets.push(left);
    }
    const interactive = offsets.length > 1;
    prev.hidden = next.hidden = !interactive;
    const photo = cards[0]?.querySelector('.card__photo');
    if (photo) prev.style.top = next.style.top = `${photo.clientHeight / 2}px`;
    dots.replaceChildren();
    if (interactive && offsets.length > 7) {
      const status = document.createElement('span');
      status.className = 'carousel__status';
      status.setAttribute('role', 'status');
      status.setAttribute('aria-label', 'Grupo de professores');
      dots.append(status);
    } else if (interactive) offsets.forEach((_, index) => {
      const dot = document.createElement('button');
      dot.type = 'button';
      dot.className = 'dot';
      dot.setAttribute('aria-label', `Ir para o grupo ${index + 1} de ${offsets.length}`);
      dot.setAttribute('aria-controls', track.id);
      dot.addEventListener('click', () => goTo(index));
      dots.append(dot);
    });
    sync();
  };
  prev.addEventListener('click', () => goTo(current - 1));
  next.addEventListener('click', () => goTo(current + 1));
  let frame;
  track.addEventListener('scroll', () => {
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(sync);
  }, { passive: true });
  track.addEventListener('keydown', (event) => {
    if (event.target !== track) return;
    const targets = { ArrowRight: current + 1, ArrowLeft: current - 1, Home: 0, End: offsets.length - 1 };
    if (!(event.key in targets)) return;
    event.preventDefault();
    goTo(targets[event.key]);
  });
  if ('ResizeObserver' in window) new ResizeObserver(layout).observe(track);
  else window.addEventListener('resize', layout, { passive: true });
  document.fonts?.ready.then(layout);
  layout();
})();
