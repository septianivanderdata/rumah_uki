const header = document.querySelector('.site-header');
const menuButton = document.querySelector('#hamburger');
const mobileMenu = document.querySelector('#mobileMenu');

function setMenu(open, returnFocus = false) {
  if (!menuButton || !mobileMenu) return;
  menuButton.setAttribute('aria-expanded', String(open));
  menuButton.setAttribute('aria-label', open ? 'Tutup menu' : 'Buka menu');
  mobileMenu.hidden = !open;
  header?.classList.toggle('menu-open', open);
  if (returnFocus) menuButton.focus();
}

menuButton?.addEventListener('click', () => {
  setMenu(menuButton.getAttribute('aria-expanded') !== 'true');
});
mobileMenu?.querySelectorAll('a').forEach(link => {
  link.addEventListener('click', () => setMenu(false));
});
document.addEventListener('keydown', event => {
  if (event.key === 'Escape' && menuButton?.getAttribute('aria-expanded') === 'true') {
    setMenu(false, true);
  }
});
document.addEventListener('click', event => {
  if (header && !header.contains(event.target)) setMenu(false);
});
const desktop = window.matchMedia('(min-width: 1001px)');
desktop.addEventListener('change', event => { if (event.matches) setMenu(false); });
function updateHeader() { header?.classList.toggle('scrolled', window.scrollY > 40); }
window.addEventListener('scroll', updateHeader, { passive: true });
updateHeader();

// Content remains visible if JavaScript or IntersectionObserver is unavailable.
if ('IntersectionObserver' in window && !window.matchMedia('(prefers-reduced-motion: reduce)').matches) {
  const observer = new IntersectionObserver(entries => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.remove('is-pending');
        observer.unobserve(entry.target);
      }
    });
  }, { threshold: 0.08 });
  document.querySelectorAll('.reveal').forEach(element => {
    element.classList.add('is-pending');
    observer.observe(element);
  });
}
