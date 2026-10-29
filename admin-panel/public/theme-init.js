// Оформление панели до отрисовки (без вспышки): тема и палитра из «Внешний вид → Оформление
// панели» (src/theme/theme.ts), иначе — системная тема и «Лайм-тек».
// Отдельный файл, а не встроенный скрипт: CSP панели — script-src 'self' (deploy/Caddyfile).
try {
  var theme = localStorage.getItem("didi-panel-theme");
  if (theme === "light" || theme === "dark") {
    document.documentElement.setAttribute("data-theme", theme);
  }
  var palette = localStorage.getItem("didi-panel-palette");
  if (palette && /^(mint|sun|steel|olive)$/.test(palette)) {
    document.documentElement.setAttribute("data-palette", palette);
  }
} catch (e) {}
