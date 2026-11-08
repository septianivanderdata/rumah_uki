const $ = id => document.getElementById(id);
let csrf = '', menus = [], revision = 0, editingId = null, setup = false, busy = false;
function message(text, tone = '') { $('status').textContent = text; $('status').dataset.tone = tone; }
async function api(path, method = 'GET', data) {
  let response;
  try {
    response = await fetch('/api/admin/' + path, {
      method, credentials: 'same-origin', cache: 'no-store',
      headers: { 'Content-Type': 'application/json', ...(csrf ? { 'X-CSRF-Token': csrf } : {}) },
      ...(data !== undefined ? { body: JSON.stringify(data) } : {})
    });
  } catch { throw new Error('Portal tidak dapat dihubungi. Periksa koneksi lalu coba lagi.'); }
  let result;
  try { result = await response.json(); }
  catch { throw new Error('Panel admin belum terhubung. Jalankan portal dengan server aplikasi, lalu buka /admin.'); }
  if (!response.ok) {
    if (response.status === 401 && path !== 'login') { showLogin(false); message(result.error || 'Sesi berakhir. Silakan masuk kembali.', 'error'); }
    const error = new Error(result.error || 'Perubahan belum tersimpan. Coba lagi.');
    error.status = response.status;
    throw error;
  }
  return result;
}
function lock(value) {
  busy = value;
  document.querySelectorAll('button').forEach(button => { button.disabled = value; });
  $('menuFields').disabled = value;
  if ($('dialogFields')) $('dialogFields').disabled = value;
  if (!value) { renderMenus(); window.dialogAdmin?.render(); }
}
function showLogin(firstSetup) {
  csrf = ''; setup = firstSetup;
  window.dialogAdmin?.reset();
  $('dashboard').hidden = true; $('authPanel').hidden = false;
  if ($('editorDialog').open) $('editorDialog').close();
  $('authTitle').innerHTML = firstSetup ? 'Mulai di sini.<br>Kelola dengan mudah.' : 'Masuk.<br>Kelola dengan mudah.';
  $('authFormTitle').textContent = firstSetup ? 'Buat akun admin pertama' : 'Masuk sebagai admin';
  $('setupNote').hidden = !firstSetup; $('confirmGroup').hidden = !firstSetup; $('passwordHint').hidden = !firstSetup;
  $('password').minLength = firstSetup ? 12 : 1;
  $('password').autocomplete = firstSetup ? 'new-password' : 'current-password';
  $('confirmPassword').required = firstSetup;
  $('authSubmit').textContent = firstSetup ? 'Buat akun admin' : 'Masuk';
}
function acceptDataset(data) { menus = data.menus; revision = data.revision; renderMenus(); }
function element(tag, className, text) { const el = document.createElement(tag); if (className) el.className = className; if (text !== undefined) el.textContent = text; return el; }
function action(label, callback, className = '') {
  const button = element('button', 'admin-button ' + className, label);
  button.type = 'button'; button.disabled = busy; button.addEventListener('click', callback); return button;
}
function renderMenus() {
  const list = $('menuList'); list.replaceChildren();
  $('menuCount').textContent = `${menus.length} menu`;
  $('activeCount').textContent = `${menus.filter(m => m.active).length} ditampilkan`;
  $('emptyState').hidden = menus.length !== 0;
  menus.forEach((menu, index) => {
    const row = element('article', 'admin-menu-row'); row.dataset.id = menu.id;
    const controls = element('div', 'reorder-controls');
    const up = action('↑', () => move(index, -1)); up.setAttribute('aria-label', `Naikkan ${menu.title}`); up.disabled = busy || index === 0;
    const down = action('↓', () => move(index, 1)); down.setAttribute('aria-label', `Turunkan ${menu.title}`); down.disabled = busy || index === menus.length - 1;
    controls.append(up, down);
    const info = element('div', 'admin-menu-info'); info.append(element('h2', '', menu.title), element('p', 'menu-url', menu.url));
    const tags = element('div', 'menu-tags'); tags.append(element('span', `menu-tag ${menu.active ? '' : 'hidden-tag'}`, menu.active ? 'Ditampilkan' : 'Disembunyikan'));
    if (menu.show_nav) tags.append(element('span', 'menu-tag', 'Navigasi'));
    if (menu.show_card) tags.append(element('span', 'menu-tag', 'Kartu layanan'));
    info.append(tags);
    const actions = element('div', 'row-actions');
    actions.append(action('Edit', () => openEditor(menu)), action(menu.active ? 'Sembunyikan' : 'Tampilkan', () => toggle(menu)), action('Hapus', () => remove(menu), 'danger'));
    row.append(controls, info, actions); list.append(row);
  });
}
async function refresh() { acceptDataset(await api('menus')); }
async function enter(session) {
  csrf = session.csrf; $('adminName').textContent = session.username;
  await refresh(); await window.dialogAdmin?.load(); $('authPanel').hidden = true; $('dashboard').hidden = false;
  $('authForm').reset(); message('');
}
$('authForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  if (setup && $('password').value !== $('confirmPassword').value) { message('Kata sandi tidak cocok. Periksa kembali kedua kolom.', 'error'); return; }
  lock(true); message(setup ? 'Membuat akun…' : 'Memeriksa akun…');
  try { await enter(await api(setup ? 'setup' : 'login', 'POST', { username: $('username').value.trim(), password: $('password').value })); }
  catch (error) { message(error.message, 'error'); }
  finally { lock(false); }
});
function updatePreview() {
  $('previewTitle').textContent = $('menuTitle').value.trim() || 'Nama menu';
  $('previewDescription').textContent = $('menuDescription').value.trim() || 'Deskripsi layanan akan tampil di sini.';
}
function openEditor(menu = null) {
  if (busy) return;
  editingId = menu?.id ?? null; $('menuForm').reset();
  $('editorTitle').textContent = menu ? 'Edit menu' : 'Tambah menu';
  $('menuTitle').value = menu?.title ?? ''; $('menuUrl').value = menu?.url ?? '';
  $('menuDescription').value = menu?.description ?? ''; $('menuCategory').value = menu?.category ?? '';
  $('menuIcon').value = menu?.icon ?? 'document';
  $('menuPosition').value = menu?.position ?? (menus.length ? Math.max(...menus.map(m => m.position)) + 1 : 0);
  $('menuActive').checked = menu?.active ?? true; $('menuNav').checked = menu?.show_nav ?? true; $('menuCard').checked = menu?.show_card ?? true;
  $('editorError').hidden = true; updatePreview(); $('editorDialog').showModal(); $('menuTitle').focus();
}
function closeEditor() { if (!busy) $('editorDialog').close(); }
$('addButton').addEventListener('click', () => openEditor()); $('emptyAddButton').addEventListener('click', () => openEditor());
$('closeEditor').addEventListener('click', closeEditor); $('cancelEditor').addEventListener('click', closeEditor);
$('editorDialog').addEventListener('cancel', event => { if (busy) event.preventDefault(); });
$('menuTitle').addEventListener('input', updatePreview); $('menuDescription').addEventListener('input', updatePreview);
function menuPayload() {
  return { title: $('menuTitle').value.trim(), url: $('menuUrl').value.trim(), description: $('menuDescription').value.trim(), category: $('menuCategory').value.trim(), icon: $('menuIcon').value, position: Number($('menuPosition').value), active: $('menuActive').checked, show_nav: $('menuNav').checked, show_card: $('menuCard').checked, revision };
}
$('menuForm').addEventListener('submit', async event => {
  event.preventDefault(); if (busy) return;
  const payload = menuPayload(); lock(true); $('saveMenu').textContent = 'Menyimpan…'; $('editorError').hidden = true;
  try {
    acceptDataset(await api(editingId === null ? 'menus' : `menus/${editingId}`, editingId === null ? 'POST' : 'PUT', payload));
    $('editorDialog').close(); message('Menu tersimpan. Perubahan sudah tersedia di portal.', 'success');
  } catch (error) {
    $('editorError').textContent = error.message; $('editorError').hidden = false;
    if (error.status === 409) { try { await refresh(); } catch (refreshError) { message(refreshError.message, 'error'); } }
  } finally { lock(false); $('saveMenu').textContent = 'Simpan menu'; }
});
async function mutate(path, method, data, success) {
  if (busy) return; lock(true);
  try { acceptDataset(await api(path, method, data)); message(success, 'success'); }
  catch (error) { message(error.message, 'error'); if (error.status === 409) { try { await refresh(); } catch (refreshError) { message(refreshError.message, 'error'); } } }
  finally { lock(false); }
}
function toggle(menu) { return mutate(`menus/${menu.id}`, 'PUT', { ...menu, active: !menu.active, revision }, menu.active ? 'Menu disembunyikan dari portal.' : 'Menu ditampilkan di portal.'); }
function remove(menu) {
  if (!confirm(`Hapus menu “${menu.title}”? Tautan dan dokumen tujuan tetap ada, tetapi menu ini akan dihapus dari portal.`)) return;
  return mutate(`menus/${menu.id}`, 'DELETE', { revision }, 'Menu dihapus.');
}
function move(index, direction) {
  const ids = menus.map(menu => menu.id); const target = index + direction;
  if (target < 0 || target >= ids.length) return;
  [ids[index], ids[target]] = [ids[target], ids[index]];
  return mutate('reorder', 'POST', { ids, revision }, 'Urutan menu tersimpan.');
}
$('refreshButton').addEventListener('click', async () => {
  if (busy) return; lock(true);
  try { await refresh(); message('Daftar menu diperbarui.', 'success'); } catch (error) { message(error.message, 'error'); } finally { lock(false); }
});
$('logoutButton').addEventListener('click', async () => {
  if (busy) return; lock(true);
  try { await api('logout', 'POST', {}); menus = []; showLogin(false); message('Anda sudah keluar.'); } catch (error) { message(error.message, 'error'); } finally { lock(false); }
});
(async () => {
  try { const session = await api('session'); if (session.authenticated) await enter(session); else { showLogin(session.setup_available); message(''); } }
  catch (error) { message(error.message, 'error'); }
})();
