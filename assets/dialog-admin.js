let dialogLinks = [], dialogRevision = 0, editingLinkId = null;
const dialogMonths = ['Januari','Februari','Maret','April','Mei','Juni','Juli','Agustus','September','Oktober','November','Desember'];
function setAdminPanel(dialog) {
  if (busy) return;
  $('menuPanel').hidden = dialog; $('dialogPanel').hidden = !dialog;
  $('menuTab').setAttribute('aria-pressed', String(!dialog)); $('dialogTab').setAttribute('aria-pressed', String(dialog));
  message('');
}
$('menuTab').addEventListener('click', () => setAdminPanel(false));
$('dialogTab').addEventListener('click', () => setAdminPanel(true));
function acceptDialog(data) { dialogLinks = data.links; dialogRevision = data.revision; renderDialogLinks(); }
async function loadDialogLinks() { acceptDialog(await api('dialog-links')); }
function filteredDialogLinks() {
  const section = $('dialogFilter').value;
  return dialogLinks.filter(link => link.section === section).sort((a,b) => section === 'monthly' ? a.month-b.month : a.position-b.position || a.id-b.id);
}
function renderDialogLinks() {
  const links = filteredDialogLinks(); const section = $('dialogFilter').value;
  $('dialogCount').textContent = `${links.length} ${section === 'monthly' ? 'bulan' : 'tautan'}`;
  $('dialogActiveCount').textContent = `${links.filter(link => link.active).length} ditampilkan`;
  $('dialogListNote').textContent = section === 'monthly' ? 'Klik Edit untuk menambahkan atau mengganti tautan folder bulan. Tautan kosong ditampilkan sebagai “Belum tersedia”.' : 'Gunakan panah untuk mengubah urutan. Klik Edit untuk mengganti nama atau tautan dokumen.';
  const list = $('dialogLinkList'); list.replaceChildren(); $('dialogEmpty').hidden = links.length !== 0;
  $('unitSuggestions').replaceChildren(...[...new Set(dialogLinks.filter(l => l.section === 'units').map(l => l.unit))].map(unit => { const option = element('option'); option.value = unit; return option; }));
  links.forEach((link,index) => {
    const row = element('article', 'admin-menu-row' + (section === 'monthly' ? ' monthly-row' : '')); row.dataset.id = link.id;
    if (section !== 'monthly') {
      const controls = element('div', 'reorder-controls');
      const up = action('↑', () => moveDialogLink(index,-1)); up.setAttribute('aria-label', `Naikkan ${link.title}`); up.disabled = busy || index === 0;
      const down = action('↓', () => moveDialogLink(index,1)); down.setAttribute('aria-label', `Turunkan ${link.title}`); down.disabled = busy || index === links.length-1;
      controls.append(up,down); row.append(controls);
    }
    const info = element('div','admin-menu-info');
    if (link.unit) info.append(element('p','menu-unit',link.unit));
    info.append(element('h2','',link.title),element('p','menu-url',link.url || 'Belum tersedia — tautan folder belum diisi'));
    const tags = element('div','menu-tags'); tags.append(element('span',`menu-tag ${link.active ? '' : 'hidden-tag'}`,link.active ? 'Ditampilkan' : 'Disembunyikan')); info.append(tags);
    const actions = element('div','row-actions'); actions.append(action('Edit',()=>openDialogEditor(link)),action(link.active ? 'Sembunyikan' : 'Tampilkan',()=>mutateDialog(`dialog-links/${link.id}`,'PUT',{...link,active:!link.active,revision:dialogRevision},'Tampilan tautan diperbarui.')),action('Hapus',()=>deleteDialogLink(link),'danger'));
    row.append(info,actions); list.append(row);
  });
}
$('dialogFilter').addEventListener('change',renderDialogLinks);
function updateDialogFields() {
  const section = $('linkSection').value; const monthly = section === 'monthly';
  $('linkMonthGroup').hidden = !monthly; $('linkUnitGroup').hidden = section !== 'units'; $('linkTitleGroup').hidden = monthly; $('linkPositionGroup').hidden = monthly;
  $('linkMonth').required = monthly;
  $('linkTitle').required = !monthly; $('linkUnit').required = section === 'units'; $('linkUrl').required = !monthly; $('linkPosition').required = !monthly;
  $('linkUrlHint').textContent = monthly ? 'Isi URL folder bulan ini. Kosongkan jika folder belum tersedia.' : 'Gunakan tautan HTTPS atau halaman yang sudah ada di portal.';
  [...$('linkMonth').options].forEach(option => { option.disabled = dialogLinks.some(l => l.section === 'monthly' && l.month === Number(option.value) && l.id !== editingLinkId); });
  if ($('linkMonth').selectedOptions[0]?.disabled) $('linkMonth').value = [...$('linkMonth').options].find(option => !option.disabled)?.value ?? '';
  if (monthly && !$('linkMonth').value) { $('dialogEditorError').textContent = 'Semua bulan sudah ada. Pilih Edit pada bulan yang ingin diperbarui.'; $('dialogEditorError').hidden = false; }
}
function openDialogEditor(link=null) {
  if (busy) return;
  editingLinkId = link?.id ?? null; $('dialogLinkForm').reset();
  $('dialogEditorTitle').textContent = link ? 'Edit tautan' : 'Tambah tautan';
  $('linkSection').value = link?.section ?? $('dialogFilter').value;
  $('linkMonth').value = String(link?.month ?? 1); $('linkUnit').value = link?.unit ?? '';
  $('linkTitle').value = link?.title ?? ''; $('linkUrl').value = link?.url ?? '';
  const current = dialogLinks.filter(l => l.section === $('linkSection').value);
  $('linkPosition').value = link?.position ?? (current.length ? Math.max(...current.map(l=>l.position))+1 : 0);
  $('linkActive').checked = link?.active ?? true; $('dialogEditorError').hidden = true;
  updateDialogFields(); $('dialogLinkEditor').showModal(); $('linkSection').focus();
}
$('linkSection').addEventListener('change',updateDialogFields);
$('addDialog').addEventListener('click',()=>openDialogEditor()); $('emptyAddDialog').addEventListener('click',()=>openDialogEditor());
function closeDialogEditor() { if (!busy) $('dialogLinkEditor').close(); }
$('closeDialogEditor').addEventListener('click',closeDialogEditor); $('cancelDialogEditor').addEventListener('click',closeDialogEditor);
$('dialogLinkEditor').addEventListener('cancel', event => { if (busy) event.preventDefault(); });
function dialogPayload() {
  const section = $('linkSection').value;
  return { section, title: section === 'monthly' ? dialogMonths[Number($('linkMonth').value)-1] || '' : $('linkTitle').value.trim(), url:$('linkUrl').value.trim(), unit:section === 'units' ? $('linkUnit').value.trim() : '', month:section === 'monthly' ? Number($('linkMonth').value) : null, position:Number($('linkPosition').value), active:$('linkActive').checked, revision:dialogRevision };
}
$('dialogLinkForm').addEventListener('submit',async event=>{
  event.preventDefault(); if (busy) return; const payload = dialogPayload(); lock(true); $('saveDialogLink').textContent = 'Menyimpan…'; $('dialogEditorError').hidden = true;
  try {
    const data = await api(editingLinkId === null ? 'dialog-links' : `dialog-links/${editingLinkId}`,editingLinkId === null ? 'POST' : 'PUT',payload);
    $('dialogFilter').value = payload.section; acceptDialog(data); $('dialogLinkEditor').close(); message('Tautan tersimpan dan tersedia di halaman Dialog Kinerja.','success');
  } catch(error) {
    $('dialogEditorError').textContent = error.message; $('dialogEditorError').hidden = false;
    if (error.status === 409) { try { await loadDialogLinks(); } catch(refreshError) { message(refreshError.message,'error'); } }
  } finally { lock(false); $('saveDialogLink').textContent = 'Simpan tautan'; }
});
async function mutateDialog(path,method,data,success) {
  if (busy) return; lock(true);
  try { acceptDialog(await api(path,method,data)); message(success,'success'); }
  catch(error) { message(error.message,'error'); if(error.status === 409) { try { await loadDialogLinks(); } catch(refreshError) { message(refreshError.message,'error'); } } }
  finally { lock(false); }
}
function deleteDialogLink(link) {
  if (!confirm(`Hapus tautan “${link.title}” dari halaman Dialog Kinerja? Dokumen di layanan asal tetap ada.`)) return;
  return mutateDialog(`dialog-links/${link.id}`,'DELETE',{revision:dialogRevision},'Tautan dihapus dari halaman Dialog Kinerja.');
}
function moveDialogLink(index,direction) {
  const ids = filteredDialogLinks().map(link=>link.id); const target = index+direction;
  if(target<0 || target>=ids.length) return; [ids[index],ids[target]]=[ids[target],ids[index]];
  return mutateDialog('dialog-links/reorder','POST',{section:$('dialogFilter').value,ids,revision:dialogRevision},'Urutan tautan tersimpan.');
}
$('refreshDialog').addEventListener('click',async()=>{
  if(busy) return; lock(true);
  try { await loadDialogLinks(); message('Daftar tautan diperbarui.','success'); } catch(error) { message(error.message,'error'); } finally { lock(false); }
});
window.dialogAdmin = { load:loadDialogLinks, render:renderDialogLinks, reset() { dialogLinks=[]; dialogRevision=0; if($('dialogLinkEditor').open) $('dialogLinkEditor').close(); setAdminPanel(false); } };
