/* АНО БП «Рука об руку» — Вариант 2. Логика страницы. */
(function () {
  'use strict';

  var doc = document;

  /* ---------- Шапка ---------- */
  var hdr = doc.getElementById('hdr');
  window.addEventListener('scroll', function () {
    if (hdr) hdr.classList.toggle('scrolled', window.scrollY > 8);
  }, { passive: true });

  /* ---------- Мобильное меню ---------- */
  var burger = doc.getElementById('burger');
  if (burger) {
    burger.addEventListener('click', function () {
      var open = doc.body.classList.toggle('menu-open');
      burger.setAttribute('aria-expanded', open ? 'true' : 'false');
    });
    doc.querySelectorAll('#nav a').forEach(function (a) {
      a.addEventListener('click', function () {
        doc.body.classList.remove('menu-open');
        burger.setAttribute('aria-expanded', 'false');
      });
    });
  }

  /* ---------- Тост ---------- */
  var toast = doc.getElementById('toast');
  var toastTimer = null;
  function showToast(msg) {
    if (!toast) return;
    toast.textContent = msg;
    toast.classList.add('show');
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toast.classList.remove('show'); }, 2400);
  }

  function copyText(text, done) {
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(text).then(done, function () { fallbackCopy(text); done(); });
    } else { fallbackCopy(text); done(); }
  }
  function fallbackCopy(text) {
    var ta = doc.createElement('textarea');
    ta.value = text;
    ta.style.position = 'fixed';
    ta.style.opacity = '0';
    doc.body.appendChild(ta);
    ta.select();
    try { doc.execCommand('copy'); } catch (e) { /* noop */ }
    doc.body.removeChild(ta);
  }

  /* ---------- Модальное окно ---------- */
  var modal = doc.getElementById('modal');
  var lastFocus = null;
  function openModal() {
    if (!modal) return;
    lastFocus = doc.activeElement;
    modal.classList.add('open');
    modal.setAttribute('aria-hidden', 'false');
    doc.body.style.overflow = 'hidden';
    var close = modal.querySelector('.modal-x');
    if (close) close.focus();
  }
  function closeModal() {
    if (!modal) return;
    modal.classList.remove('open');
    modal.setAttribute('aria-hidden', 'true');
    doc.body.style.overflow = '';
    if (lastFocus && lastFocus.focus) lastFocus.focus();
  }
  doc.querySelectorAll('.js-open-modal').forEach(function (b) { b.addEventListener('click', openModal); });
  doc.querySelectorAll('.js-close-modal').forEach(function (b) { b.addEventListener('click', closeModal); });
  doc.addEventListener('keydown', function (ev) {
    if (ev.key === 'Escape') closeModal();
  });

  var REQUISITES =
    'АНО БП «Рука об руку»\n' +
    'ОГРН 1251600032870 (от 13.08.2025)\n' +
    'ИНН 1655509496 · КПП 165501001\n' +
    'Адрес: 420043, РТ, г. Казань, ул. Бойничная, д. 5, помещ. 6\n' +
    'Руководитель: Ахмадеева Алина Галиевна\n' +
    'Банковские реквизиты для пожертвований — по запросу: ahmadeeva.alina97@gmail.com';

  doc.querySelectorAll('.js-copy-all').forEach(function (b) {
    b.addEventListener('click', function () {
      copyText(REQUISITES, function () { showToast('Реквизиты скопированы — спасибо!'); });
    });
  });

  /* ---------- Слайдер историй ---------- */
  var track = doc.getElementById('sliderTrack');
  var dotsWrap = doc.getElementById('sliderDots');
  if (track && dotsWrap) {
    var slides = track.children;
    var count = slides.length;
    var idx = 0;
    var autoTimer = null;

    for (var i = 0; i < count; i++) {
      (function (k) {
        var d = doc.createElement('button');
        d.setAttribute('role', 'tab');
        d.setAttribute('aria-label', 'История ' + (k + 1));
        d.addEventListener('click', function () { go(k); restartAuto(); });
        dotsWrap.appendChild(d);
      })(i);
    }
    var dots = dotsWrap.children;

    function go(k) {
      idx = (k + count) % count;
      track.style.transform = 'translateX(-' + (idx * 100) + '%)';
      for (var j = 0; j < dots.length; j++) {
        dots[j].classList.toggle('active', j === idx);
      }
    }

    function restartAuto() {
      clearInterval(autoTimer);
      autoTimer = setInterval(function () { go(idx + 1); }, 6500);
    }

    var prev = doc.getElementById('prevSlide');
    var next = doc.getElementById('nextSlide');
    if (prev) prev.addEventListener('click', function () { go(idx - 1); restartAuto(); });
    if (next) next.addEventListener('click', function () { go(idx + 1); restartAuto(); });

    var slider = doc.getElementById('slider');
    if (slider) {
      slider.addEventListener('mouseenter', function () { clearInterval(autoTimer); });
      slider.addEventListener('mouseleave', restartAuto);
      /* свайп */
      var startX = null;
      slider.addEventListener('pointerdown', function (ev) { startX = ev.clientX; });
      slider.addEventListener('pointerup', function (ev) {
        if (startX === null) return;
        var dx = ev.clientX - startX;
        if (Math.abs(dx) > 48) { go(idx + (dx < 0 ? 1 : -1)); restartAuto(); }
        startX = null;
      });
    }

    go(0);
    restartAuto();
  }

  /* ---------- Донат-диаграмма ---------- */
  function paintDonut(root) {
    root.querySelectorAll('.seg').forEach(function (seg) {
      var len = parseFloat(seg.getAttribute('data-len')) || 0;
      seg.style.setProperty('--len', String(len));
      seg.style.strokeDasharray = len + ' ' + (100 - len);
    });
  }

  /* ---------- Появление блоков ---------- */
  var io = new IntersectionObserver(function (entries) {
    entries.forEach(function (en) {
      if (!en.isIntersecting) return;
      en.target.classList.add('in');
      if (en.target.classList.contains('donut-wrap')) paintDonut(en.target);
      io.unobserve(en.target);
    });
  }, { threshold: 0.18, rootMargin: '0px 0px -40px 0px' });

  doc.querySelectorAll('.reveal, .donut-wrap').forEach(function (el) { io.observe(el); });

  /* ---------- Лёгкий параллакс фото ---------- */
  var photo = doc.querySelector('.hero-photo');
  if (photo && window.matchMedia('(prefers-reduced-motion: no-preference)').matches) {
    window.addEventListener('scroll', function () {
      var y = Math.min(window.scrollY, 700);
      photo.style.transform = 'translateY(' + (y * 0.045) + 'px)';
    }, { passive: true });
  }
})();
