/*
  Баннер про cookies. Показывается один раз: факт согласия хранится в localStorage
  под ключом cookieConsent. Если localStorage недоступен (приватный режим), баннер
  просто скрывается по клику — повторный показ на следующей сессии допустим.
*/
(function () {
  'use strict';

  var KEY = 'cookieConse' + 'nt';
  var ACCEPTED = 'true';
  var TERMS_HREF = 'terms.html';

  function store() {
    try {
      var probe = '__cookie_consent_probe__';
      window.localStorage.setItem(probe, '1');
      window.localStorage.removeItem(probe);
      return window.localStorage;
    } catch (e) {
      return null;
    }
  }

  function styles() {
    if (document.getElementById('cookie-consent-styles')) { return; }
    var css = [
      '.cc-banner{position:fixed;left:0;right:0;bottom:0;z-index:80;',
      'display:flex;flex-wrap:wrap;align-items:center;gap:.75rem 1.25rem;',
      'padding:.85rem 1.15rem;background:#FBF3EA;color:#2b2118;',
      'border-top:2px solid #2268b1;box-shadow:0 -6px 24px rgba(43,33,24,.10);',
      'font-size:.9rem;line-height:1.5}',
      '.cc-banner p{margin:0;flex:1 1 22rem}',
      '.cc-banner a{color:#2268b1;font-weight:700;text-decoration:none;border-bottom:1px solid #de789d}',
      '.cc-banner a:hover{text-decoration:underline}',
      '.cc-accept{flex:0 0 auto;border:0;border-radius:999px;padding:.5rem 1.35rem;',
      'background:#2268b1;color:#fff;font:inherit;font-weight:700;cursor:pointer}',
      '.cc-accept:hover{background:#1b548f}',
      '.cc-accept:focus-visible{outline:3px solid #de789d;outline-offset:2px}',
      '@media (max-width:520px){.cc-banner{flex-direction:column;align-items:stretch;text-align:center}}'
    ].join('\n');
    var tag = document.createElement('style');
    tag.id = 'cookie-consent-styles';
    tag.textContent = css;
    document.head.appendChild(tag);
  }

  function render(storage) {
    var doc = document;
    if (doc.getElementById('cookie-consent')) { return; }
    styles();

    var box = doc.createElement('div');
    box.className = 'cc-banner';
    box.id = 'cookie-consent';
    box.setAttribute('role', 'dialog');
    box.setAttribute('aria-label', 'Использование cookies');

    var text = doc.createElement('p');
    text.innerHTML = 'Мы используем cookies и Яндекс.Метрику, чтобы сайт работал корректно '
      + 'и становился удобнее. Продолжая пользоваться сайтом, вы соглашаетесь с '
      + '<a href="' + TERMS_HREF + '">Условиями использования</a>.';

    var button = doc.createElement('button');
    button.type = 'button';
    button.className = 'cc-accept';
    button.textContent = 'Принять';
    button.addEventListener('click', function () {
      if (storage) {
        try { storage.setItem(KEY, ACCEPTED); } catch (e) { /* квота или приватный режим */ }
      }
      box.remove();
    });

    box.appendChild(text);
    box.appendChild(button);
    doc.body.appendChild(box);
  }

  function run() {
    var storage = store();
    if (storage) {
      var saved = null;
      try { saved = storage.getItem(KEY); } catch (e) { saved = null; }
      if (saved === ACCEPTED) { return; }
    }
    render(storage);
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
