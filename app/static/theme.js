/* Theme preference: system default, light, or dark. */
(() => {
  const modes=['auto','light','dark'];
  const prefersDark=window.matchMedia('(prefers-color-scheme: dark)');
  let mode='auto';
  try{const saved=localStorage.getItem('lectoriumTheme');if(modes.includes(saved))mode=saved}catch{}
  const labels={auto:'Авто',light:'Светлая',dark:'Тёмная'};
  const icons={auto:'◐',light:'☼',dark:'☾'};
  function render(){
    const resolved=mode==='auto'?(prefersDark.matches?'dark':'light'):mode;
    document.documentElement.dataset.theme=resolved;
    const button=document.querySelector('#themeButton');
    if(!button)return;
    button.dataset.mode=mode;
    const icon=button.querySelector('[data-theme-icon]'),label=button.querySelector('[data-theme-label]');
    if(icon)icon.textContent=icons[mode];
    if(label)label.textContent=window.t?.(labels[mode])||labels[mode];
    const title=window.t?.(`Сменить тему сайта: ${mode==='auto'?'автоматически':mode==='light'?'светлая':'тёмная'}`)||`Сменить тему сайта: ${labels[mode].toLowerCase()}`;
    button.setAttribute('aria-label',title);button.title=title;
  }
  function init(){
    const button=document.querySelector('#themeButton');
    button?.addEventListener('click',()=>{mode=modes[(modes.indexOf(mode)+1)%modes.length];try{localStorage.setItem('lectoriumTheme',mode)}catch{}render()});
    window.addEventListener('lectorium:language-change',render);
    prefersDark.addEventListener?.('change',()=>{if(mode==='auto')render()});
    render();
  }
  document.documentElement.dataset.theme=mode==='auto'?(prefersDark.matches?'dark':'light'):mode;
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',init,{once:true});else init();
  window.setSiteTheme=next=>{if(!modes.includes(next))return;mode=next;try{localStorage.setItem('lectoriumTheme',mode)}catch{}render()};
})();
