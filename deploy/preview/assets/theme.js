/* Превью на GitHub Pages: тема из cookie до отрисовки (на сайте это делает сервер).
   Страницы собраны без темы, поэтому здесь же выставляется theme-color: иначе статус-бар
   телефона остаётся цвета системной темы (светлая полоса над тёмной страницей). */
(function () {
  var match = document.cookie.match(/(?:^|; )theme=(light|dark)(?:;|$)/);
  if (!match) return;
  var theme = match[1];
  var root = document.documentElement;
  root.setAttribute("data-theme", theme);
  var scheme = document.querySelector('meta[name="color-scheme"]');
  if (scheme) scheme.content = theme;
  var color = theme === "dark" ? "#070E0A" : "#EBF1E2";
  document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
    meta.content = color;
    meta.removeAttribute("media");
  });
})();
