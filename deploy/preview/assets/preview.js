/* Превью на GitHub Pages: страницы — статичные снимки настоящих шаблонов, здесь — имитация того,
   что на сайте делает сервер: корзина (в localStorage), «В корзину», оформление, вход.
   Подключается только сборкой deploy/preview/build.py; на боевом сайте этого файла нет. */
(function () {
  "use strict";

  var root = document.documentElement;
  var BASE = root.getAttribute("data-preview-base") || "";
  var TREE = root.getAttribute("data-preview-tree") === "me" ? "me" : "guest";
  var ROOM = root.getAttribute("data-preview-room") || "";
  var ME = BASE + "/me";
  var PREFIX = TREE === "me" ? ME : BASE;
  var KEY = "didi-preview-cart";
  var NBSP = " ";

  var dataReady = fetch(BASE + "/static/preview/data.json").then(function (r) { return r.json(); });

  // --- Утилиты ---

  function rub(kopecks) {
    var rubles = Math.floor(kopecks / 100);
    var rest = kopecks % 100;
    var whole = String(rubles).replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
    return rest ? whole + "," + String(rest).padStart(2, "0") : whole;
  }
  function money(kopecks) { return rub(kopecks) + NBSP + "₽"; }

  function localPath(pathname) {
    if (pathname.indexOf(ME + "/") === 0) return pathname.slice(ME.length);
    if (pathname.indexOf(BASE + "/") === 0) return pathname.slice(BASE.length);
    return pathname;
  }
  var HERE = localPath(location.pathname);

  function go(url) { location.href = url; }

  var toastEl = null;
  var toastTimer = null;
  function toast(text) {
    if (!toastEl) {
      toastEl = document.createElement("div");
      toastEl.className = "pv-toast";
      toastEl.setAttribute("role", "status");
      document.body.appendChild(toastEl);
    }
    toastEl.textContent = text;
    void toastEl.offsetWidth;
    toastEl.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { toastEl.classList.remove("is-on"); }, 2600);
  }

  function fetchDoc(url) {
    return fetch(url).then(function (r) { return r.text(); }).then(function (html) {
      return new DOMParser().parseFromString(html, "text/html");
    });
  }

  // --- Корзина: [[variant_id, quantity], …] в браузере ---

  function readCart() {
    try {
      var lines = JSON.parse(localStorage.getItem(KEY) || "[]");
      return Array.isArray(lines) ? lines : [];
    } catch (e) { return []; }
  }
  function writeCart(lines) {
    try { localStorage.setItem(KEY, JSON.stringify(lines)); } catch (e) { /* приватный режим */ }
    setBadges(lines);
  }
  function units(lines) { return lines.reduce(function (n, line) { return n + line[1]; }, 0); }

  function setBadges(lines) {
    var count = units(lines);
    ["cart-badge-top", "cart-badge-tab"].forEach(function (id) {
      var badge = document.getElementById(id);
      if (!badge) return;
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.hidden = !count;
    });
  }

  function lineIndex(lines, id) {
    for (var i = 0; i < lines.length; i++) if (String(lines[i][0]) === String(id)) return i;
    return -1;
  }

  // --- «В корзину» на странице товара ---

  function addToCart(form) {
    var input = form.querySelector('input[name="variant"]:checked') ||
      form.querySelector('input[type="hidden"][name="variant"]');
    var result = form.querySelector("#buy-result");
    if (!input || !result) return;
    var id = input.value;
    dataReady.then(function (data) {
      var variant = data.variants[id];
      if (!variant) { result.innerHTML = '<p class="note note--danger">Товара нет в наличии.</p>'; return; }
      var lines = readCart();
      var index = lineIndex(lines, id);
      var quantity = (index >= 0 ? lines[index][1] : 0) + 1;
      if (quantity > variant.max) {
        result.innerHTML = '<p class="note note--danger">Больше добавить нельзя: доступно ' + variant.max + " шт.</p>";
        return;
      }
      if (index >= 0) lines[index][1] = quantity; else lines.push([Number(id), 1]);
      writeCart(lines);
      return fetchDoc(BASE + "/_sim/added-" + TREE + ".html").then(function (doc) {
        var added = doc.querySelector("[data-added]");
        result.innerHTML = added ? added.outerHTML : "";
        var cta = form.querySelector("[data-cta]");
        if (cta) {
          cta.classList.add("is-done");
          var label = cta.querySelector(".cta__label");
          if (label) label.textContent = "Добавлено в корзину";
        }
      });
    });
  }

  // --- Страница корзины: строки из настоящего шаблона, количество и суммы — здесь ---

  var emptyCart = null;

  function renderCart() {
    var current = document.getElementById("cart");
    if (!current) return;
    if (!emptyCart) emptyCart = current.cloneNode(true);
    var lines = readCart();
    if (!lines.length) { current.replaceWith(emptyCart.cloneNode(true)); return; }
    Promise.all([dataReady, fetchDoc(BASE + "/_sim/cart-" + TREE + "/")]).then(function (res) {
      var data = res[0];
      var template = res[1].getElementById("cart");
      var cart = document.importNode(template, true);
      var list = cart.querySelector(".lines");
      var byId = {};
      Array.prototype.forEach.call(list.children, function (li) {
        var form = li.querySelector("form[action*='/cart/line/']");
        var match = form && form.getAttribute("action").match(/\/cart\/line\/(\d+)\//);
        if (match) byId[match[1]] = li;
      });
      list.innerHTML = "";
      var total = 0;
      var kept = [];
      lines.forEach(function (line) {
        var variant = data.variants[line[0]];
        var li = byId[line[0]];
        if (!variant || !li) return; // товара больше нет в каталоге превью
        kept.push(line);
        var sum = variant.price * line[1];
        total += sum;
        li.querySelector(".stepper__value").textContent = line[1];
        li.querySelector(".line__price").textContent = money(sum);
        var forms = li.querySelectorAll("form");
        forms[0].setAttribute("data-op", "dec");
        forms[0].querySelector("button").disabled = line[1] <= 1;
        forms[1].setAttribute("data-op", "inc");
        forms[1].querySelector("button").disabled = line[1] >= variant.max;
        forms[2].setAttribute("data-op", "del");
        list.appendChild(li);
      });
      if (!kept.length) { writeCart([]); current.replaceWith(emptyCart.cloneNode(true)); return; }
      if (kept.length !== lines.length) writeCart(kept);
      var first = cart.querySelector(".summary__row");
      first.children[0].textContent = "Товары, " + units(kept) + " шт.";
      first.children[1].textContent = money(total);
      cart.querySelector(".summary__total").children[1].textContent = money(total);
      var price = cart.querySelector(".cta__price");
      if (price) price.textContent = money(total);
      document.getElementById("cart").replaceWith(cart);
    });
  }

  function changeLine(form, id) {
    var op = form.getAttribute("data-op");
    if (!op) { toast("В превью это действие не выполняется"); return; }
    dataReady.then(function (data) {
      var lines = readCart();
      var index = lineIndex(lines, id);
      if (index < 0) return;
      var max = data.variants[id] ? data.variants[id].max : 1;
      if (op === "del") lines.splice(index, 1);
      else lines[index][1] = Math.max(1, Math.min(max, lines[index][1] + (op === "inc" ? 1 : -1)));
      writeCart(lines);
      renderCart();
    });
  }

  // --- Оформление: состав и суммы из имитированной корзины ---

  function setupCheckout(form) {
    var lines = readCart();
    if (!lines.length) { location.replace(PREFIX + "/cart/"); return; }
    dataReady.then(function (data) {
      var items = 0;
      var mini = form.querySelector(".mini");
      mini.innerHTML = "";
      lines.forEach(function (line) {
        var variant = data.variants[line[0]];
        if (!variant) return;
        var sum = variant.price * line[1];
        items += sum;
        var li = document.createElement("li");
        var name = document.createElement("span");
        name.textContent = variant.name + (variant.size ? ", " + variant.size : "") + " × " + line[1];
        var price = document.createElement("span");
        price.textContent = money(sum);
        li.appendChild(name);
        li.appendChild(price);
        mini.appendChild(li);
      });
      var courier = items >= data.freeFrom ? 0 : data.courier;
      var radio = form.querySelector('input[name="delivery_method"][value="courier"]');
      if (radio) {
        radio.setAttribute("data-cost", courier);
        var choice = radio.closest(".choice");
        choice.querySelector(".choice__price").textContent = money(courier);
        choice.querySelector(".choice__hint").textContent = (courier ? "Бесплатно от " : "Бесплатно — заказ от ") + money(data.freeFrom);
      }
      var rows = form.querySelectorAll(".summary__row");
      rows[0].children[1].textContent = money(items);
      var totalEl = form.querySelector("[data-total]");
      var costEl = form.querySelector("[data-delivery-cost]");
      var update = function () {
        var picked = form.querySelector('input[name="delivery_method"]:checked');
        var cost = picked ? parseInt(picked.getAttribute("data-cost"), 10) || 0 : 0;
        costEl.textContent = money(cost);
        totalEl.textContent = money(items + cost);
      };
      totalEl.setAttribute("data-items", items);
      form.addEventListener("change", function (event) {
        if (event.target.name === "delivery_method") update();
      });
      update();
    });
  }

  function placeOrder(form) {
    var online = form.querySelector('input[name="payment_method"]:checked');
    writeCart([]);
    go(ME + (online && online.value === "online" ? "/orders/placed-online/" : "/orders/placed/"));
  }

  // --- Отправка форм: на сайте — сервер, здесь — имитация или подсказка ---

  document.addEventListener("submit", function (event) {
    if (event.defaultPrevented) return; // тема, баннер, отменённое подтверждение — уже обработано
    var form = event.target;
    event.preventDefault();
    var action = localPath(new URL(form.getAttribute("action") || location.href, location.href).pathname);
    var line = action.match(/^\/cart\/line\/(\d+)\/$/);

    if (form.hasAttribute("data-buy")) return addToCart(form);
    if (line) return changeLine(form, line[1]);
    if (form.hasAttribute("data-checkout") && !ROOM) return placeOrder(form);
    if ((form.method || "get").toLowerCase() === "get") {
      if (action === "/search/") return go(PREFIX + "/search/");
      return toast("Фильтры и сортировка в превью не применяются");
    }
    if (action === "/login/" || action === "/register/") {
      // Как на сайте: после входа — туда, откуда пришли (например, к оформлению).
      var next = form.querySelector('input[name="next"]');
      var back = next && next.value ? localPath(new URL(next.value, location.href).pathname) : "";
      return go(ME + (back && back !== "/login/" ? back : "/profile/"));
    }
    if (action === "/password-reset/") return go(BASE + "/password-reset/confirm/");
    if (action === "/password-reset/confirm/") return go(ME + "/profile/");
    if (action === "/logout/") return go(BASE + "/");
    toast("В превью это действие не выполняется");
  });

  // --- Панель «Превью»: гость / покупатель, все комнаты, очистка корзины ---

  function counterpart(pages, tree) {
    var target = (tree === "me" ? ME : BASE) + (ROOM ? "/" : HERE);
    if (pages.indexOf(target) >= 0) return target;
    return (tree === "me" ? ME : BASE) + "/profile/";
  }

  function buildPanel() {
    var box = document.createElement("div");
    box.className = "pv";
    box.innerHTML =
      '<button class="pv__tab" type="button" aria-expanded="false" aria-controls="pv-panel">Превью</button>' +
      '<div class="pv__panel" id="pv-panel" hidden>' +
      '<p class="pv__title">Превью оформления</p>' +
      '<p class="pv__text">Это снимок сайта: покупки, вход и оформление только имитируются.</p>' +
      '<div class="pv__seg" role="group" aria-label="Кто смотрит">' +
      '<a class="pv__opt' + (TREE === "guest" ? " is-on" : "") + '" data-tree="guest" href="' + BASE + '/">Гость</a>' +
      '<a class="pv__opt' + (TREE === "me" ? " is-on" : "") + '" data-tree="me" href="' + ME + '/">Покупатель</a>' +
      "</div>" +
      '<a class="pv__link" href="' + BASE + '/rooms/">Все комнаты</a>' +
      '<button class="pv__link" type="button" data-pv-reset>Очистить корзину</button>' +
      "</div>";
    document.body.appendChild(box);
    var tab = box.querySelector(".pv__tab");
    var panel = box.querySelector(".pv__panel");
    tab.addEventListener("click", function () {
      panel.hidden = !panel.hidden;
      tab.setAttribute("aria-expanded", String(!panel.hidden));
    });
    document.addEventListener("click", function (event) {
      if (!panel.hidden && !box.contains(event.target)) {
        panel.hidden = true;
        tab.setAttribute("aria-expanded", "false");
      }
    });
    box.querySelector("[data-pv-reset]").addEventListener("click", function () {
      writeCart([]);
      if (HERE === "/cart/" && !ROOM) renderCart();
      toast("Корзина очищена");
    });
    dataReady.then(function (data) {
      box.querySelectorAll("[data-tree]").forEach(function (link) {
        link.href = counterpart(data.pages, link.getAttribute("data-tree"));
      });
    });
  }

  // --- Старт ---

  if (ROOM !== "sim") {
    buildPanel();
    if (ROOM !== "cart-problems") setBadges(readCart());
    if (!ROOM && HERE === "/cart/") renderCart();
    var checkout = document.querySelector("[data-checkout]");
    if (checkout && !ROOM && TREE === "me") setupCheckout(checkout);
  }
})();
