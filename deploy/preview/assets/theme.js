/* Превью на GitHub Pages: тема из cookie до отрисовки (на сайте это делает сервер). */
(function () {
  var match = document.cookie.match(/(?:^|; )theme=(light|dark)(?:;|$)/);
  if (!match) return;
  var root = document.documentElement;
  root.setAttribute("data-theme", match[1]);
  var scheme = document.querySelector('meta[name="color-scheme"]');
  if (scheme) scheme.content = match[1];
})();
