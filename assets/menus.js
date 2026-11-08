// Menu content comes from the shared server database. Static HTML remains a fallback.
const menuIllustrations = {};
document.querySelectorAll('.service-card').forEach((card, index) => {
  const svg = card.querySelector('svg');
  if (svg) menuIllustrations[['document', 'chart', 'dialogue'][index]] = svg.cloneNode(true);
});
function menuElement(tag, className, text) {
  const element = document.createElement(tag);
  if (className) element.className = className;
  if (text !== undefined) element.textContent = text;
  return element;
}
function menuLink(menu) {
  const link = menuElement('a', '', menu.title); link.href = menu.url;
  if (menu.url.startsWith('https://')) { link.target = '_blank'; link.rel = 'noopener noreferrer'; }
  const destination = new URL(menu.url, location.href);
  if (destination.origin === location.origin && destination.pathname === (location.pathname === '/' ? '/index.html' : location.pathname) && !destination.hash) link.setAttribute('aria-current', 'page');
  return link;
}
function genericIllustration() {
  const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 180 180'); svg.setAttribute('aria-hidden', 'true');
  // Constant artwork, never supplied by the database.
  svg.innerHTML = '<rect x="32" y="32" width="116" height="116" rx="8" fill="white" stroke="#a2b0a5"/><path d="M64 116 116 64M73 64h43v43" fill="none" stroke="#36534b" stroke-width="3"/>';
  return svg;
}
let renderedRevision = null, menuRequestPending = false;
async function refreshPortalMenus() {
  if (menuRequestPending) return;
  menuRequestPending = true;
  try {
    const response = await fetch('/api/menus', { cache: 'no-store' });
    if (!response.ok) return;
    const data = await response.json();
    if (!Array.isArray(data.menus) || data.revision === renderedRevision) return;
    const menus = data.menus.filter(menu => menu.active);
    const navigation = menus.filter(menu => menu.show_nav);
    document.querySelectorAll('[data-menu-nav]').forEach(container => {
      container.replaceChildren(...navigation.map(menu => { const item = menuElement('li'); item.append(menuLink(menu)); return item; }));
    });
    const mobile = document.querySelector('#mobileMenu');
    if (mobile) {
      mobile.replaceChildren(...navigation.map(menuLink));
      const about = menuElement('a', '', 'Tentang UKI'); about.href = 'index.html#tentang'; mobile.append(about);
    }
    const header = document.querySelector('.site-header');
    header?.classList.toggle('compact-nav', navigation.length > 4 || navigation.reduce((sum, menu) => sum + menu.title.length, 0) > 75);
    const grid = document.querySelector('[data-menu-cards]');
    if (grid) {
      const cards = menus.filter(menu => menu.show_card).map(menu => {
        const card = menuLink(menu); card.className = 'service-card'; card.textContent = '';
        const art = menuElement('div', 'service-art'); art.append(menuElement('span', 'art-label', menu.category || 'Layanan'));
        art.append(menuIllustrations[menu.icon]?.cloneNode(true) ?? genericIllustration());
        const heading = menuElement('div', 'service-heading'); const arrow = menuElement('span', 'circle-arrow', '↗'); arrow.setAttribute('aria-hidden', 'true');
        heading.append(menuElement('h3', '', menu.title), arrow); card.append(art, heading, menuElement('p', '', menu.description)); return card;
      });
      grid.replaceChildren(...cards);
      if (!cards.length) grid.append(menuElement('p', 'section-intro', 'Belum ada layanan yang ditampilkan. Silakan kembali nanti.'));
    }
    renderedRevision = data.revision;
  } catch { /* Keep the existing portal usable during a temporary API outage. */ }
  finally { menuRequestPending = false; }
}
refreshPortalMenus();
window.addEventListener('pageshow', refreshPortalMenus);
window.addEventListener('focus', refreshPortalMenus);
setInterval(() => { if (!document.hidden) refreshPortalMenus(); }, 60000);
