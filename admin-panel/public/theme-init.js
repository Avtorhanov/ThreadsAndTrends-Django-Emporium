// Оформление панели до отрисовки (без вспышки): тема, палитра, акцент «Своей», углы и размер
// текста из «Внешний вид → Панель» (src/theme/theme.ts), иначе — системная тема и «Лайм-тек».
// Отдельный файл, а не встроенный скрипт: CSP панели — script-src 'self' (deploy/Caddyfile).
// Белые списки — как в src/theme/palettes.ts (генерирует scripts/gen_tokens.py).
try {
  var root = document.documentElement;
  var get = function (key, pattern) {
    var value = localStorage.getItem(key);
    return value && pattern.test(value) ? value : null;
  };
  var theme = get("didi-panel-theme", /^(light|dark)$/);
  if (theme) root.setAttribute("data-theme", theme);
  var palette = get("didi-panel-palette", /^(mint|sun|steel|olive|custom)$/);
  if (palette) root.setAttribute("data-palette", palette);
  if (palette === "custom") {
    root.setAttribute(
      "data-accent",
      get("didi-panel-accent", /^(mint|sun|sky|pink|lilac|steel|orange|olive|sand|navy|wine|graphite|forest)$/) || "lime",
    );
  }
  var radius = get("didi-panel-radius", /^(sharp|soft)$/);
  if (radius) root.setAttribute("data-radius", radius);
  var text = get("didi-panel-text", /^(m|l)$/);
  if (text) root.setAttribute("data-text", text);
} catch (e) {}
