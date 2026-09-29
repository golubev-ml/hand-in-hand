/*
  Карусель рисунков галереи на лендинге. Без сторонних библиотек.

  Данные: GET <основной сайт>/api/pictures?status=available — поле img приходит
  путём вида /uploads/xxx.jpg, поэтому перед ним подставляется origin галереи
  (взятого из ссылки плашки, то есть из env SITE_URL).
  Если API недоступно (лендинг открыт без основного сайта, CORS, таймаут) —
  рисуется статичный массив-заглушка STUB: его можно заменить на реальные данные,
  не трогая вёрстку.
*/
(function () {
  'use strict';

  var MAX_ITEMS = 7;
  var AUTOSROLL_MS = 5000;
  var FETCH_TIMEOUT_MS = 4500;

  var STUB = [
    { title: 'Солнце над Казанью', author: 'Амина', age: 8, price: 1500 },
    { title: 'Мой кот Барсик', author: 'Тимур', age: 6, price: 1000 },
    { title: 'Мама и я', author: 'Даша', age: 9, price: 2000 },
    { title: 'Радуга для друга', author: 'Лев', age: 7, price: 1200 },
    { title: 'Подводный мир', author: 'Соня', age: 10, price: 1800 },
    { title: 'Первый снег', author: 'Юсуф', age: 5, price: 900 },
    { title: 'Дом, где живут мечты', author: 'Вера', age: 11, price: 2500 }
  ];

  var PALETTE = [
    ['#FFE9C7', '#FFB37E'], ['#E7F0FF', '#9CB8E8'], ['#FDE3EC', '#F0A6C0'],
    ['#E6F5EA', '#9CCBA9'], ['#FFF3D1', '#F2C879'], ['#EFE6FB', '#B79BE0'],
    ['#E4F4F6', '#8FC3CC']
  ];

  /* Заглушка вместо внешней картинки: рисуем «детский рисунок» прямо в SVG. */
  function stubImage(i) {
    var c = PALETTE[i % PALETTE.length];
    var svg = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 400 300">'
      + '<defs><linearGradient id="g" x1="0" y1="0" x2="0" y2="1">'
      + '<stop offset="0" stop-color="' + c[0] + '"/><stop offset="1" stop-color="' + c[1] + '"/>'
      + '</linearGradient></defs>'
      + '<rect width="400" height="300" fill="url(#g)"/>'
      + '<circle cx="320" cy="60" r="30" fill="#FFD34E" stroke="#E2A32A" stroke-width="4"/>'
      + '<path d="M0 230 Q100 170 200 225 T400 215 V300 H0Z" fill="#7FB08A" opacity=".85"/>'
      + '<path d="M60 250 l18-46 18 46z" fill="#4A7C59"/>'
      + '<circle cx="200" cy="150" r="26" fill="#fff" stroke="#2268b1" stroke-width="5"/>'
      + '<path d="M186 152c6-10 22-10 28 0" stroke="#de789d" stroke-width="5" fill="none" stroke-linecap="round"/>'
      + '<circle cx="192" cy="144" r="3.5" fill="#2C2416"/><circle cx="208" cy="144" r="3.5" fill="#2C2416"/>'
      + '</svg>';
    return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg);
  }

  function $(id) { return document.getElementById(id); }

  /* Origin галереи берём из готовой ссылки плашки: её уже починил cross-link.js. */
  function galleryBase() {
    var link = $('xlink-gallery');
    if (link && link.href) {
      try { return new URL(link.href, window.location.href).origin; } catch (e) { /* noop */ }
    }
    // host, а не hostname — иначе теряется порт нестандартного стенда
    var host = window.location.host.replace(/^hand\./, '');
    return window.location.protocol + '//' + host;
  }

  function pictureUrl(img, base) {
    if (!img) return '';
    if (/^https?:\/\//i.test(img)) return img;
    return base + (img.charAt(0) === '/' ? img : '/' + img);
  }

  function fetchPictures(base) {
    if (!window.fetch || !window.AbortController) { return Promise.resolve(null); }
    var ctrl = new AbortController();
    var timer = setTimeout(function () { ctrl.abort(); }, FETCH_TIMEOUT_MS);
    return fetch(base + '/api/pictures?status=available', { signal: ctrl.signal, credentials: 'omit' })
      .then(function (r) {
        if (!r.ok) { throw new Error('http ' + r.status); }
        return r.json();
      })
      .then(function (list) {
        clearTimeout(timer);
        return Array.isArray(list) && list.length ? list.slice(0, MAX_ITEMS) : null;
      })
      .catch(function () { clearTimeout(timer); return null; });
  }

  function money(n) {
    var v = Math.round(Number(n) || 0);
    return v ? v.toLocaleString('ru-RU') + ' ₽' : 'Дар';
  }

  function esc(s) {
    return String(s == null ? '' : s).replace(/[&<>"]/g, function (ch) {
      return { '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;' }[ch];
    });
  }

  function card(item, i, base) {
    var img = item.img ? pictureUrl(item.img, base) : stubImage(i);
    var author = item.author ? esc(item.author) + (item.age ? ', ' + esc(item.age) : '') : 'юный художник';
    var el = document.createElement('a');
    el.className = 'gc-card';
    el.href = base + '/#gallery';
    el.setAttribute('aria-label', 'Открыть галерею: ' + esc(item.title));
    el.innerHTML =
      '<span class="gc-frame"><img src="' + img + '" alt="' + esc(item.title) + '" loading="lazy" draggable="false"></span>'
      + '<span class="gc-meta"><span class="gc-title">' + esc(item.title) + '</span>'
      + '<span class="gc-author">' + author + '</span></span>'
      + '<span class="gc-price">' + money(item.price) + '</span>';
    return el;
  }

  function initCarousel(view, track, prev, next, dots) {
    var step = function () {
      var first = track.querySelector('.gc-card');
      if (!first) { return view.clientWidth * 0.8; }
      return first.getBoundingClientRect().width + 20;
    };
    var pages = function () {
      if (!view.clientWidth) { return 1; }        // раскладка ещё не готова
      return Math.max(1, Math.ceil((track.scrollWidth - view.clientWidth) / step()) + 1);
    };
    var index = function () {
      return Math.min(pages() - 1, Math.round(view.scrollLeft / step()));
    };
    var reduced = window.matchMedia && window.matchMedia('(prefers-reduced-motion: reduce)').matches;

    function paint() {
      var n = pages();
      var active = index();
      dots.textContent = '';
      for (var i = 0; i < n; i++) {
        var b = document.createElement('button');
        b.type = 'button';
        b.className = 'gc-dot' + (i === active ? ' is-on' : '');
        b.setAttribute('role', 'tab');
        b.setAttribute('aria-label', 'Слайд ' + (i + 1));
        b.setAttribute('aria-selected', i === active ? 'true' : 'false');
        (function (target) {
          b.addEventListener('click', function () { go(target * step()); });
        })(i);
        dots.appendChild(b);
      }
      var overflow = track.scrollWidth > view.clientWidth + 4;
      prev.disabled = !overflow;
      next.disabled = !overflow;
      view.parentNode.classList.toggle('gc-single', !overflow);
    }

    function go(left) { view.scrollTo({ left: left, behavior: reduced ? 'auto' : 'smooth' }); }
    function advance(dir) {
      var max = track.scrollWidth - view.clientWidth;
      var to = view.scrollLeft + dir * step();
      if (to > max + 4) { to = 0; }                  // автопереход в начало
      if (to < -4) { to = max; }
      go(to);
    }

    prev.addEventListener('click', function () { advance(-1); });
    next.addEventListener('click', function () { advance(1); });
    var t;
    view.addEventListener('scroll', function () { clearTimeout(t); t = setTimeout(paint, 120); }, { passive: true });
    window.addEventListener('resize', paint);

    if (!reduced) {
      var timer = null;
      var play = function () { if (!timer) { timer = setInterval(function () { advance(1); }, AUTOSROLL_MS); } };
      var stop = function () { clearInterval(timer); timer = null; };
      ['mouseenter', 'focusin', 'touchstart', 'pointerdown'].forEach(function (ev) {
        view.parentNode.addEventListener(ev, stop, { passive: true });
      });
      ['mouseleave', 'focusout'].forEach(function (ev) {
        view.parentNode.addEventListener(ev, play, { passive: true });
      });
      document.addEventListener('visibilitychange', function () {
        if (document.hidden) { stop(); } else { play(); }
      });
      play();
    }
    paint();

    // Первая разметка может измеряться до загрузки шрифтов и картинок
    // (clientWidth = 0 → лишние точки). Пересчитываем по событиям разметки.
    var remeasure = function () { paint(); };
    if (window.ResizeObserver) { new ResizeObserver(remeasure).observe(view); }
    window.addEventListener('load', remeasure);
    Array.prototype.forEach.call(track.querySelectorAll('img'), function (img) {
      if (!img.complete) { img.addEventListener('load', remeasure, { once: true }); }
    });
  }

  function render(items, base) {
    var view = $('gcView'), track = $('gcTrack'), dots = $('gcDots');
    var prev = $('gcPrev'), next = $('gcNext'), box = $('gc');
    if (!view || !track || !dots || !box) { return; }
    track.textContent = '';
    items.forEach(function (item, i) { track.appendChild(card(item, i, base)); });
    box.hidden = false;
    initCarousel(view, track, prev, next, dots);
  }

  function boot() {
    var base = galleryBase();
    var all = $('gcAll');
    if (all) { all.href = base + '/#gallery'; }
    fetchPictures(base).then(function (list) {
      render(list || STUB.map(function (s) { return Object.assign({ img: '' }, s); }), base);
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', boot);
  } else {
    boot();
  }
})();
