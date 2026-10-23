// Тема панели до отрисовки (без вспышки): выбор из меню (src/theme/theme.ts), иначе — системная.
// Отдельный файл, а не встроенный скрипт: CSP панели — script-src 'self' (deploy/Caddyfile).
try {
  var theme = localStorage.getItem("didi-panel-theme");
  if (theme === "light" || theme === "dark") {
    document.documentElement.setAttribute("data-theme", theme);
  }
} catch (e) {}
