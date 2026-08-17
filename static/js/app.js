(() => {
  'use strict';

  const root = document.documentElement;
  const themeButton = document.getElementById('themeToggle');
  const savedTheme = localStorage.getItem('ktn-theme');

  if (savedTheme) root.dataset.bsTheme = savedTheme;
  themeButton?.addEventListener('click', () => {
    const nextTheme = root.dataset.bsTheme === 'dark' ? 'light' : 'dark';
    root.dataset.bsTheme = nextTheme;
    localStorage.setItem('ktn-theme', nextTheme);
  });

  const hasAdCode = (container) => Boolean(
    container?.querySelector('script, iframe, ins, img, video, object, embed') ||
    container?.textContent.trim()
  );

  const overlay = document.getElementById('clickAdOverlay');
  const closeButton = document.getElementById('clickAdClose');
  const adContent = overlay?.querySelector('.click-ad-content');
  const clickAdEnabled = overlay?.dataset.adEnabled === 'true' && hasAdCode(adContent);
  let pendingNavigation = null;
  let previouslyFocused = null;

  const finishPendingNavigation = () => {
    if (!pendingNavigation) return;
    const { href, target } = pendingNavigation;
    pendingNavigation = null;
    if (target === '_blank') window.open(href, '_blank', 'noopener');
    else window.location.assign(href);
  };

  const closeClickAd = () => {
    if (!overlay || overlay.hidden) return;
    overlay.classList.remove('is-visible');
    overlay.setAttribute('aria-hidden', 'true');
    overlay.hidden = true;
    document.body.classList.remove('click-ad-open');
    previouslyFocused?.focus?.();
    finishPendingNavigation();
  };

  const showClickAd = () => {
    if (!overlay || !closeButton) return;
    sessionStorage.setItem('dyNewsClickAdShown', '1');
    previouslyFocused = document.activeElement;
    overlay.hidden = false;
    overlay.setAttribute('aria-hidden', 'false');
    requestAnimationFrame(() => overlay.classList.add('is-visible'));
    document.body.classList.add('click-ad-open');
    closeButton.focus();
  };

  const firstMeaningfulClick = (event) => {
    if (event.defaultPrevented || event.button !== 0 || event.target.closest('#clickAdOverlay, .ad-placement')) return;

    const link = event.target.closest('a[href]');
    if (link && !link.href.startsWith('javascript:') && !link.hasAttribute('download')) {
      event.preventDefault();
      pendingNavigation = { href: link.href, target: link.target };
    }

    document.removeEventListener('click', firstMeaningfulClick, true);
    showClickAd();
  };

  if (clickAdEnabled && !sessionStorage.getItem('dyNewsClickAdShown')) {
    document.addEventListener('click', firstMeaningfulClick, true);
    closeButton?.addEventListener('click', closeClickAd);
    overlay?.addEventListener('click', (event) => {
      if (event.target === overlay) closeClickAd();
    });
    document.addEventListener('keydown', (event) => {
      if (event.key === 'Escape' && !overlay.hidden) closeClickAd();
    });
  } else if (overlay) {
    overlay.hidden = true;
  }

  const bottomAd = document.getElementById('bottomAd');
  const bottomAdContent = bottomAd?.querySelector('.bottom-ad-content');
  const bottomAdEnabled = bottomAd?.dataset.adEnabled === 'true' && hasAdCode(bottomAdContent);

  if (bottomAdEnabled) {
    bottomAd.hidden = false;
    bottomAd.setAttribute('aria-hidden', 'false');
    document.getElementById('bottomAdClose')?.addEventListener('click', () => {
      bottomAd.hidden = true;
      bottomAd.setAttribute('aria-hidden', 'true');
    });
  } else if (bottomAd) {
    bottomAd.hidden = true;
  }
})();
