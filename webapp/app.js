(() => {
  const tg = window.Telegram?.WebApp;
  tg?.ready(); tg?.expand();
  const $ = (id) => document.getElementById(id);
  const views = ['home','listings','profile','admin','form'];
  const listings = [];
  let selectedFiles = [];
  const showToast = (message) => { const el=$('toast'); el.textContent=message; el.classList.add('show'); setTimeout(()=>el.classList.remove('show'),2600); };
  function showView(name){ views.forEach(v=>$(v+'View')?.classList.toggle('hidden',v!==name)); document.querySelectorAll('.tab').forEach(t=>t.classList.toggle('active',t.dataset.view===name)); }
  document.querySelectorAll('.tab').forEach(t=>t.addEventListener('click',()=>showView(t.dataset.view)));
  $('startListing').onclick=()=>showView('form'); $('newListing').onclick=()=>showView('form'); $('closeForm').onclick=()=>showView('home');
  const user=tg?.initDataUnsafe?.user;
  if(user){ $('profileName').textContent=[user.first_name,user.last_name].filter(Boolean).join(' ')||'SMDC Seller'; $('profileId').textContent='Telegram ID: '+user.id; }
  // Admin UI is intentionally not enabled from client-side data. Backend must authorize admins.
  $('mediaInput').addEventListener('change',e=>{
    selectedFiles=Array.from(e.target.files||[]);
    const box=$('mediaPreview'); box.innerHTML='';
    selectedFiles.forEach(file=>{const url=URL.createObjectURL(file);let node;if(file.type.startsWith('image/')){node=document.createElement('img');node.src=url;}else if(file.type.startsWith('video/')){node=document.createElement('video');node.src=url;node.muted=true;node.controls=true;}else return;box.appendChild(node);});
  });
  $('listingForm').addEventListener('submit',e=>{
    e.preventDefault(); const data=Object.fromEntries(new FormData(e.currentTarget).entries());
    const item={...data,id:Date.now(),status:'На проверке',media:selectedFiles.length}; listings.unshift(item);
    $('homeCount').textContent=listings.length; renderListings(); e.currentTarget.reset(); selectedFiles=[]; $('mediaPreview').innerHTML='';
    showToast('Черновик создан. Для реальной отправки нужен подключённый сервер.'); showView('listings');
  });
  function renderListings(){const box=$('listingList');box.innerHTML='';if(!listings.length){box.className='empty-state';box.innerHTML='<div class="empty-symbol">▧</div><b>Пока здесь пусто</b><p>Твои объявления появятся здесь после создания.</p>';return;}box.className='';listings.forEach(item=>{const card=document.createElement('article');card.className='listing-card';const title=document.createElement('b');title.textContent=item.title;const meta=document.createElement('small');meta.textContent=`${item.price} ${item.currency} · ${item.media} медиа · ${item.status}`;card.append(title,meta);box.appendChild(card);});}
})();
