(() => { const root=document.documentElement, button=document.getElementById('themeToggle'); const saved=localStorage.getItem('ktn-theme'); if(saved) root.dataset.bsTheme=saved; button?.addEventListener('click',()=>{const next=root.dataset.bsTheme==='dark'?'light':'dark';root.dataset.bsTheme=next;localStorage.setItem('ktn-theme',next)}); })();

