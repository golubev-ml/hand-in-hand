/*
  Ссылки на основной сайт (галерею рисунков).

  Домен не зашит: в index.html стоит ${SITE_URL}, который nginx подставляет из env
  при старте контейнера. Если переменная не задана (локальный просмотр файлов,
  сборка без env), ссылка чинится из hostname текущей витрины: лендинг живёт на
  поддомене hand.<домен-сайта>, поэтому основной сайт — это hostname без префикса.
*/
(function () {
  'use strict';

  var PLACEHOLDER = '${' + 'SITE_URL}';

  function galleryOrigin() {
    // host, а не hostname: hostname режет порт, и на нестандартном порту
    // (локальный просмотр, стенд) ссылка уходила бы на 80-й
    var host = window.location.host || 'localhost';
    if (host.indexOf('hand.') === 0) {
      host = host.slice('hand.'.length);
    }
    return window.location.protocol + '//' + host;
  }

  function fix() {
    var links = document.querySelectorAll('[data-gallery-href]');
    for (var i = 0; i < links.length; i++) {
      var el = links[i];
      var href = el.getAttribute('href') || '';
      if (!href || href.indexOf(PLACEHOLDER) !== -1) {
        var rest = href.replace(PLACEHOLDER, '') || '/';
        el.setAttribute('href', galleryOrigin() + (rest.charAt(0) === '/' ? rest : '/' + rest));
      }
    }
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', fix);
  } else {
    fix();
  }
})();
