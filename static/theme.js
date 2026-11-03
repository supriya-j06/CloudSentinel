(function(){
  let saved=null;
  try { saved=localStorage.getItem('cloudsentinel-theme'); } catch(e) {}
  // Apply the saved theme immediately to avoid a bright flash on page load.
  const preferred=window.matchMedia&&window.matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';
  document.documentElement.dataset.theme=saved||preferred;
  function addToggle(){
    if(document.querySelector('.cs-theme-toggle'))return;
    const b=document.createElement('button');b.type='button';b.className='cs-theme-toggle';
    function paint(){const dark=document.documentElement.dataset.theme==='dark';b.textContent=dark?'☀ Light mode':'☾ Dark mode';b.setAttribute('aria-label',dark?'Switch to light mode':'Switch to dark mode');}
    b.addEventListener('click',()=>{const next=document.documentElement.dataset.theme==='dark'?'light':'dark';document.documentElement.dataset.theme=next;try { localStorage.setItem('cloudsentinel-theme',next); } catch(e) {}
      paint();});
    document.body.appendChild(b);paint();
  }
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',addToggle);else addToggle();
})();
