/* Превью на GitHub Pages: тема и оформление из cookie до отрисовки (на сайте это делает
   сервер). Страницы собраны без них, поэтому здесь же выставляется theme-color: иначе
   статус-бар телефона остаётся цвета системной темы (светлая полоса над тёмной страницей). */
(function () {
  var root = document.documentElement;

  function cookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([a-z0-9_-]+)(?:;|$)"));
    return match ? match[1] : "";
  }

  var theme = cookie("theme");
  if (theme === "light" || theme === "dark") {
    root.setAttribute("data-theme", theme);
    var scheme = document.querySelector('meta[name="color-scheme"]');
    if (scheme) scheme.content = theme;
  }
  // Палитра, акцент, углы, текст: значения по умолчанию — без атрибута (как на сервере).
  var palette = cookie("palette");
  if (palette && palette !== "lime") root.setAttribute("data-palette", palette);
  if (palette === "custom") root.setAttribute("data-accent", cookie("accent") || "lime");
  var radius = cookie("radius");
  if (radius === "sharp" || radius === "soft") root.setAttribute("data-radius", radius);
  var text = cookie("text_size");
  if (text === "m" || text === "l") root.setAttribute("data-text", text);

  if (!theme && !palette) return;
  // Скрипт стоит после стилей в <head> — переменные палитры уже доступны.
  var color = getComputedStyle(root).getPropertyValue("--bg").trim();
  if (!color) return;
  document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
    meta.content = color;
    meta.removeAttribute("media");
  });
})();
