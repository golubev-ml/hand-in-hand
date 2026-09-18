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
    'Банковские реквизиты для пожертвований — по запросу: rukaobruku.fond@gmail.com';

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

  /* ---------- Цели Яндекс.Метрики (ID приходит из env YANDEX_METRIKA_ID) ----------
     ВАЖНО (почему в кабинете может быть 0 при живых запросах в DevTools):
     1) Статистика визитов и конверсий обновляется с задержкой до 24 часов —
        сразу после установки счётчика «0 посещений» это нормально.
     2) Цели нужно завести в интерфейсе Яндекс.Метрики:
        Настройки счётчика → «Цели» → Добавить цель, тип «JavaScript-событие»,
        точные имена: donate_click, volunteer_click, copy_requisites, nav_click,
                      pay_create, pay_success.
        Без заведённых целей reachGoal-события в отчёты не попадут.
     3) pay_create/pay_success срабатывают только при включённой онлайн-оплате
        (paymentsEnabled=true в админке). Пока оплата выключена — этих событий нет. */
  function ymGoal(name, params) {
    /* guard: если счётчик не загрузился (adblock, пустой YANDEX_METRIKA_ID) — молча пропускаем.
       ID берём из window.YM_ID (его публикует index.html), чтобы не держать его в двух местах */
    try {
      var id = Number(window.YM_ID);
      if (id && typeof window.ym === 'function') window.ym(id, 'reachGoal', name, params);
    } catch (e) { /* noop */ }
  }

  /* клик по любой кнопке "Пожертвовать" (шапка, hero, футер) = открытие модалки */
  doc.querySelectorAll('.js-open-modal, .hdr-cta, .hero-actions .btn-terra').forEach(function (btn) {
    btn.addEventListener('click', function () { ymGoal('donate_click'); });
  });

  /* "Стать волонтёром" и переходы к разделу "Как помочь" */
  doc.querySelectorAll('a[href="#volunteer"], .link-arrow').forEach(function (link) {
    link.addEventListener('click', function () { ymGoal('volunteer_click'); });
  });

  /* копирование реквизитов в модалке */
  doc.querySelectorAll('.js-copy-all').forEach(function (btn) {
    btn.addEventListener('click', function () { ymGoal('copy_requisites'); });
  });

  /* переходы по навигационным ссылкам шапки (цель nav_click + секция в параметрах) */
  doc.querySelectorAll('#nav a').forEach(function (a) {
    a.addEventListener('click', function () {
      ymGoal('nav_click', { section: a.getAttribute('href') });
    });
  });

  /* ---------- Онлайн-оплата ----------
     Кнопки оплаты есть в разметке, но скрыты (.pay-block { display:none }).
     Появляются ТОЛЬКО если бэкенд ответил paymentsEnabled:true.
     Бэкенд может лежать, отсутствовать вовсе или быть отрезан блокировщиком —
     тогда страница ведёт себя ровно как до подключения оплаты. */

  var PAY_API = '/api'; /* API на корне домена: https://hand-in-hand-kzn.ru/api/... */

  var payBlock = doc.getElementById('payBlock');
  var payGo = doc.getElementById('payGo');
  var payHint = doc.getElementById('payHint');
  var payCustom = doc.getElementById('payCustom');
  var payState = { enabled: false, sum: 0, method: '', min: 10, max: 1500000 };

  function setPayHint(text) {
    if (payHint) payHint.textContent = text;
  }

  /** fetch + разбор JSON + таймаут. Сообщение ошибки берём от бэкенда, если он его вернул. */
  function fetchJson(url, options, timeoutMs) {
    var opts = options || {};
    var timer = null;
    if (window.AbortController && timeoutMs) {
      var controller = new AbortController();
      opts.signal = controller.signal;
      timer = setTimeout(function () { controller.abort(); }, timeoutMs);
    }
    return fetch(url, opts).then(function (res) {
      if (timer) clearTimeout(timer);
      return res.json().catch(function () { return {}; }).then(function (data) {
        if (!res.ok) throw new Error(data && data.error ? data.error : 'Ошибка сервера');
        return data;
      });
    }, function (e) {
      if (timer) clearTimeout(timer);
      throw e;
    });
  }

  function refreshPayButton() {
    if (!payGo) return;
    var ok = payState.enabled && payState.sum >= payState.min && payState.sum <= payState.max && Boolean(payState.method);
    payGo.disabled = !ok;
    if (ok) setPayHint('Переведём на защищённую страницу банка');
    else if (!payState.sum) setPayHint('Выберите сумму');
    else if (!payState.method) setPayHint('Выберите способ оплаты');
    else setPayHint('Сумма от ' + payState.min + ' до ' + payState.max.toLocaleString('ru-RU') + ' ₽');
  }

  function selectSum(rub) {
    payState.sum = Number(rub) || 0;
    doc.querySelectorAll('#paySums .pay-sum').forEach(function (b) {
      b.classList.toggle('sel', Number(b.getAttribute('data-sum')) === payState.sum);
    });
    refreshPayButton();
  }

  function selectMethod(method) {
    payState.method = method;
    doc.querySelectorAll('#payMethods .pay-method').forEach(function (b) {
      b.classList.toggle('sel', b.getAttribute('data-method') === method);
    });
    refreshPayButton();
  }

  function startPayment() {
    if (!payGo || payGo.disabled) return;
    payGo.disabled = true;
    setPayHint('Создаём платёж…');

    var kopecks = Math.round(payState.sum * 100);
    fetchJson(PAY_API + '/payments/create', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ orderId: makeOrderNumber(), amount: kopecks, method: payState.method })
    }, 25000).then(function (res) {
      if (!res || !res.redirectUrl) throw new Error('банк не вернул ссылку на оплату');
      ymGoal('pay_create', { method: payState.method, amount: kopecks });
      setPayHint('Открываем страницу банка…');
      window.location.href = res.redirectUrl;
    }).catch(function (e) {
      payGo.disabled = false;
      setPayHint('Не получилось начать оплату — ' + (e && e.message ? e.message : 'нет связи с сервером') +
        '. Можно перевести по реквизитам ниже.');
    });
  }

  /** Номер заказа: HH + YYMMDDHHMMSS + 4 случайных hex. Укладывается в [A-Z0-9_-]{4,20}. */
  function makeOrderNumber() {
    var d = new Date();
    function pad(n) { return (n < 10 ? '0' : '') + n; }
    var rnd = Math.floor(Math.random() * 0xffff).toString(16).toUpperCase();
    while (rnd.length < 4) rnd = '0' + rnd;
    return ('HH' + String(d.getFullYear()).slice(2) + pad(d.getMonth() + 1) + pad(d.getDate()) +
      pad(d.getHours()) + pad(d.getMinutes()) + pad(d.getSeconds()) + rnd).slice(0, 20);
  }

  function enablePayments(cfg) {
    payState.enabled = true;
    payState.min = Math.ceil((cfg.minAmountKopecks || 1000) / 100);
    payState.max = Math.floor((cfg.maxAmountKopecks || 150000000) / 100);
    payState.chips = [300, 500, 1000].filter(function (v) { return v >= payState.min && v <= payState.max; });

    if (payCustom) {
      payCustom.setAttribute('min', payState.min);
      payCustom.setAttribute('max', payState.max);
    }
    var allowed = cfg.methods || ['sbp', 'mirpay', 'sberpay'];
    doc.querySelectorAll('#payMethods .pay-method').forEach(function (b) {
      if (allowed.indexOf(b.getAttribute('data-method')) === -1) b.style.display = 'none';
    });
    payBlock.classList.add('pay-on');
    /* предвыбираем 500 ₽ — самая частая сумма пожертвования, если она в допустимом диапазоне */
    if (payState.chips.length) selectSum(payState.chips.indexOf(500) > -1 ? 500 : payState.chips[0]);
    else refreshPayButton();
  }

  function loadPayConfig() {
    if (!payBlock || typeof window.fetch !== 'function') return;
    fetchJson(PAY_API + '/config', { cache: 'no-store' }, 5000).then(function (cfg) {
      /* false / нет ответа / истёк таймаут — оплату не показываем */
      if (cfg && cfg.paymentsEnabled === true) enablePayments(cfg);
    }).catch(function () { /* бэкенда нет — оставляем прежнее поведение */ });
  }

  if (payGo) payGo.addEventListener('click', startPayment);
  doc.querySelectorAll('#paySums .pay-sum').forEach(function (b) {
    b.addEventListener('click', function () {
      if (payCustom) payCustom.value = '';
      selectSum(Number(b.getAttribute('data-sum')));
    });
  });
  doc.querySelectorAll('#payMethods .pay-method').forEach(function (b) {
    b.addEventListener('click', function () { selectMethod(b.getAttribute('data-method')); });
  });
  if (payCustom) {
    payCustom.addEventListener('input', function () {
      var v = Math.floor(Number(payCustom.value));
      if (!v) { payState.sum = 0; refreshPayButton(); return; }
      selectSum(v);
    });
  }

  /* Баннер по результату редиректа от банка: /variant2/?payment=success */
  function showPaymentResult() {
    var m = /[?&]payment=([^&]+)/.exec(window.location.search || '');
    if (!m) return;
    var status = decodeURIComponent(m[1]);
    var messages = {
      success: 'Спасибо! Платёж прошёл — вы очень помогли.',
      pending: 'Платёж принят, банк его подтверждает. Если деньги списались — спасибо!',
      failed: 'Оплата не прошла. Попробуйте ещё раз или переведите по реквизитам.',
      unknown: 'Не удалось найти этот платёж. Напишите нам, если деньги списались.',
      back: 'Возврат на сайт.'
    };
    if (status === 'success') ymGoal('pay_success');
    if (messages[status]) showToast(messages[status]);

    /* убираем только payment=, utm-метки и прочие параметры сохраняем */
    if (window.history && window.history.replaceState && window.URLSearchParams) {
      var params = new URLSearchParams(window.location.search);
      params.delete('payment');
      var qs = params.toString();
      window.history.replaceState({}, '', window.location.pathname + (qs ? '?' + qs : '') + window.location.hash);
    }
  }

  loadPayConfig();
  showPaymentResult();
})();
