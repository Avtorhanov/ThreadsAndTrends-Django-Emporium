/* Превью на GitHub Pages: до отрисовки — то, что на сайте делает сервер.
   1) Дерево страниц: вошедший покупатель видит страницы /me/…, гость — обычные (вход и выход
      имитирует preview.js, состояние — в localStorage, его пишет sim.js).
   2) Тема и оформление: выбор покупателя из cookie, иначе — что задал администратор в панели
      (палитра, тема, углы для нового посетителя, вид нижнего меню).
   3) theme-color: иначе статус-бар телефона остаётся цвета системной темы. */
(function () {
  var root = document.documentElement;
  var BASE = root.getAttribute("data-preview-base") || "";
  var TREE = root.getAttribute("data-preview-tree");
  var ROOM = root.getAttribute("data-preview-room") || "";
  var ME = BASE + "/me";

  function cookie(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([a-z0-9_-]+)(?:;|$)"));
    return match ? match[1] : "";
  }

  var shop = {};
  try { shop = JSON.parse(localStorage.getItem("didi-sim-look") || "{}") || {}; } catch (e) { shop = {}; }

  if (!ROOM) {
    var path = location.pathname;
    if (TREE === "guest" && shop.user && path.indexOf(ME + "/") !== 0) {
      var local = path.indexOf(BASE + "/") === 0 ? path.slice(BASE.length) : path;
      // Вход, регистрация и сброс пароля есть только у гостя.
      if (!/^\/(login|register|password-reset)\//.test(local)) {
        location.replace(ME + local + location.search + location.hash);
        return;
      }
    } else if (TREE === "me" && !shop.user && shop.out) {
      var mine = path.slice(ME.length) || "/";
      var closed = /^\/(profile|orders|checkout)\//.test(mine);
      location.replace(BASE + (closed ? "/login/?next=" + encodeURIComponent(mine) : mine + location.search));
      return;
    }
  }

  var theme = cookie("theme") || shop.mode || "";
  var scheme = document.querySelector('meta[name="color-scheme"]');
  if (theme === "light" || theme === "dark") {
    root.setAttribute("data-theme", theme);
    if (scheme) scheme.content = theme;
  } else if (theme === "system") {
    root.removeAttribute("data-theme");
    if (scheme) scheme.content = "light dark";
  }

  // Палитра, акцент, углы, текст: значения по умолчанию — без атрибута (как на сервере).
  var palette = cookie("palette");
  if (shop.palettes && palette && shop.palettes.indexOf(palette) < 0) palette = "";
  palette = palette || shop.palette || "lime";
  if (palette !== "lime") root.setAttribute("data-palette", palette);
  else root.removeAttribute("data-palette");
  if (palette === "custom") root.setAttribute("data-accent", cookie("accent") || "lime");
  else root.removeAttribute("data-accent");
  var radius = cookie("radius") || shop.radius || "";
  if (radius === "sharp" || radius === "soft") root.setAttribute("data-radius", radius);
  else if (radius === "normal") root.removeAttribute("data-radius");
  var text = cookie("text_size");
  if (text === "m" || text === "l") root.setAttribute("data-text", text);
  // Нижнее меню: «Сплошное» (по умолчанию) — без атрибута.
  if (shop.nav && shop.nav !== "solid") root.setAttribute("data-nav", shop.nav);
  else if (shop.nav) root.removeAttribute("data-nav");

  if (!theme && palette === "lime") return;
  // Скрипт стоит после стилей в <head> — переменные палитры уже доступны.
  var color = getComputedStyle(root).getPropertyValue("--bg").trim();
  if (!color) return;
  document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
    meta.content = color;
    meta.removeAttribute("media");
  });
})();
