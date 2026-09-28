/*
  Подстановка домена на странице «Условия использования».
  Домен нигде не зашит: берётся hostname той витрины, на которой открыта страница,
  поэтому один и тот же файл корректен и на тестовом контуре, и на боевом.
*/
(function () {
  'use strict';

  var MARKER = '{{' + 'DOMAIN' + '}}';

  function host() {
    // window.location.hostname — единственный источник имени хоста
    return window.location.hostname || 'localhost';
  }

  function fill(node, value) {
    if (node.nodeType === 3) {                       // текстовый узел
      if (node.data.indexOf(MARKER) !== -1) {
        node.data = node.data.split(MARKER).join(value);
      }
      return;
    }
    if (node.nodeType !== 1 && node.nodeType !== 9 && node.nodeType !== 11) { return; }

    var attrs = node.attributes;
    if (attrs) {
      for (var i = 0; i < attrs.length; i++) {
        var a = attrs[i];
        if (a.value && a.value.indexOf(MARKER) !== -1) {
          a.value = a.value.split(MARKER).join(value);
        }
      }
    }

    var kids = node.childNodes;
    if (!kids) { return; }
    for (var j = 0; j < kids.length; j++) { fill(kids[j], value); }
  }

  function run() { fill(document, host()); }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', run);
  } else {
    run();
  }
})();
