let dialogPageRevision = null, dialogPagePending = false;
function dialogElement(tag,className,text) { const el = document.createElement(tag); if(className) el.className=className; if(text!==undefined) el.textContent=text; return el; }
function documentLink(item,className,label=item.title) {
  const link=dialogElement('a',className,label); link.href=item.url;
  if(new URL(item.url,location.href).origin !== location.origin) { link.target='_blank'; link.rel='noopener noreferrer'; }
  return link;
}
async function refreshDialogPage() {
  if(dialogPagePending) return; dialogPagePending=true;
  try {
    const response=await fetch('/api/dialog-links',{cache:'no-store'}); if(!response.ok) return;
    const data=await response.json(); if(!Array.isArray(data.links) || data.revision===dialogPageRevision) return;
    const links=data.links.filter(item=>item.active);
    const documents=document.querySelector('[data-dialog-documents]');
    documents.replaceChildren(...links.filter(item=>item.section==='documents').map(item=>documentLink(item,'action-btn',item.title+' ↗')));
    if(!documents.childElementCount) documents.append(dialogElement('p','section-intro','Belum ada dokumen yang ditampilkan.'));
    const months=document.querySelector('[data-dialog-months]');
    months.replaceChildren(...links.filter(item=>item.section==='monthly').sort((a,b)=>a.month-b.month).map(item=>{
      if(item.url) return documentLink(item,'month-btn');
      const placeholder=dialogElement('span','month-btn unavailable',item.title); placeholder.append(dialogElement('small','','Belum tersedia')); return placeholder;
    }));
    if(!months.childElementCount) months.append(dialogElement('p','section-intro','Belum ada folder bulanan yang ditampilkan.'));
    const units=document.querySelector('[data-dialog-units]'); const groups=new Map();
    links.filter(item=>item.section==='units').forEach(item=>{ if(!groups.has(item.unit)) groups.set(item.unit,[]); groups.get(item.unit).push(item); });
    const knownMarks={'Subbagian Umum':'UM','Seksi Penindakan dan Penyidikan':'P2','Seksi Perbendaharaan':'PB','Seksi Pelayanan Kepabeanan dan Cukai dan Dukungan Teknis':'PKC','Seksi Kepatuhan Internal dan Penyuluhan':'KI'};
    units.replaceChildren(...[...groups.entries()].map(([unit,items])=>{
      const card=dialogElement('div','unit-card'); const mark=dialogElement('div','unit-emblem',knownMarks[unit] || '↗'); mark.setAttribute('aria-hidden','true');
      const body=dialogElement('div','unit-body'); body.append(dialogElement('h3','unit-name',unit));
      const buttons=dialogElement('div','unit-btns'); buttons.append(...items.map(item=>documentLink(item,'unit-btn'))); body.append(buttons); card.append(mark,body); return card;
    }));
    if(!units.childElementCount) units.append(dialogElement('p','section-intro','Belum ada dokumen unit kerja yang ditampilkan.'));
    dialogPageRevision=data.revision;
  } catch { /* Existing page content stays available when the API cannot be reached. */ }
  finally { dialogPagePending=false; }
}
refreshDialogPage();
window.addEventListener('focus',refreshDialogPage);
window.addEventListener('pageshow',refreshDialogPage);
setInterval(()=>{if(!document.hidden) refreshDialogPage();},60000);
