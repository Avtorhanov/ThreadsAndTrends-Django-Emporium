/* Магазин на GitHub Pages: страницы — снимки настоящих шаблонов, а всё, что на сайте делает
   сервер, здесь делает имитация (sim.js, общая с панелью администратора): каталог, поиск и
   фильтры, корзина, «Купить сейчас», оформление и оплата, заказы и их отмена, вход,
   регистрация, профиль. Разметка повторяет шаблоны web/templates/web/*. Изменения из панели
   (товары, цены, остатки, категории, статьи, главная, тема, настройки) видны сразу.
   Подключается только сборкой deploy/preview/build.py; на боевом сайте этого файла нет. */
(function () {
  "use strict";

  var sim = window.DidiSim;
  if (!sim) return;

  var root = document.documentElement;
  var BASE = root.getAttribute("data-preview-base") || "";
  var ROOM = root.getAttribute("data-preview-room") || "";
  var ME = BASE + "/me";
  var path = location.pathname;
  var TREE = path.indexOf(ME + "/") === 0 ? "me" : root.getAttribute("data-preview-tree") === "me" ? "me" : "guest";
  var PREFIX = TREE === "me" ? ME : BASE;
  var NBSP = " ";
  var PAGE_SIZE = 24;
  var dataReady = fetch(BASE + "/static/preview/data.json").then(function (r) { return r.json(); });

  function localPath(pathname) {
    if (pathname.indexOf(ME + "/") === 0) return pathname.slice(ME.length);
    if (pathname.indexOf(BASE + "/") === 0) return pathname.slice(BASE.length);
    return pathname;
  }
  var HERE = localPath(path);
  var query = new URLSearchParams(location.search);

  // --- Утилиты ---

  function esc(value) {
    return String(value === null || value === undefined ? "" : value)
      .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;").replace(/"/g, "&quot;");
  }
  function rub(kopecks) {
    var whole = String(Math.floor(kopecks / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, NBSP);
    var rest = kopecks % 100;
    return rest ? whole + "," + String(rest).padStart(2, "0") : whole;
  }
  function money(kopecks) { return rub(kopecks) + NBSP + "₽"; }
  function plural(n, forms) {
    var f = forms.split(",");
    var a = Math.abs(n);
    var word = a % 10 === 1 && a % 100 !== 11 ? f[0] : a % 10 >= 2 && a % 10 <= 4 && (a % 100 < 12 || a % 100 > 14) ? f[1] : f[2];
    return n + " " + word;
  }
  var MONTHS = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября", "октября", "ноября", "декабря"];
  function pad(n) { return (n < 10 ? "0" : "") + n; }
  function date(iso, withYear, withTime) {
    var d = new Date(iso);
    var out = d.getDate() + " " + MONTHS[d.getMonth()] + (withYear ? " " + d.getFullYear() : "");
    return withTime ? out + ", " + pad(d.getHours()) + ":" + pad(d.getMinutes()) : out;
  }
  function time(iso) { var d = new Date(iso); return pad(d.getHours()) + ":" + pad(d.getMinutes()); }
  var TONES = ["lime", "sun", "mint", "apricot", "sage", "aqua"];
  // Тон плашки фото по slug: FNV-1a, как web.templatetags.storefront.tone.
  function tone(slug) {
    var value = 0x811c9dc5;
    for (var i = 0; i < slug.length; i++) {
      value ^= slug.charCodeAt(i);
      value = Math.imul(value, 0x01000193) >>> 0;
    }
    return TONES[value % TONES.length];
  }
  function discount(p) {
    var old = p.compare_at_kopecks;
    var price = p.price_kopecks;
    if (!old || price === null || old <= price) return 0;
    return Math.floor(((old - price) * 100 + Math.floor(old / 2)) / old);
  }
  var STATUS_TONES = {
    awaiting_payment: "warning", confirmed: "tag", paid: "tag", assembled: "tag",
    shipped: "info", ready_for_pickup: "info", delivered: "success", cancelled: "neutral"
  };
  function icon(name, size, css) {
    return '<svg class="ic' + (css ? " " + css : "") + '" width="' + size + '" height="' + size + '"><use href="#i-' + name + '"/></svg>';
  }
  function link(p) { return PREFIX + p; }
  function go(url) { location.href = url; }
  function img(url, sizes, css, eager, alt) {
    if (!url) return "";
    var src = sim.imageSources(url);
    var attrs = 'src="' + esc(url) + '"';
    if (src && src.srcset) attrs += ' srcset="' + esc(src.srcset) + '" sizes="' + esc(sizes) + '"';
    if (src && src.w && src.h) attrs += ' width="' + src.w + '" height="' + src.h + '"';
    return "<img " + attrs + ' alt="' + esc(alt || "") + '" loading="' + (eager ? "eager" : "lazy") + '" fetchpriority="' +
      (eager ? "high" : "auto") + '" decoding="async" class="' + css + '">';
  }
  function paragraphs(text) {
    return String(text || "").split(/\n\s*\n/).map(function (p) { return p.trim(); }).filter(Boolean);
  }

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

  // Сообщение на следующей странице (как django.contrib.messages).
  var FLASH = "didi-sim-flash";
  function flash(text, level) {
    try { sessionStorage.setItem(FLASH, JSON.stringify({ text: text, level: level || "success" })); } catch (e) { /* без хранилища */ }
  }
  function showFlash() {
    var raw = null;
    try { raw = sessionStorage.getItem(FLASH); sessionStorage.removeItem(FLASH); } catch (e) { raw = null; }
    if (!raw) return;
    var message = JSON.parse(raw);
    var main = document.getElementById("main");
    if (!main) return;
    var box = main.querySelector(".flash");
    if (!box) {
      box = document.createElement("div");
      box.className = "flash";
      box.setAttribute("role", "status");
      main.insertBefore(box, main.firstChild);
    }
    box.innerHTML = '<p class="note note--' + esc(message.level) + '">' + esc(message.text) + "</p>";
  }

  // --- Общее для всех страниц ---

  function cartSlugs() {
    var map = {};
    sim.cart().lines.forEach(function (line) { if (line.product) map[line.product.slug] = (map[line.product.slug] || 0) + line.quantity; });
    return map;
  }

  function setBadges() {
    var count = sim.cartCount();
    ["cart-badge-top", "cart-badge-tab"].forEach(function (id) {
      var badge = document.getElementById(id);
      if (!badge) return;
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.hidden = !count;
    });
  }

  function renderCats(activeSlug) {
    var strip = document.querySelector(".cats");
    if (!strip) return;
    var roots = sim.categories().filter(function (c) { return !c.parent; });
    var html = '<a class="seg' + (activeSlug ? "" : " is-on") + '" href="' + link("/") + '"' + (activeSlug ? "" : ' aria-current="page"') + ">Все</a>";
    roots.forEach(function (c) {
      var on = c.slug === activeSlug;
      html += '<a class="seg' + (on ? " is-on" : "") + '" href="' + link("/category/" + c.slug + "/") + '"' + (on ? ' aria-current="page"' : "") + ">" + esc(c.name) + "</a>";
    });
    if (strip.innerHTML.replace(/\s+/g, " ") !== html) {
      var x = strip.scrollLeft;
      strip.innerHTML = html;
      strip.scrollLeft = x;
    }
    // Выбранная категория (в том числе новая из панели) — целиком в поле зрения.
    var on = strip.querySelector(".seg.is-on");
    if (on) {
      var pad = 16;
      if (on.offsetLeft - pad < strip.scrollLeft) strip.scrollLeft = on.offsetLeft - pad;
      else if (on.offsetLeft + on.offsetWidth + pad > strip.scrollLeft + strip.clientWidth) {
        strip.scrollLeft = on.offsetLeft + on.offsetWidth + pad - strip.clientWidth;
      }
    }
  }

  function renderFooter() {
    var foot = document.querySelector(".foot__inner");
    if (!foot) return;
    var s = sim.settings().seller;
    var parts = [];
    var clean = function (v) { return String(v || "").split(/\s+/).filter(Boolean).join(" ").replace(/[\s,;:·]+$/, ""); };
    var inn = String(s.inn || "").replace(/\D/g, "");
    var ogrn = String(s.ogrn || "").replace(/\D/g, "");
    if (clean(s.name)) parts.push(esc(clean(s.name)));
    if (inn) parts.push("ИНН " + inn);
    if (ogrn) parts.push((ogrn.length === 13 ? "ОГРН " : "ОГРНИП ") + ogrn);
    if (clean(s.address)) parts.push(esc(clean(s.address)));
    if (clean(s.phone)) parts.push('<a href="tel:' + esc(clean(s.phone).replace(/[^\d+]/g, "")) + '">' + esc(clean(s.phone)) + "</a>");
    if (s.email) parts.push('<a href="mailto:' + esc(lowerTrim(s.email)) + '">' + esc(lowerTrim(s.email)) + "</a>");
    var line = foot.querySelector(".foot__seller");
    if (!parts.length) { if (line) line.remove(); return; }
    var html = parts.map(function (p) { return '<span class="foot__part">' + p + "</span>"; }).join("&nbsp;· ");
    if (!line) {
      line = document.createElement("p");
      line.className = "foot__seller";
      foot.insertBefore(line, foot.querySelector(".foot__copy"));
    }
    line.innerHTML = html;
  }
  function lowerTrim(v) { return String(v || "").trim().toLowerCase(); }

  // Палитры, которые администратор выключил, из профиля пропадают.
  function filterPalettes() {
    var form = document.querySelector("[data-theme-select]");
    if (!form) return;
    var t = sim.db().theme;
    form.querySelectorAll('input[name="palette"]').forEach(function (input) {
      var label = input.closest(".swatch");
      if (label) label.hidden = t.enabled.indexOf(input.value) < 0;
    });
    form.querySelectorAll(".swatches").forEach(function (group) {
      var visible = group.querySelectorAll(".swatch:not([hidden])").length;
      group.hidden = !visible;
      var title = group.previousElementSibling;
      if (title && title.classList.contains("look__sub")) title.hidden = !visible;
    });
    var accents = form.querySelector("[data-accents]");
    if (accents && t.enabled.indexOf("custom") < 0) accents.hidden = true;
    // Отмечено то, что действует сейчас: личный выбор (cookie) или настройки магазина.
    var palette = cookieValue("palette");
    if (t.enabled.indexOf(palette) < 0) palette = t.default_palette;
    var current = {
      theme: cookieValue("theme") || t.default_mode,
      palette: palette,
      accent: cookieValue("accent"),
      radius: cookieValue("radius") || t.default_radius,
      text: cookieValue("text_size") || t.default_text || "s"
    };
    Object.keys(current).forEach(function (name) {
      if (!current[name]) return;
      var input = form.querySelector('input[name="' + name + '"][value="' + current[name] + '"]');
      if (input) input.checked = true;
    });
  }
  function cookieValue(name) {
    var match = document.cookie.match(new RegExp("(?:^|; )" + name + "=([a-z0-9_-]+)(?:;|$)"));
    return match ? match[1] : "";
  }

  // --- Карточки и сетки (web/catalog/_card.html, _grid.html) ---

  function cardHTML(p, eager, inCart) {
    var off = discount(p);
    var html = '<a class="card" href="' + link("/product/" + p.slug + "/") + '">';
    html += '<span class="card__img tone-' + tone(p.slug) + '">';
    html += img(p.cover_url, "(min-width: 1200px) 280px, (min-width: 900px) 25vw, (min-width: 600px) 33vw, 50vw", "card__photo", eager, "");
    if (off) html += '<span class="sale">−' + off + "%</span>";
    if (!p.in_stock) html += '<span class="soldout">Нет в наличии</span>';
    if (inCart && inCart[p.slug]) html += '<span class="incart">' + icon("bag", 14) + "В корзине</span>";
    html += '</span><span class="card__body"><span class="card__title">' + esc(p.name) + "</span>";
    if (p.status) html += '<span class="mark mark--' + esc(p.status.tone) + '">' + esc(p.status.name) + "</span>";
    html += '<span class="price">';
    html += p.price_on_request ? '<span class="price__now price__now--ask">По запросу</span>' : '<span class="price__now">' + rub(p.price_kopecks) + "&nbsp;₽</span>";
    if (p.compare_at_kopecks && !p.price_on_request) html += '<s class="price__old"><span class="sr">Старая цена </span>' + rub(p.compare_at_kopecks) + "&nbsp;₽</s>";
    html += "</span></span></a>";
    return html;
  }

  function emptyHTML(title, text, iconName, action) {
    return '<div class="empty">' + icon(iconName || "box", 40, "empty__ic") + '<p class="empty__title">' + esc(title) + "</p>" +
      (text ? '<p class="empty__text">' + esc(text) + "</p>" : "") + (action || "") + "</div>";
  }

  function gridHTML(list, eagerCount) {
    if (!list.length) return emptyHTML("Ничего не нашлось", "Попробуйте изменить запрос или фильтры.");
    var inCart = cartSlugs();
    return '<div class="grid">' + list.map(function (p, i) { return cardHTML(p, i < eagerCount, inCart); }).join("") + "</div>";
  }

  // --- Главная из блоков (web/catalog/_home_blocks.html) ---

  // Баннер (web/catalog/_home_banner.html): с картинками или товаром — фото в рамке карточки,
  // заголовок поверх; иначе — цветная плашка.
  function bannerHTML(b, eager) {
    var product = b.preview_product;
    var heading = b.title || (product ? product.name : "");
    var images = b.preview_images || [];
    var cat = b.category ? sim.category(b.category) : null;
    if (cat && !cat.is_active) cat = null;
    var url = product ? link("/product/" + product.slug + "/") : cat ? link("/category/" + cat.slug + "/") : "";
    if (images.length) {
      var slides = images.map(function (src, i) {
        return '<span class="hblock-photo__slide' + (i === 0 ? " is-on" : "") + '">' + img(src, "(min-width: 1200px) 1100px, 100vw", "hblock-photo__img", eager && i === 0, "") + "</span>";
      }).join("");
      var text = b.text || (product && !product.price_on_request ? rub(product.price_kopecks) + "&nbsp;₽" : "");
      var shade = heading || text ? '<span class="hblock-photo__shade">' + (heading ? '<span class="hblock-photo__title">' + esc(heading) + "</span>" : "") +
        (text ? '<span class="hblock-photo__text">' + (b.text ? esc(b.text) : text) + "</span>" : "") + "</span>" : "";
      var inner = '<span class="hblock-photo__slides"' + (images.length > 1 ? " data-slides" : "") + ">" + slides + "</span>" + shade;
      return '<section class="hblock hblock-banner hblock-photo">' + (url ? '<a class="hblock-photo__frame" href="' + url + '"' + (heading ? ' aria-label="' + esc(heading) + '"' : "") + ">" + inner + "</a>" :
        '<div class="hblock-photo__frame">' + inner + "</div>") + "</section>";
    }
    if (!b.title && !b.text) return "";
    var body = '<span class="hblock-banner__body">' + (b.title ? '<span class="hblock-banner__title">' + esc(b.title) + "</span>" : "") +
      (b.text ? '<span class="hblock-banner__text">' + esc(b.text) + "</span>" : "") + "</span>";
    return '<section class="hblock hblock-banner" style="--hb-bg:' + esc(b.color || "#DDF38A") + ";--hb-ink:" + esc(b.ink) + '">' +
      (url ? '<a class="hblock-banner__link" href="' + url + '" aria-label="' + esc((b.title ? b.title + " — " : "") + (cat ? cat.name : "")) + '">' + body + "</a>" : body) + "</section>";
  }

  function homeBlocksHTML(blocks) {
    var inCart = cartSlugs();
    var parts = blocks.map(function (b, index) {
      if (b.kind === "banner") return { banner: true, html: bannerHTML(b, index === 0) };
      return { banner: false, html: blockHTML(b, inCart) };
    }).filter(function (part) { return part.html; });
    // Баннеры подряд — карусель (content.home.with_carousels).
    var out = [];
    for (var i = 0; i < parts.length; i++) {
      if (!parts[i].banner) { out.push(parts[i].html); continue; }
      var group = [parts[i].html];
      while (i + 1 < parts.length && parts[i + 1].banner) group.push(parts[++i].html);
      if (group.length === 1) { out.push(group[0]); continue; }
      out.push('<section class="hblock hblock-carousel" data-carousel aria-roledescription="карусель" aria-label="Баннеры"><div class="hblock-carousel__track" data-carousel-track>' +
        group.map(function (html, n) { return '<div class="hblock-carousel__slide" aria-roledescription="слайд" aria-label="' + (n + 1) + " из " + group.length + '">' + html + "</div>"; }).join("") +
        '</div><div class="hblock-carousel__dots" role="group" aria-label="Выбор баннера">' +
        group.map(function (html, n) { return '<button class="hblock-carousel__dot' + (n === 0 ? " is-on" : "") + '" type="button" data-carousel-dot aria-label="Баннер ' + (n + 1) + '"' + (n === 0 ? ' aria-current="true"' : "") + "></button>"; }).join("") +
        "</div></section>");
    }
    return out.join("");
  }

  function blockHTML(b, inCart) {
      if (b.kind === "collection") {
        if (!b.preview_products.length) return "";
        var all = "";
        var bcat = b.source === "category" && b.category ? sim.category(b.category) : null;
        if (bcat) all = '<a class="hblock-head__all" href="' + link("/category/" + bcat.slug + "/") + '">Все' + icon("chevron", 16) + "</a>";
        else if (b.source === "new") all = '<a class="hblock-head__all" href="' + link("/products/") + '">Все' + icon("chevron", 16) + "</a>";
        return '<section class="hblock hblock-rail" aria-label="' + esc(b.title || "Подборка") + '"><div class="hblock-head">' +
          (b.title ? '<h2 class="hblock-head__title">' + esc(b.title) + "</h2>" : "") + all + '</div><div class="hblock-rail__track">' +
          b.preview_products.map(function (p) { return '<div class="hblock-rail__cell">' + cardHTML(p, false, inCart) + "</div>"; }).join("") +
          "</div></section>";
      }
      if (b.kind === "categories") {
        // Свои вкладки (категории, статьи, страницы, ссылки) или корневые категории.
        var items = (b.preview_links || []).map(function (l) {
          var external = /^https?:\/\//.test(l.url);
          return '<a class="hblock-cats__item" href="' + (external ? esc(l.url) : link(l.url)) + '"' + (external ? ' target="_blank" rel="noopener noreferrer"' : "") + ">" + esc(l.title) + "</a>";
        });
        if (!items.length) {
          items = sim.categories().filter(function (c) { return !c.parent; }).map(function (c) {
            return '<a class="hblock-cats__item" href="' + link("/category/" + c.slug + "/") + '">' + esc(c.name) + "</a>";
          });
        }
        if (!items.length) return "";
        return '<nav class="hblock hblock-cats" aria-label="' + esc(b.title || "Категории") + '">' +
          (b.title ? '<h2 class="hblock-head__title">' + esc(b.title) + "</h2>" : "") + '<div class="hblock-cats__list">' + items.join("") + "</div></nav>";
      }
      var pars = paragraphs(b.text);
      if (!b.title && !pars.length) return "";
      return '<section class="hblock hblock-text">' + (b.title ? '<h2 class="hblock-head__title">' + esc(b.title) + "</h2>" : "") +
        pars.map(function (p) { return "<p>" + esc(p).replace(/\n/g, "<br>") + "</p>"; }).join("") + "</section>";
  }

  function renderHome() {
    var feed = document.querySelector(".feed");
    if (!feed) return;
    var blocks = homeBlocksHTML(sim.publishedHome());
    var products = sim.liveProducts();
    var html = '<h1 class="visually-hidden">Свежее в каталоге</h1>';
    if (blocks) html += '<div class="home-blocks">' + blocks + '</div><h2 class="hblock-head__title hblock-head__title--feed">Все товары</h2>';
    html += gridHTML(products.slice(0, PAGE_SIZE), 4);
    if (products.length > PAGE_SIZE) {
      html += '<p class="more"><a class="btn btn--ghost" href="' + link("/products/") + '">Весь каталог' + icon("chevron", 18) + "</a></p>";
    }
    feed.innerHTML = html;
    if (window.didiHomeMotion) window.didiHomeMotion(feed);
  }

  // --- Каталог, категория, поиск (web/catalog/listing.html) ---

  function parseRubles(value) {
    var raw = String(value || "").replace(/[\s ]/g, "").replace(",", ".");
    var m = raw.match(/^(\d{1,9})(?:\.(\d{1,2}))?$/);
    if (!m) return null;
    return parseInt(m[1], 10) * 100 + parseInt((m[2] || "0").padEnd(2, "0"), 10);
  }

  function renderListing(kind) {
    var feed = document.querySelector(".feed");
    if (!feed) return;
    var q = (query.get("q") || "").trim();
    var sort = query.get("sort") || "";
    var priceMin = parseRubles(query.get("price_min"));
    var priceMax = parseRubles(query.get("price_max"));
    var inStock = query.get("in_stock") === "1";
    var list = sim.liveProducts();
    var cat = null;
    if (kind === "category") {
      var slug = HERE.split("/")[2];
      cat = sim.categoryBySlug(slug);
      var active = cat && sim.categories().some(function (c) { return c.id === cat.id; });
      renderCats(cat && active ? (cat.parent ? sim.category(cat.parent).slug : cat.slug) : "");
      if (!cat || !active) {
        feed.innerHTML = emptyHTML("Категория недоступна", "Её скрыли или удалили. Загляните в каталог.", "box",
          '<a class="btn btn--dark" href="' + link("/") + '">В каталог</a>');
        return;
      }
      document.title = cat.name + " — DiDi-shop";
      var ids = sim.descendants(cat.id);
      list = list.filter(function (p) { return p.category && ids.indexOf(p.category.id) >= 0; });
    } else if (kind === "products") {
      renderCats("");
    }
    if (priceMin !== null) list = list.filter(function (p) { return p.price_kopecks !== null && p.price_kopecks >= priceMin; });
    if (priceMax !== null) list = list.filter(function (p) { return p.price_kopecks !== null && p.price_kopecks <= priceMax; });
    var words = q.toLowerCase().split(/\s+/).filter(Boolean);
    if (inStock || words.length) list = list.filter(function (p) { return p.in_stock; });
    var score = {};
    if (words.length) {
      list = list.filter(function (p) {
        var full = sim.productById(p.id);
        var name = p.name.toLowerCase();
        var desc = String(full && full.description || "").toLowerCase();
        var s = 0;
        for (var i = 0; i < words.length; i++) {
          var inName = name.indexOf(words[i]) >= 0;
          var inDesc = desc.indexOf(words[i]) >= 0;
          if (!inName && !inDesc) return false;
          s += inName ? 2 : 1;
        }
        score[p.id] = s;
        return true;
      });
    }
    var byPrice = function (dir) {
      return function (a, b) {
        if (a.price_kopecks === null && b.price_kopecks === null) return 0;
        if (a.price_kopecks === null) return 1;
        if (b.price_kopecks === null) return -1;
        return dir * (a.price_kopecks - b.price_kopecks);
      };
    };
    if (sort === "price_asc") list.sort(byPrice(1));
    else if (sort === "price_desc") list.sort(byPrice(-1));
    else if (words.length && sort !== "new") list.sort(function (a, b) { return (score[b.id] || 0) - (score[a.id] || 0); });

    var pages = Math.max(1, Math.ceil(list.length / PAGE_SIZE));
    var page = Math.min(pages, Math.max(1, parseInt(query.get("page"), 10) || 1));
    var html = gridHTML(list.slice((page - 1) * PAGE_SIZE, page * PAGE_SIZE), page === 1 ? 4 : 0);
    if (pages > 1) {
      var pageUrl = function (n) {
        var params = new URLSearchParams(location.search);
        if (n > 1) params.set("page", n); else params.delete("page");
        var s = params.toString();
        return location.pathname + (s ? "?" + s : "");
      };
      html += '<nav class="pager" aria-label="Страницы">';
      if (page > 1) html += '<a class="pager__step" href="' + pageUrl(page - 1) + '" rel="prev" aria-label="Предыдущая страница">' + icon("chevron", 18, "flip") + "</a>";
      for (var n = 1; n <= pages; n++) {
        html += n === page ? '<span class="pager__num is-on" aria-current="page">' + n + "</span>" : '<a class="pager__num" href="' + pageUrl(n) + '">' + n + "</a>";
      }
      if (page < pages) html += '<a class="pager__step" href="' + pageUrl(page + 1) + '" rel="next" aria-label="Следующая страница">' + icon("chevron", 18) + "</a>";
      html += "</nav>";
    }
    var old = feed.querySelectorAll(".grid, .pager, .more, .empty");
    old.forEach(function (el) { el.remove(); });
    var holder = document.createElement("div");
    holder.innerHTML = html;
    while (holder.firstChild) feed.appendChild(holder.firstChild);

    // Форма фильтров — текущие значения из адреса.
    var form = feed.querySelector("[data-filters]");
    if (form) {
      var set = function (name, value) { var el = form.querySelector('[name="' + name + '"]'); if (el) el.value = value; };
      set("q", q);
      set("sort", sort);
      set("price_min", query.get("price_min") || "");
      set("price_max", query.get("price_max") || "");
      var check = form.querySelector('[name="in_stock"]');
      if (check) check.checked = inStock;
      var details = form.querySelector(".filters__panel");
      if (details && (sort || priceMin !== null || priceMax !== null || inStock || query.get("filters") === "1")) details.open = true;
      var reset = form.querySelector(".filters__actions a");
      if (reset) reset.setAttribute("href", location.pathname + (kind === "search" && q ? "?q=" + encodeURIComponent(q) : ""));
    }
    if (kind === "search") {
      var h1 = feed.querySelector(".h1");
      if (h1) h1.textContent = q ? "«" + q + "»" : "Найти товар";
      document.title = (q ? "«" + q + "» — поиск" : "Поиск") + " — DiDi-shop";
    }
  }

  // --- Карточка товара (web/catalog/product.html) ---

  function askHTML(p, ask) {
    var message = "Здравствуйте! Подскажите цену: " + p.name + " — " + location.origin + link("/product/" + p.slug + "/");
    var links = (ask || []).map(function (a) {
      var url = a.kind === "whatsapp" ? a.url.split("?")[0] + "?text=" + encodeURIComponent(message) : a.url;
      return '<a class="ask__link ask__link--' + esc(a.kind) + '" href="' + esc(url) + '" target="_blank" rel="noopener noreferrer"><span class="channel__icon" aria-hidden="true">' +
        icon(a.kind === "telegram" ? "send" : "chat", 20) + "</span><span>" + esc(a.title) + "</span></a>";
    }).join("") || '<a class="ask__link" href="' + link("/contacts/") + '"><span>Контакты магазина</span></a>';
    return '<details class="rise r4 ask" data-ask><summary class="cta ask__toggle"><span class="cta__label">Узнать</span>' +
      '<svg class="ic ask__chev" width="20" height="20" aria-hidden="true"><use href="#i-chevron"/></svg></summary><div class="ask__body">' + links + "</div></details>";
  }

  function renderProduct(data) {
    var slug = HERE.split("/")[2];
    var full = sim.product(slug);
    var pd = document.querySelector(".pd");
    var main = document.getElementById("main");
    if (!full || !sim.isLive(full)) {
      var target = pd || main;
      if (target) {
        target.outerHTML = '<section class="page">' + emptyHTML("Товар недоступен", "Его сняли с продажи или скрыли. Посмотрите другие товары.", "box",
          '<a class="btn btn--dark" href="' + link("/") + '">В каталог</a>') + "</section>";
      }
      document.title = "Товар недоступен — DiDi-shop";
      return;
    }
    if (!pd) return;
    var p = sim.publicProduct(full);
    var cat = p.category;
    var images = full.images.slice().sort(function (a, b) { return a.position - b.position; });
    var variants = full.variants.slice().sort(function (a, b) { return a.position - b.position || a.id - b.id; });
    var single = variants.length === 1 && !variants[0].size ? variants[0] : null;
    var sizes = variants.map(function (v) { return { v: v, available: sim.maxQuantity(v.id) > 0 }; });
    var inStock = sizes.some(function (s) { return s.available; });
    // Сколько уже в корзине по размерам — как web/views/catalog.product (state для site.js).
    var lineQty = {};
    sim.cart().lines.forEach(function (line) { lineQty[line.variant_id] = line.quantity; });
    var state = {};
    var inCartIds = [];
    sizes.forEach(function (s) {
      var q = lineQty[s.v.id] || 0;
      if (q) inCartIds.push(s.v.id);
      state[s.v.id] = { q: q, max: sim.maxQuantity(s.v.id), size: s.v.size || "Без размера" };
    });
    var chosen = single ? single.id : (inCartIds.length === 1 && state[inCartIds[0]].max > 0 ? inCartIds[0] : null);
    var chosenState = chosen ? state[chosen] : null;
    var inCartTotal = inCartIds.reduce(function (n, id) { return n + state[id].q; }, 0);
    var st = p.status;
    var off = discount(p);
    var t = tone(p.slug);

    var gallery = '<div class="pd__gallery"><a class="glass-btn pd__back" href="' + link("/category/" + cat.slug + "/") + '" data-back aria-label="Назад к категории ' + esc(cat.name) + '">' +
      icon("back", 22) + '</a><div class="pd__frame"><div class="hero tone-' + t + '">';
    if (images.length) {
      gallery += '<div class="hero__track" data-gallery tabindex="0" aria-label="Фото товара, ' + images.length + ' шт.">' +
        images.map(function (im, i) {
          return '<figure class="hero__slide" id="photo-' + (i + 1) + '">' + img(im.url, "(min-width: 900px) 560px, 100vw", "hero__photo", i === 0, p.name) + "</figure>";
        }).join("") + "</div>";
      if (images.length > 1) {
        gallery += '<div class="hero__dots" aria-hidden="true">' + images.map(function (im, i) {
          return '<a href="#photo-' + (i + 1) + '" tabindex="-1" class="' + (i === 0 ? "is-on" : "") + '"></a>';
        }).join("") + "</div>";
      }
    } else {
      gallery += '<div class="hero__empty">' + icon("box", 56) + "</div>";
    }
    gallery += "</div></div></div>";

    var head = '<div class="rise r1"><a class="tag" href="' + link("/category/" + cat.slug + "/") + '">' + esc(cat.name) + "</a>" +
      '<h1 class="pd__title">' + esc(p.name) + "</h1>";
    if (st) {
      head += '<p class="status status--' + esc(st.tone) + ' pd__status"' + (st.hint ? ' title="' + esc(st.hint) + '"' : "") + ">" + esc(st.name) + "</p>" +
        (st.hint ? '<p class="muted pd__status-hint">' + esc(st.hint) + "</p>" : "");
    }
    head += '<p class="price price--detail">' + (p.price_on_request ? '<span class="price__now price__now--ask">Цена по запросу</span>' :
      '<span class="price__now">' + rub(p.price_kopecks) + "&nbsp;₽</span>");
    if (p.compare_at_kopecks && !p.price_on_request) {
      head += '<s class="price__old"><span class="sr">Старая цена </span>' + rub(p.compare_at_kopecks) + "&nbsp;₽</s>" +
        (off ? '<span class="sale sale--inline">−' + off + "%</span>" : "");
    }
    head += "</p></div>";

    var desc = paragraphs(full.description);
    var descHTML = desc.length ? '<div class="rise r3 pd__desc">' + desc.map(function (x) { return "<p>" + esc(x).replace(/\n/g, "<br>") + "</p>"; }).join("") + "</div>" : "";
    var buy;
    if (p.price_on_request) {
      buy = '<div class="buy">' + descHTML + askHTML(p, data.ask) + "</div>";
    } else {
      buy = '<form class="buy" method="post" action="' + link("/cart/add/") + '" data-buy>';
      if (single) buy += '<input type="hidden" name="variant" value="' + single.id + '">';
      else {
        buy += '<fieldset class="rise r2 sizes"><legend class="label">Размер</legend><div class="sizes__list">' + sizes.map(function (s) {
          return '<label class="sz' + (s.available ? "" : " is-off") + '"><input type="radio" name="variant" value="' + s.v.id + '"' +
            (s.available ? "" : " disabled") + (s.v.id === chosen ? " checked" : "") + ' required><span>' + esc(s.v.size || "Без размера") + "</span></label>";
        }).join("") + "</div></fieldset>";
      }
      buy += descHTML + '<div class="rise r4 buy__bar">';
      if (inStock) {
        var q = chosenState ? chosenState.q : 0;
        buy += '<div class="incart-row" data-incart data-line-url="' + link("/cart/line/0/") + '"' + (inCartTotal ? "" : " hidden") + '>' +
          '<a class="incart" href="' + link("/cart/") + '">' + icon("bag", 16) + '<span data-incart-text>В корзине · ' + (q || inCartTotal) + ' шт.</span></a>' +
          '<div class="stepper" role="group" aria-label="Количество в корзине" data-incart-stepper' + (q ? "" : " hidden") + '>' +
          '<button class="stepper__btn" type="button" data-incart-step="-1" aria-label="Убрать одну">' + icon("minus", 18) + '</button>' +
          '<span class="stepper__value" data-incart-qty aria-live="polite">' + q + '</span>' +
          '<button class="stepper__btn" type="button" data-incart-step="1" aria-label="Добавить ещё одну"' + (q && q >= chosenState.max ? " disabled" : "") + '>' + icon("plus", 18) + '</button>' +
          '</div></div><script id="incart-state" type="application/json">' + JSON.stringify(state).replace(/</g, "\\u003c") + "</script>";
        buy += '<button class="cta" type="submit" data-cta><span class="cta__label" data-cta-label>' + (q ? "Добавить ещё" : "В корзину") + '</span><span class="cta__price">' + rub(p.price_kopecks) + "&nbsp;₽</span></button>" +
          '<button class="cta cta--alt" type="submit" data-buy-now><span class="cta__label">Купить сейчас</span></button>';
      } else {
        buy += '<button class="cta" type="button" disabled><span class="cta__label">Нет в наличии</span></button>';
      }
      buy += '<div id="buy-result" class="buy__result" aria-live="polite"></div></div></form>';
    }
    pd.innerHTML = gallery + '<div class="pd__info">' + head + buy + "</div>";
    document.title = p.price_on_request ? p.name + " — цена по запросу в DiDi-shop" : p.name + " — купить за " + rub(p.price_kopecks) + " ₽ в DiDi-shop";
    bindGallery(pd);
    bindBack(pd);
    if (TREE === "me") sim.recordView(slug);
    renderSimilar(slug);
  }

  function bindGallery(scope) {
    var track = scope.querySelector("[data-gallery]");
    if (!track) return;
    var dots = scope.querySelectorAll(".hero__dots a");
    if (!dots.length) return;
    track.addEventListener("scroll", function () {
      var index = Math.round(track.scrollLeft / track.clientWidth);
      dots.forEach(function (dot, i) { dot.classList.toggle("is-on", i === index); });
    }, { passive: true });
  }
  function bindBack(scope) {
    var back = scope.querySelector("[data-back]");
    if (back && document.referrer && document.referrer.indexOf(location.origin + "/") === 0 && history.length > 1) {
      back.addEventListener("click", function (event) { event.preventDefault(); history.back(); });
    }
  }

  function addToCart(form, submitter) {
    var input = form.querySelector('input[name="variant"]:checked') || form.querySelector('input[type="hidden"][name="variant"]');
    var result = form.querySelector("#buy-result");
    if (!input) {
      if (result) result.innerHTML = '<p class="note note--danger">Выберите размер.</p>';
      return;
    }
    if (submitter && submitter.hasAttribute("data-buy-now")) {
      // «Купить сейчас»: оформление только этого товара, корзина не меняется.
      if (sim.maxQuantity(input.value) < 1) {
        result.innerHTML = '<p class="note note--danger">Товара нет в наличии.</p>';
        return;
      }
      var target = "/checkout/?variant=" + input.value + "&qty=1";
      go(TREE === "me" ? ME + target : BASE + "/login/?next=" + encodeURIComponent(target));
      return;
    }
    var res = sim.cartAdd(input.value, 1);
    if (res.error) {
      result.innerHTML = '<p class="note note--danger">' + esc(res.error) + "</p>";
      return;
    }
    result.innerHTML = '<p class="buy__done" data-added>' + icon("check", 18) + 'Товар в корзине · <a href="' + link("/cart/") + '">Перейти в корзину</a></p>';
    setBadges();
    // «В корзине · N», «−/+» и «Добавить ещё» обновляет site.js — как после ответа сервера.
    form.dispatchEvent(new CustomEvent("didi:cart-added", { bubbles: true }));
  }

  // --- Корзина (web/cart/_cart.html) ---

  function cartHTML() {
    var cart = sim.cart();
    if (!cart.lines.length) {
      return '<div id="cart" class="cart">' + emptyHTML("Корзина пуста", "Загляните в каталог — там много интересного.", "bag",
        '<a class="btn btn--dark" href="' + link("/") + '">В каталог</a>') + "</div>";
    }
    var html = '<div id="cart" class="cart"><ul class="lines">';
    cart.lines.forEach(function (line) {
      var p = line.product;
      var available = p && line.status !== "unavailable";
      var href = available ? link("/product/" + p.slug + "/") : "";
      html += '<li class="line' + (line.status !== "ok" ? " line--problem" : "") + '" id="line-' + line.variant_id + '">';
      html += '<a class="line__img tone-' + (p ? tone(p.slug) : "lime") + '"' + (href ? ' href="' + href + '"' : "") + ' tabindex="-1" aria-hidden="true">' +
        (p ? img(p.cover_url, "96px", "line__photo", false, "") : "") + "</a>";
      html += '<div class="line__body"><p class="line__title">' + (available ? '<a href="' + href + '">' + esc(p.name) + "</a>" : p ? esc(p.name) : "Товар снят с продажи") + "</p>";
      if (line.size) html += '<p class="line__meta">Размер ' + esc(line.size) + "</p>";
      if (p && p.status && available) html += '<p class="status status--' + esc(p.status.tone) + '">' + esc(p.status.name) + "</p>";
      html += '<div class="line__parts">';
      if (line.status === "unavailable") html += '<p class="pill pill--neutral">Недоступен</p>';
      else if (line.status === "out_of_stock") html += '<p class="pill pill--danger">Нет в наличии</p>';
      else if (line.status === "exceeds_stock") html += '<p class="pill pill--warning">Доступно только ' + line.max_quantity + " шт.</p>";
      html += '<div class="line__foot">';
      if (line.status === "ok" || line.status === "exceeds_stock") {
        var fix = line.status === "exceeds_stock";
        html += '<div class="stepper" role="group" aria-label="Количество">' +
          '<form method="post" data-line="' + line.variant_id + '" data-op="dec"><button class="stepper__btn" type="submit" aria-label="Уменьшить"' + (line.quantity <= 1 ? " disabled" : "") + ">" + icon("minus", 18) + "</button></form>" +
          '<span class="stepper__value" aria-live="polite">' + line.quantity + "</span>" +
          '<form method="post" data-line="' + line.variant_id + '" data-op="' + (fix ? "fix" : "inc") + '"><button class="stepper__btn" type="submit" aria-label="' + (fix ? "Уменьшить до доступного" : "Увеличить") + '"' +
          (!fix && line.quantity >= line.max_quantity ? " disabled" : "") + ">" + icon(fix ? "check" : "plus", 18) + "</button></form></div>";
      }
      html += '<p class="line__price">' + (line.status === "ok" ? money(line.line_total_kopecks) : line.unit_price_kopecks ? '<span class="muted">' + money(line.unit_price_kopecks) + "/шт.</span>" : "") + "</p>";
      html += '<form method="post" data-line="' + line.variant_id + '" data-op="del"><button class="icon-btn" type="submit" aria-label="Удалить ' + esc(p ? p.name : "позицию") + '">' + icon("trash", 18) + "</button></form>";
      html += "</div></div></div></li>";
    });
    html += "</ul>";
    var free = sim.settings().free_from;
    html += '<aside class="summary" id="cart-summary"><p class="summary__row"><span>Товары, ' + cart.items_count + " шт.</span><span>" + money(cart.total_kopecks) + "</span></p>" +
      '<p class="summary__hint">Доставка курьером — при оформлении, бесплатно от ' + money(free) + ".</p>" +
      '<p class="summary__row summary__total"><span>Итого</span><span>' + money(cart.total_kopecks) + "</span></p>";
    if (cart.can_checkout) {
      html += '<a class="cta cta--link" href="' + (TREE === "me" ? ME + "/checkout/" : BASE + "/login/?next=" + encodeURIComponent("/checkout/")) + '"><span class="cta__label">Оформить заказ</span><span class="cta__price">' + money(cart.total_kopecks) + "</span></a>";
      if (TREE !== "me") html += '<p class="summary__hint">Для оформления нужно войти — корзина сохранится.</p>';
    } else {
      html += '<button class="cta" type="button" disabled><span class="cta__label">Уберите недоступные товары</span></button>';
    }
    return html + "</aside></div>";
  }

  function renderCart() {
    var current = document.getElementById("cart");
    if (!current) return;
    current.outerHTML = cartHTML();
    setBadges();
  }

  function changeLine(form) {
    var id = Number(form.getAttribute("data-line"));
    var op = form.getAttribute("data-op");
    var line = sim.cart().lines.filter(function (l) { return l.variant_id === id; })[0];
    if (!line) return renderCart();
    if (op === "del") sim.cartSet(id, 0);
    else if (op === "fix") sim.cartSet(id, line.max_quantity);
    else sim.cartSet(id, line.quantity + (op === "inc" ? 1 : -1));
    renderCart();
  }

  // --- Оформление (web/orders/checkout.html) ---

  function buyNowLine() {
    var variant = parseInt(query.get("variant"), 10);
    if (!variant) return null;
    return { variant: variant, quantity: Math.max(1, parseInt(query.get("qty"), 10) || 1) };
  }

  function renderCheckout() {
    var form = document.querySelector("[data-checkout]");
    if (!form) return;
    var buyNow = buyNowLine();
    var cart = sim.cart(buyNow ? [[buyNow.variant, buyNow.quantity]] : undefined);
    if (!cart.lines.length || (!buyNow && !cart.can_checkout)) { location.replace(link("/cart/")); return; }
    if (buyNow && !cart.can_checkout) {
      flash("Этого товара больше нет в наличии.", "danger");
      location.replace(link("/"));
      return;
    }
    var head = document.querySelector(".section-head");
    if (head) {
      head.querySelector(".overline").textContent = buyNow ? "Купить сейчас" : "Корзина";
      var note = head.querySelector(".section-head__note");
      if (buyNow && !note) {
        note = document.createElement("p");
        note.className = "section-head__note";
        note.textContent = "Только этот товар — корзина не изменится.";
        head.appendChild(note);
      } else if (!buyNow && note) note.remove();
    }
    var items = cart.total_kopecks;
    var mini = form.querySelector(".mini");
    mini.innerHTML = cart.lines.map(function (line) {
      return "<li><span>" + esc(line.product.name) + (line.size ? ", " + esc(line.size) : "") + " × " + line.quantity + "</span><span>" + money(line.line_total_kopecks) + "</span></li>";
    }).join("");
    var s = sim.settings();
    var options = sim.deliveryOptions(items);
    var deliveryBox = form.querySelector('input[name="delivery_method"]').closest(".choices");
    var picked = (form.querySelector('input[name="delivery_method"]:checked') || {}).value || "courier";
    if (!options.some(function (o) { return o.method === picked; })) picked = options[0].method;
    deliveryBox.innerHTML = options.map(function (o) {
      return '<label class="choice"><input type="radio" name="delivery_method" value="' + o.method + '" data-cost="' + o.cost_kopecks + '"' + (o.method === picked ? " checked" : "") + " required>" +
        '<span class="choice__body"><span class="choice__title">' + esc(o.title) + "</span>" +
        (o.address ? '<span class="choice__hint">' + esc(o.address) + "</span>" : '<span class="choice__hint">' + (o.cost_kopecks ? "Бесплатно от " : "Бесплатно — заказ от ") + money(s.free_from) + "</span>") +
        '</span><span class="choice__price">' + money(o.cost_kopecks) + "</span></label>";
    }).join("");
    form.querySelectorAll('input[name="payment_method"]').forEach(function (input) {
      var allowed = input.value === "online" ? s.online : s.cash;
      input.closest(".choice").hidden = !allowed;
      if (!allowed) input.checked = false;
    });
    var payment = form.querySelector('input[name="payment_method"]:checked');
    if (!payment) {
      var first = Array.prototype.filter.call(form.querySelectorAll('input[name="payment_method"]'), function (i) { return !i.closest(".choice").hidden; })[0];
      if (first) first.checked = true;
    }
    var last = sim.lastRecipient();
    var fill = function (name, value) { var el = form.querySelector('[name="' + name + '"]'); if (el && !el.value && value) el.value = value; };
    var me = sim.currentCustomer();
    if (last) {
      fill("recipient_name", last.name);
      fill("recipient_phone", last.phone);
      fill("delivery_address", last.address);
    } else if (me) {
      fill("recipient_name", [me.first_name, me.last_name].filter(Boolean).join(" "));
    }
    var rows = form.querySelectorAll(".summary__row");
    rows[0].children[1].textContent = money(items);
    var totalEl = form.querySelector("[data-total]");
    var costEl = form.querySelector("[data-delivery-cost]");
    totalEl.setAttribute("data-items", items);
    var address = form.querySelector("[data-address]");
    var update = function () {
      var chosen = form.querySelector('input[name="delivery_method"]:checked');
      var cost = chosen ? parseInt(chosen.getAttribute("data-cost"), 10) || 0 : 0;
      costEl.textContent = money(cost);
      totalEl.textContent = money(items + cost);
      if (address) address.hidden = !!chosen && chosen.value === "pickup";
    };
    form.addEventListener("change", function (event) { if (event.target.name === "delivery_method") update(); });
    update();
  }

  function clearErrors(form) {
    form.querySelectorAll(".field__error, .sim-error").forEach(function (el) { el.remove(); });
    form.querySelectorAll(".has-error").forEach(function (el) { el.classList.remove("has-error"); });
    form.querySelectorAll('[aria-invalid="true"]').forEach(function (el) { el.removeAttribute("aria-invalid"); });
  }
  function showErrors(form, errors, general) {
    clearErrors(form);
    var first = null;
    Object.keys(errors || {}).forEach(function (name) {
      var input = form.querySelector('[name="' + name + '"]');
      var field = input && (input.closest(".field") || input.closest(".panel"));
      var text = Array.isArray(errors[name]) ? errors[name][0] : errors[name];
      if (!field) { general = general || text; return; }
      field.classList.add("has-error");
      input.setAttribute("aria-invalid", "true");
      var p = document.createElement("p");
      p.className = "field__error";
      p.textContent = text;
      var anchor = input.closest(".choices") || input.closest(".check") || input;
      anchor.parentNode.insertBefore(p, anchor.nextSibling);
      if (!first) first = input;
    });
    if (general) {
      var note = document.createElement("p");
      note.className = "note note--danger sim-error";
      note.setAttribute("role", "alert");
      note.textContent = general;
      var target = form.querySelector(".panel__title") ? form.querySelector(".panel__title").nextSibling : form.firstChild;
      if (form.classList.contains("checkout")) form.insertBefore(note, form.firstChild);
      else form.insertBefore(note, target);
    }
    var submit = form.querySelector('button[type="submit"]');
    if (submit) setTimeout(function () { submit.disabled = false; }, 0);
    var focus = first || (general ? form : null);
    if (first) first.focus({ preventScroll: true });
    if (focus) (first ? first.closest(".field") || first : form).scrollIntoView({ block: "center", behavior: "smooth" });
  }

  function placeOrder(form) {
    var data = {};
    new FormData(form).forEach(function (value, key) { data[key] = value; });
    var res = sim.checkout(data, buyNowLine());
    if (res.error || res.errors) return showErrors(form, res.errors, res.error);
    setBadges();
    flash(res.order.payment_method === "online" ? "Заказ оформлен — оплатите его, чтобы мы начали сборку." : "Заказ " + res.order.number + " оформлен. Мы скоро свяжемся с вами.");
    go(ME + "/orders/" + res.order.number + "/");
  }

  // --- Заказы (web/orders/list.html, detail.html) ---

  function orderCard(o, current) {
    return '<a class="order-card' + (current ? " order-card--current" : "") + '" href="' + ME + "/orders/" + o.number + '/">' +
      (current ? '<span class="overline">Текущий заказ</span>' : "") +
      '<span class="order-card__head"><span class="order-card__num">' + esc(o.number) + '</span><span class="status status--' + STATUS_TONES[o.status] + '">' +
      esc(sim.statusLabel(o.status)) + "</span></span>" +
      '<span class="order-card__meta">' + (current ? date(o.created_at, false, true) + " · " + esc(sim.deliveryLabel(o.delivery_method)) :
        date(o.created_at, true, true) + " · " + plural(o.items.reduce(function (n, i) { return n + i.quantity; }, 0), "товар,товара,товаров")) + "</span>" +
      '<span class="order-card__total">' + money(o.total_kopecks) + "</span></a>";
  }

  function renderOrders() {
    var page = document.querySelector("#main .page");
    if (!page) return;
    page.querySelectorAll(".orders, .pager, .empty").forEach(function (el) { el.remove(); });
    var orders = sim.myOrders();
    var holder = document.createElement("div");
    holder.innerHTML = orders.length ? '<ul class="orders">' + orders.map(function (o) { return "<li>" + orderCard(o) + "</li>"; }).join("") + "</ul>" :
      emptyHTML("Заказов пока нет", "", "box", '<a class="btn btn--dark" href="' + link("/") + '">В каталог</a>');
    page.appendChild(holder.firstChild);
  }

  function renderOrder() {
    var number = HERE.split("/")[2];
    var o = sim.myOrder(number);
    var page = document.querySelector("#main .page");
    if (!page) return;
    if (!o) {
      page.innerHTML = emptyHTML("Заказ не найден", "Проверьте номер или откройте список заказов.", "box", '<a class="btn btn--dark" href="' + ME + '/orders/">Мои заказы</a>');
      return;
    }
    document.title = "Заказ " + o.number + " — DiDi-shop";
    var payment = o.payments[o.payments.length - 1] || null;
    var refund = payment && payment.refunds[payment.refunds.length - 1];
    var html = '<a class="back-link" href="' + ME + '/orders/">' + icon("chevron", 16, "flip") + "Мои заказы</a>" +
      '<header class="section-head section-head--row"><div><p class="overline">' + date(o.created_at, true, true) + '</p><h1 class="h1">Заказ <span class="nowrap">' + esc(o.number) + "</span></h1></div>" +
      '<span class="status status--' + STATUS_TONES[o.status] + '">' + esc(sim.statusLabel(o.status)) + "</span></header>";
    if (o.payment_method === "online") {
      html += '<div class="panel pay">';
      if (o.status === "awaiting_payment") {
        html += '<p class="pay__text">Оплатите заказ' + (o.pay_until ? " до " + time(o.pay_until) + " — после этого он отменится автоматически" : "") + ".</p>" +
          '<form method="post" data-pay="' + esc(o.number) + '"><button class="cta" type="submit"><span class="cta__label">Оплатить</span><span class="cta__price">' + money(o.total_kopecks) + "</span></button></form>" +
          '<p class="summary__hint">Демо: оплата проходит сразу, без банка.</p>';
      } else if (o.status === "cancelled" && refund) {
        html += '<p class="pay__text">Возврат денег: <b>' + (refund.status === "succeeded" ? "выполнен" : refund.status === "pending" ? "выполняется" : "задерживается — мы свяжемся с вами") + "</b>.</p>";
      } else if (payment && (payment.status === "succeeded" || payment.status === "refunded")) {
        html += '<p class="pay__text">' + icon("check", 18) + " Оплачено онлайн</p>";
      } else {
        html += '<p class="pay__text">Заказ не оплачен.</p>';
      }
      html += "</div>";
    }
    html += '<ul class="lines lines--static">' + o.items.map(function (item) {
      return '<li class="line"><span class="line__img tone-' + tone(item.product_slug) + '" aria-hidden="true">' + img(item.cover_url, "96px", "line__photo", false, "") + "</span>" +
        '<div class="line__body"><p class="line__title">' + esc(item.product_name) + '</p><p class="line__meta">' + (item.size ? "Размер " + esc(item.size) + " · " : "") +
        (item.status_name ? esc(item.status_name) + " · " : "") + item.quantity + " × " + money(item.price_kopecks) + "</p></div>" +
        '<p class="line__price">' + money(item.line_total_kopecks) + "</p></li>";
    }).join("") + "</ul>";
    html += '<div class="order-info"><div class="panel"><p class="panel__title">Получение</p><p>' + esc(sim.deliveryLabel(o.delivery_method)) + "</p>" +
      (o.delivery_address ? '<p class="muted">' + esc(o.delivery_address) + "</p>" : "") +
      '<p class="muted">' + esc(o.recipient_name) + (o.recipient_phone ? ", " + esc(o.recipient_phone) : "") + "</p>" +
      (o.comment ? '<p class="muted">«' + esc(o.comment) + "»</p>" : "") + "</div>" +
      '<div class="panel"><p class="summary__row"><span>Товары</span><span>' + money(o.items_total_kopecks) + '</span></p><p class="summary__row"><span>Доставка</span><span>' +
      money(o.delivery_kopecks) + '</span></p><p class="summary__row summary__total"><span>Итого</span><span>' + money(o.total_kopecks) + '</span></p><p class="muted">' +
      esc(sim.paymentLabel(o.payment_method)) + "</p></div></div>";
    if (o.status_history.length) {
      html += '<div class="panel"><p class="panel__title">История</p><ol class="history">' + o.status_history.map(function (h) {
        return '<li><span class="status status--' + STATUS_TONES[h.to_status] + '">' + esc(sim.statusLabel(h.to_status)) + '</span><span class="muted">' + date(h.created_at, false, true) + "</span>" +
          (h.comment ? '<p class="history__note">' + esc(h.comment) + "</p>" : "") + "</li>";
      }).join("") + "</ol></div>";
    }
    if (sim.canCancel(o)) {
      html += '<form class="cancel" method="post" data-cancel="' + esc(o.number) + '" data-message="Отменить заказ ' + esc(o.number) + "?" +
        (payment && payment.status === "succeeded" ? " Деньги вернутся на карту." : "") + '"><button class="btn btn--danger" type="submit">Отменить заказ</button></form>';
    }
    page.innerHTML = html;
  }

  // --- Профиль ---

  function avatarHTML(c, big) {
    var letter = String((c.first_name || c.email || "?").trim().charAt(0)).toUpperCase();
    return '<span class="avatar' + (big ? " avatar--big" : "") + '" data-avatar>' +
      (c.avatar ? '<img class="avatar__img" src="' + c.avatar + '" width="320" height="320" alt="">' : '<span class="avatar__letter" aria-hidden="true">' + esc(letter) + "</span>") + "</span>";
  }

  function railHTML(list) {
    var inCart = cartSlugs();
    return list.map(function (p) { return '<div class="hblock-rail__cell">' + cardHTML(p, false, inCart) + "</div>"; }).join("");
  }

  function renderProfile() {
    var me = sim.currentCustomer();
    if (!me) return;
    var page = document.querySelector("#main .page");
    var avatar = page.querySelector("[data-avatar]");
    if (avatar) avatar.outerHTML = avatarHTML(me, false);
    var name = page.querySelector(".me__name");
    if (name) name.textContent = me.first_name || "Мой аккаунт";
    var email = page.querySelector(".me__email");
    if (email) email.textContent = me.email;

    var orders = sim.myOrders();
    var current = page.querySelector(".order-card--current");
    var open = orders.filter(function (o) { return o.status !== "delivered" && o.status !== "cancelled"; })[0];
    if (open) {
      var holder = document.createElement("div");
      holder.innerHTML = orderCard(open, true);
      if (current) current.replaceWith(holder.firstChild);
      else page.insertBefore(holder.firstChild, page.querySelector("[data-me-purchases]"));
    } else if (current) current.remove();

    var box = page.querySelector("[data-me-purchases]");
    if (box) {
      var done = orders.filter(function (o) { return o.status === "delivered"; });
      box.querySelectorAll(".buys, .box__empty, .box__more").forEach(function (el) { el.remove(); });
      var html = done.length ? '<ul class="buys">' + done.slice(0, 3).map(function (o) {
        return '<li><a class="buy-row" href="' + ME + "/orders/" + o.number + '/"><span class="buy-row__main"><span class="buy-row__num">' + esc(o.number) + '</span><span class="buy-row__meta">' +
          date(o.created_at, true, false) + " · " + plural(o.items.length, "позиция,позиции,позиций") + '</span></span><span class="buy-row__total">' + money(o.total_kopecks) + "</span></a></li>";
      }).join("") + "</ul>" + (done.length > 3 ? '<p class="muted box__more">Всего получено заказов: ' + done.length + "</p>" : "") :
        '<p class="muted box__empty">Здесь появятся полученные заказы.</p>';
      box.insertAdjacentHTML("beforeend", html);
    }

    var cartBox = page.querySelector("[data-me-cart]");
    if (cartBox) {
      var cart = sim.cart();
      cartBox.querySelectorAll(".cart-peek, .box__empty, .box__all").forEach(function (el) { el.remove(); });
      if (cart.lines.length) {
        cartBox.querySelector(".box__head").insertAdjacentHTML("beforeend", '<a class="box__all" href="' + link("/cart/") + '">Открыть' + icon("chevron", 16) + "</a>");
        var count = cart.lines.reduce(function (n, l) { return n + l.quantity; }, 0);
        cartBox.insertAdjacentHTML("beforeend", '<a class="cart-peek" href="' + link("/cart/") + '"><span class="cart-peek__thumbs" aria-hidden="true">' +
          cart.lines.slice(0, 4).map(function (l) {
            return '<span class="cart-peek__thumb tone-' + tone(l.product ? l.product.slug : "") + '">' + (l.product ? img(l.product.cover_url, "56px", "card__photo", false, "") : "") + "</span>";
          }).join("") + '</span><span class="cart-peek__text"><b>' + count + ' шт.</b><span class="muted">на ' + money(cart.total_kopecks) + "</span></span></a>");
      } else {
        cartBox.insertAdjacentHTML("beforeend", '<p class="muted box__empty">Корзина пуста. <a href="' + link("/") + '">В каталог</a></p>');
      }
    }

    var viewedBox = page.querySelector("[data-me-viewed]");
    if (viewedBox) {
      var seen = sim.viewed(12);
      viewedBox.hidden = !seen.length;
      viewedBox.querySelector("[data-rail]").innerHTML = railHTML(seen);
    }
  }

  function renderProfileData() {
    var me = sim.currentCustomer();
    if (!me) return;
    var photo = document.querySelector("[data-photo]");
    if (photo) {
      photo.querySelector("[data-avatar]").outerHTML = avatarHTML(me, true);
      var pick = photo.querySelector("[data-pick-label]");
      if (pick) pick.textContent = me.avatar ? "Заменить" : "Загрузить";
      var remove = photo.querySelector("[data-avatar-remove]");
      if (remove) remove.hidden = !me.avatar;
    }
    var form = document.querySelector('form[action$="/profile/data/"]');
    if (form) {
      form.querySelector('[name="first_name"]').value = me.first_name || "";
      form.querySelector('[name="last_name"]').value = me.last_name || "";
      var mail = form.querySelector(".readonly");
      if (mail) mail.textContent = me.email;
    }
  }

  function renderSimilar(slug) {
    var list = sim.similar(slug, 12);
    var holder = document.querySelector(".pd-more");
    if (!list.length) { if (holder) holder.remove(); return; }
    var p = sim.product(slug);
    var cat = p && sim.category(p.category);
    if (!holder) {
      holder = document.createElement("div");
      holder.className = "pd-more";
      document.querySelector(".pd").insertAdjacentElement("afterend", holder);
    }
    holder.innerHTML = '<section class="similar" aria-labelledby="similar-title"><div class="hblock-head"><h2 class="hblock-head__title" id="similar-title">Похожие товары</h2>' +
      (cat ? '<a class="hblock-head__all" href="' + link("/category/" + cat.slug + "/") + '">Все' + icon("chevron", 16) + "</a>" : "") +
      '</div><div class="hblock-rail__track" data-rail>' + railHTML(list) + "</div></section>";
  }

  // --- Контакты и статьи ---

  function renderContacts() {
    var page = document.querySelector("#main .page");
    if (!page) return;
    var articles = sim.articles();
    var box = page.querySelector(".articles");
    var head = box ? box.previousElementSibling : null;
    if (!articles.length) {
      if (box) box.remove();
      if (head && head.classList.contains("section-head--sub")) head.remove();
      return;
    }
    var html = articles.map(function (a) {
      var cover = a.images.slice().sort(function (x, y) { return x.position - y.position; })[0];
      return '<a class="article-card" href="' + link("/articles/" + a.slug + "/") + '"><span class="article-card__img tone-' + tone(a.slug) + '">' +
        (cover ? img(cover.url, "(min-width: 900px) 380px, (min-width: 600px) 50vw, 100vw", "card__photo", false, "") : icon("box", 40, "article-card__ph")) +
        '</span><span class="article-card__body">' + (a.published_at ? '<span class="article-card__date">' + date(a.published_at, true, false) + "</span>" : "") +
        '<span class="article-card__title">' + esc(a.title) + "</span>" + (a.excerpt ? '<span class="article-card__text">' + esc(a.excerpt) + "</span>" : "") + "</span></a>";
    }).join("");
    if (!box) {
      var wrap = document.createElement("div");
      wrap.innerHTML = '<header class="section-head section-head--sub"><p class="overline">Журнал</p><h2 class="h1 h1--sub">Статьи</h2></header><div class="articles"></div>';
      var help = page.querySelector(".menu--help");
      while (wrap.firstChild) page.insertBefore(wrap.firstChild, help);
      box = page.querySelector(".articles");
    }
    box.innerHTML = html;
  }

  function renderArticle() {
    var slug = HERE.split("/")[2];
    var a = sim.article(slug);
    var post = document.querySelector(".post");
    if (!post) return;
    if (!a || !a.is_published || a.deleted_at) {
      post.innerHTML = emptyHTML("Статья недоступна", "Её сняли с публикации.", "box", '<a class="btn btn--dark" href="' + link("/contacts/") + '">Контакты и статьи</a>');
      return;
    }
    var images = a.images.slice().sort(function (x, y) { return x.position - y.position; });
    var t = tone(a.slug);
    var html = '<a class="back-link" href="' + link("/contacts/") + '">' + icon("chevron", 16, "flip") + "Контакты и статьи</a>";
    if (images.length) html += '<figure class="post__hero hero tone-' + t + '">' + img(images[0].url, "(min-width: 760px) 712px, 100vw", "hero__photo", true, a.title) + "</figure>";
    html += '<header class="section-head rise r1">' + (a.published_at ? '<p class="overline">' + date(a.published_at, true, false) + "</p>" : "") +
      '<h1 class="h1">' + esc(a.title) + "</h1>" + (a.excerpt ? '<p class="post__lead">' + esc(a.excerpt) + "</p>" : "") + "</header>";
    html += '<div class="post__body rise r2">' + paragraphs(a.body).map(function (p) { return "<p>" + esc(p).replace(/\n/g, "<br>") + "</p>"; }).join("") + "</div>";
    if (images.length > 1) {
      html += '<div class="post__gallery rise r3">' + images.slice(1).map(function (im) {
        return '<figure class="post__photo tone-' + t + '">' + img(im.url, "(min-width: 760px) 350px, 50vw", "card__photo", false, "") + "</figure>";
      }).join("") + "</div>";
    }
    post.innerHTML = html;
    document.title = a.title + " — DiDi-shop";
  }

  // --- Формы: на сайте — сервер, здесь — имитация ---

  function nextAfterLogin(form) {
    var next = form.querySelector('input[name="next"]');
    var value = (next && next.value) || query.get("next") || "";
    if (value) {
      var url = new URL(value, location.href);
      var local = localPath(url.pathname);
      if (local && local !== "/login/" && local !== "/register/") return ME + local + url.search;
    }
    return ME + "/profile/";
  }

  function onSubmit(event) {
    if (event.defaultPrevented) return; // тема, баннер — уже обработано site.js
    var form = event.target;
    var submitter = event.submitter;
    event.preventDefault();
    var action = localPath(new URL(form.getAttribute("action") || location.href, location.href).pathname);
    var value = function (name) { var el = form.querySelector('[name="' + name + '"]'); return el ? el.value : ""; };

    if (form.hasAttribute("data-line")) return changeLine(form);
    if (form.hasAttribute("data-buy")) return addToCart(form, submitter);
    if (form.hasAttribute("data-checkout") && !ROOM) return placeOrder(form);
    if (form.hasAttribute("data-pay")) {
      if (sim.payOrder(form.getAttribute("data-pay"))) {
        flash("Оплата прошла. Мы начали собирать заказ.");
        location.reload();
      }
      return;
    }
    if (form.hasAttribute("data-cancel")) {
      if (!window.confirm(form.getAttribute("data-message"))) return;
      if (sim.cancelOrder(form.getAttribute("data-cancel"))) {
        flash("Заказ отменён.", "info");
        location.reload();
      }
      return;
    }
    if ((form.method || "get").toLowerCase() === "get") {
      // Поиск и фильтры: адрес с параметрами, выборку делает renderListing.
      var params = new URLSearchParams();
      new FormData(form).forEach(function (v, k) { if (String(v).trim()) params.set(k, String(v).trim()); });
      if (submitter && submitter.name) params.set(submitter.name, submitter.value);
      var target = action === "/search/" || form.hasAttribute("data-quick") || form.hasAttribute("data-drop") ? link("/search/") : location.pathname;
      var s = params.toString();
      return go(target + (s ? "?" + s : ""));
    }
    if (action === "/login/") {
      var login = sim.login(value("email"), value("password"));
      if (login.admin) return go(BASE + "/panel/");
      if (login.error) return showErrors(form, {}, login.error);
      flash("Вы вошли.");
      return go(nextAfterLogin(form));
    }
    if (action === "/register/") {
      var consent = form.querySelector('[name="consent"]');
      var errors = {};
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value("email").trim())) errors.email = "Введите правильный адрес электронной почты.";
      if (value("password").length < 8) errors.password = "Пароль — не короче 8 символов.";
      if (consent && !consent.checked) errors.consent = "Нужно согласие на обработку персональных данных.";
      if (Object.keys(errors).length) return showErrors(form, errors);
      var reg = sim.register(value("email"), value("password"), value("first_name"));
      if (reg.errors) return showErrors(form, reg.errors);
      flash("Аккаунт создан. Добро пожаловать!");
      return go(nextAfterLogin(form));
    }
    if (action === "/password-reset/") {
      if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(value("email").trim())) return showErrors(form, { email: "Введите правильный адрес электронной почты." });
      return go(BASE + "/password-reset/confirm/?email=" + encodeURIComponent(value("email").trim()));
    }
    if (action === "/password-reset/confirm/") {
      var errs = {};
      if (!/^\d{6}$/.test(value("code").trim())) errs.code = "Код — 6 цифр из письма (в демо подойдут любые).";
      if (value("new_password").length < 8) errs.new_password = "Пароль — не короче 8 символов.";
      if (Object.keys(errs).length) return showErrors(form, errs);
      var who = sim.db().customers.filter(function (c) { return c.email === value("email").trim().toLowerCase(); })[0];
      if (who && who.status === "active") {
        who.password = value("new_password");
        sim.login(who.email, who.password);
        sim.updateCustomer({ password: value("new_password") });
        flash("Пароль изменён, вы вошли.");
        return go(ME + "/profile/");
      }
      return showErrors(form, { code: "Неверный или устаревший код." });
    }
    if (action === "/profile/data/") {
      sim.updateCustomer({ first_name: value("first_name"), last_name: value("last_name") });
      flash("Данные сохранены.");
      return location.reload();
    }
    if (action === "/profile/avatar/") {
      if (value("remove")) {
        sim.removeAvatar();
        flash("Фото удалено.");
        return location.reload();
      }
      var file = form.querySelector('[name="avatar"]').files[0];
      if (!file) return toast("Выберите файл с фото.");
      sim.setAvatar(file).then(function (saved) {
        flash(saved ? "Фото обновлено." : "Фото не поместилось в хранилище браузера.", saved ? "success" : "danger");
        location.reload();
      }, function (err) {
        toast(err && err.message === "size" ? "Файл больше 5 МБ." : "Допустимые форматы: JPEG, PNG, WebP.");
      });
      return;
    }
    if (action === "/profile/viewed/clear/") {
      sim.clearViewed();
      flash("История просмотров очищена.");
      return location.reload();
    }
    if (action === "/profile/password/") {
      var pe = {};
      if (!value("old_password")) pe.old_password = "Введите текущий пароль.";
      if (value("new_password").length < 8) pe.new_password = "Пароль — не короче 8 символов.";
      if (Object.keys(pe).length) return showErrors(form, pe);
      sim.updateCustomer({ password: value("new_password") });
      flash("Пароль изменён.");
      return go(ME + "/profile/");
    }
    if (action === "/profile/delete/") {
      if (!value("password")) return showErrors(form, { password: "Введите пароль." });
      if (!window.confirm("Удалить аккаунт? Это действие нельзя отменить.")) return;
      var del = sim.deleteAccount();
      if (del.error) return showErrors(form, {}, del.error);
      flash("Аккаунт удалён.", "info");
      return go(BASE + "/");
    }
    if (action === "/logout/") {
      sim.logout();
      flash("Вы вышли из аккаунта.", "info");
      return go(BASE + "/");
    }
    toast("Это действие в демо не выполняется");
  }

  // --- Новые товары, заказы, статьи и категории: страницы нет, Pages отдаёт 404 ---
  // 404 подгружает настоящую страницу того же вида и подставляет данные по адресу.

  function swapDocument(url) {
    return fetch(url).then(function (r) { return r.text(); }).then(function (html) {
      var doc = new DOMParser().parseFromString(html, "text/html");
      // Пока данные не подставлены, содержимое страницы-образца не показывается.
      doc.documentElement.setAttribute("data-sim-pending", "");
      document.documentElement.replaceWith(doc.documentElement);
      var scripts = Array.prototype.slice.call(document.querySelectorAll("script"));
      scripts.forEach(function (old) {
        var s = document.createElement("script");
        for (var i = 0; i < old.attributes.length; i++) s.setAttribute(old.attributes[i].name, old.attributes[i].value);
        s.async = false;
        s.textContent = old.textContent;
        old.replaceWith(s);
      });
    });
  }

  function dynamicRoute(data) {
    if (path.indexOf(BASE + "/panel/") === 0) {
      location.replace(BASE + "/panel/?route=" + encodeURIComponent(path.slice((BASE + "/panel/").length)));
      return true;
    }
    var t = data.templates || {};
    var prefix = TREE === "me" ? ME : BASE;
    var m;
    if ((m = HERE.match(/^\/product\/([^/]+)\/$/)) && sim.product(m[1]) && t.product) return swapDocument(prefix + t.product), true;
    if ((m = HERE.match(/^\/category\/([^/]+)\/$/)) && sim.categoryBySlug(m[1]) && t.category) return swapDocument(prefix + t.category), true;
    if ((m = HERE.match(/^\/articles\/([^/]+)\/$/)) && sim.article(m[1]) && t.article) return swapDocument(prefix + t.article), true;
    if (TREE === "me" && (m = HERE.match(/^\/orders\/([^/]+)\/$/)) && t.order) return swapDocument(ME + t.order), true;
    return false;
  }

  /** Шапка и нижняя панель администратора — «Панель» вместо «Войти»/«Профиль»
      (на сервере так рисуют web/partials/header.html и tabbar.html для is_staff). */
  function showPanelLinks() {
    var panel = BASE + "/panel/";
    document.querySelectorAll('.topnav a[href$="/login/"], .topnav a[href$="/profile/"]').forEach(function (a) {
      a.href = panel;
      a.textContent = "Панель";
      a.removeAttribute("aria-current");
      a.setAttribute("data-panel-link", "");
    });
    document.querySelectorAll('.topnav a[href$="/orders/"]').forEach(function (a) { a.remove(); });
    document.querySelectorAll('.tabbar .tab[href$="/profile/"]').forEach(function (a) {
      a.href = panel;
      a.classList.remove("is-on");
      a.removeAttribute("aria-current");
      a.setAttribute("data-panel-link", "");
      var label = a.querySelector("span:last-child");
      if (label) label.textContent = "Панель";
    });
  }

  // --- Старт ---

  if (!window.__didiPreviewBound) {
    window.__didiPreviewBound = true;
    document.addEventListener("submit", function (event) { if (window.__didiPreviewSubmit) window.__didiPreviewSubmit(event); });
  }
  // Обработчики — последней загруженной копии скрипта (после подмены страницы 404 он запускается снова).
  window.__didiPreviewSubmit = onSubmit;
  // «−/+» на карточке товара (site.js) — в «базу» демо вместо запроса к серверу.
  window.didiCartLine = function (variantId, quantity) {
    sim.cartSet(variantId, quantity);
    var line = sim.cart().lines.filter(function (l) { return l.variant_id === Number(variantId); })[0];
    return { quantity: line ? line.quantity : 0, count: sim.cartCount(), errors: [] };
  };

  Promise.all([sim.ready(), dataReady]).then(function (res) {
    var data = res[1];
    if (ROOM === "404" && dynamicRoute(data)) return;
    if (ROOM && ROOM !== "404") return; // отдельные состояния (ошибки форм и т. п.) — как есть
    if (sim.adminSignedIn()) {
      // Как на сервере (web/views/account.py): вошедший администратор смотрит магазин как
      // покупатель, а вход, регистрация и кабинет ведут в панель — второй вход не нужен.
      if (/^\/(login|register|profile|orders|checkout)\//.test(HERE)) {
        location.replace(BASE + "/panel/");
        return;
      }
      if (TREE === "me") { // страница магазина из дерева покупателя — та же страница гостя
        location.replace(BASE + HERE + location.search + location.hash);
        return;
      }
      showPanelLinks();
    }
    if (TREE === "me" && !sim.ensureCustomer()) {
      location.replace(BASE + "/login/?next=" + encodeURIComponent(HERE));
      return;
    }
    setBadges();
    renderFooter();
    filterPalettes();
    showFlash();
    var m;
    if (HERE === "/") { renderCats(""); renderHome(); }
    else if (HERE === "/products/") renderListing("products");
    else if (HERE === "/search/") renderListing("search");
    else if (/^\/category\/[^/]+\/$/.test(HERE)) renderListing("category");
    else if (/^\/product\/[^/]+\/$/.test(HERE)) renderProduct(data);
    else if (HERE === "/cart/") renderCart();
    else if (HERE === "/checkout/" && TREE === "me") renderCheckout();
    else if (HERE === "/orders/" && TREE === "me") renderOrders();
    else if ((m = HERE.match(/^\/orders\/([^/]+)\/$/)) && TREE === "me") renderOrder();
    else if (HERE === "/profile/" && TREE === "me") renderProfile();
    else if (HERE === "/profile/data/" && TREE === "me") renderProfileData();
    else if (HERE === "/contacts/") renderContacts();
    else if (/^\/articles\/[^/]+\/$/.test(HERE)) renderArticle();
    if (HERE === "/password-reset/confirm/") {
      var email = document.querySelector('[name="email"]');
      if (email && query.get("email")) email.value = query.get("email");
    }
  }).finally(function () {
    root.removeAttribute("data-sim-pending");
  });
})();
