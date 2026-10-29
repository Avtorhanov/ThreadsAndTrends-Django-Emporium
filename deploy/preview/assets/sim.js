/* DiDi-shop на GitHub Pages: имитация сервера в браузере (только превью, на боевом сайте файла нет).
   Одна «база» в localStorage на весь сайт превью: её читает и меняет панель администратора
   (admin-panel/src/preview/mock.ts → DidiSim.api) и витрина (preview.js → DidiSim.*). Поэтому
   товар, заказ, блок главной или тема, изменённые в панели, сразу видны в магазине, а заказ
   покупателя — в панели. Начальные данные — снимок настоящего API на демо-каталоге
   (panel/preview-api.json, deploy/preview/build.py). «Сбросить демо-данные» — DidiSim.reset(). */
(function () {
  "use strict";
  if (window.DidiSim) return;

  var script = document.currentScript;
  var BASE = (script && script.getAttribute("data-base")) || document.documentElement.getAttribute("data-preview-base") || "";
  var KEY = "didi-sim-db-v2";
  var LOOK_KEY = "didi-sim-look";
  var ADMIN_SESSION = "didi-preview-admin";
  var A = "/api/v1/admin";
  var PAGE = 20;
  var CART_MAX_QUANTITY = 10;
  var CART_MAX_ITEMS = 50;
  var LOW_STOCK = 3;

  var STATUS_LABELS = {
    awaiting_payment: "Ожидает оплаты", confirmed: "Принят", paid: "Оплачен", assembled: "Собран",
    shipped: "В пути", ready_for_pickup: "В пункте выдачи", delivered: "Получен", cancelled: "Отменён"
  };
  var PAYMENT_LABELS = { online: "Онлайн", on_delivery: "При получении" };
  var DELIVERY_LABELS = { courier: "Курьер", pickup: "Самовывоз" };
  var UNFINISHED = ["awaiting_payment", "confirmed", "paid", "assembled", "shipped", "ready_for_pickup"];
  var CUSTOMER_CANCEL = ["awaiting_payment", "confirmed", "paid", "assembled"];

  // --- Утилиты ---

  function clone(value) { return value === undefined ? undefined : JSON.parse(JSON.stringify(value)); }
  function now() { return new Date().toISOString(); }
  function byId(list, id) {
    id = Number(id);
    for (var i = 0; i < list.length; i++) if (list[i].id === id) return list[i];
    return null;
  }
  function next(db, name) {
    db.seq[name] = (db.seq[name] || 0) + 1;
    return db.seq[name];
  }
  function maxId(list) { return list.reduce(function (m, x) { return Math.max(m, x.id || 0); }, 0); }
  function digits(value) { return String(value || "").replace(/\D/g, ""); }
  function lower(value) { return String(value || "").trim().toLowerCase(); }

  var TRANSLIT = {
    а: "a", б: "b", в: "v", г: "g", д: "d", е: "e", ё: "e", ж: "zh", з: "z", и: "i", й: "y", к: "k", л: "l", м: "m",
    н: "n", о: "o", п: "p", р: "r", с: "s", т: "t", у: "u", ф: "f", х: "kh", ц: "ts", ч: "ch", ш: "sh", щ: "shch",
    ъ: "", ы: "y", ь: "", э: "e", ю: "yu", я: "ya"
  };
  function slugify(value) {
    var out = lower(value).split("").map(function (ch) { return TRANSLIT[ch] !== undefined ? TRANSLIT[ch] : ch; }).join("");
    return out.replace(/[^a-z0-9]+/g, "-").replace(/^-+|-+$/g, "").slice(0, 200) || "item";
  }
  function uniqueSlug(list, wanted, selfId) {
    var base = slugify(wanted);
    var slug = base;
    var n = 2;
    var taken = function (s) { return list.some(function (x) { return x.slug === s && x.id !== selfId; }); };
    while (taken(slug)) slug = base + "-" + n++;
    return slug;
  }

  function fail(status, body) { return { status: status, body: body }; }
  function bad(detail) { return fail(400, { detail: detail }); }
  function fields(errors) { return fail(400, errors); }
  function ok(body, status) { return { status: status || 200, body: body }; }

  // Цвет текста на фоне баннера — как content.home.ink_for (яркость по WCAG).
  function inkFor(color) {
    if (!/^#[0-9a-f]{6}$/i.test(color || "")) return "#13261C";
    var ch = function (i) {
      var v = parseInt(color.slice(i, i + 2), 16) / 255;
      return v <= 0.03928 ? v / 12.92 : Math.pow((v + 0.055) / 1.055, 2.4);
    };
    return 0.2126 * ch(1) + 0.7152 * ch(3) + 0.0722 * ch(5) > 0.18 ? "#13261C" : "#FFFFFF";
  }

  // --- Хранилище ---

  var cache = null;
  function load() {
    if (cache) return cache;
    try { cache = JSON.parse(localStorage.getItem(KEY) || "null"); } catch (e) { cache = null; }
    return cache;
  }
  function save(db) {
    cache = db;
    try {
      localStorage.setItem(KEY, JSON.stringify(db));
    } catch (e) {
      return false;
    }
    writeLook(db);
    return true;
  }
  // Свежие данные из другой вкладки (панель и магазин открыты рядом).
  window.addEventListener("storage", function (event) {
    if (event.key === KEY) cache = null;
  });

  function writeLook(db) {
    var t = db.theme;
    var look = {
      palettes: t.enabled, palette: t.default_palette, mode: t.default_mode, radius: t.default_radius,
      text: t.default_text || "s", nav: t.nav_style || "solid",
      // Вошёл ли покупатель: theme.js до отрисовки уводит на страницу нужного дерева (гость / /me/).
      user: db.session ? 1 : 0,
      out: db.loggedOut ? 1 : 0
    };
    try { localStorage.setItem(LOOK_KEY, JSON.stringify(look)); } catch (e) { /* без хранилища */ }
  }

  var readyPromise = null;
  function ready() {
    if (load()) return Promise.resolve(cache);
    if (readyPromise) return readyPromise;
    readyPromise = Promise.all([
      fetch(BASE + "/panel/preview-api.json").then(function (r) { return r.json(); }),
      fetch(BASE + "/static/preview/data.json").then(function (r) { return r.json(); })
    ]).then(function (res) {
      if (load()) return cache; // другая вкладка успела раньше
      var db = seed(res[0], res[1]);
      save(db);
      return db;
    });
    return readyPromise;
  }

  function reset() {
    cache = null;
    readyPromise = null;
    try {
      localStorage.removeItem(KEY);
      localStorage.removeItem(LOOK_KEY);
      localStorage.removeItem("didi-preview-cart");
    } catch (e) { /* без хранилища */ }
    return ready();
  }

  function seed(snap, data) {
    var pick = function (re) {
      return Object.keys(snap).filter(function (k) { return re.test(k); }).map(function (k) { return clone(snap[k]); })
        .sort(function (a, b) { return a.id - b.id; });
    };
    var products = pick(/\/admin\/catalog\/products\/\d+\/$/);
    var orders = pick(/\/admin\/orders\/\d+\/$/);
    var articles = pick(/\/admin\/content\/articles\/\d+\/$/);
    // Служебные покупатели сборки превью (корзины-образцы) в демо не нужны.
    var customers = clone(snap[A + "/customers/"].results).filter(function (c) {
      return !/^(sim|problem)@example\.ru$/.test(c.email);
    });
    customers.forEach(function (c) { c.password = ""; });
    var home = clone(snap[A + "/content/home/"]);
    var theme = clone(snap[A + "/content/theme/"]);
    if (!theme.nav_style) theme.nav_style = "solid";
    if (!theme.default_text) theme.default_text = "s";
    var variants = [];
    products.forEach(function (p) { variants = variants.concat(p.variants); });
    var images = [];
    products.forEach(function (p) { images = images.concat(p.images); });
    var articleImages = [];
    articles.forEach(function (a) { articleImages = articleImages.concat(a.images); });
    var orderItems = [];
    orders.forEach(function (o) {
      o.items.forEach(function (item) {
        var product = products.filter(function (p) { return p.slug === item.product_slug; })[0];
        var variant = product && product.variants.filter(function (v) { return v.sku === item.sku; })[0];
        item.product_id = product ? product.id : null;
        item.variant_id = variant ? variant.id : null;
        orderItems.push(item);
      });
    });
    var payments = [];
    var refunds = [];
    orders.forEach(function (o) {
      payments = payments.concat(o.payments);
      o.payments.forEach(function (p) { refunds = refunds.concat(p.refunds); });
    });
    var staff = clone(snap[A + "/staff/"]);
    var db = {
      v: 2,
      seededAt: now(),
      products: products,
      categories: clone(snap[A + "/catalog/categories/"]),
      statuses: clone(snap[A + "/catalog/statuses/"]),
      orders: orders,
      articles: articles,
      customers: customers,
      staff: staff,
      settings: clone(snap[A + "/content/settings/"]),
      theme: theme,
      home: { blocks: home.blocks, published: clone(home.blocks), has_changes: false, published_at: home.published_at },
      me: clone(snap[A + "/auth/me/"]),
      login: clone(snap._login),
      imageSources: data.images || {},
      carts: {},
      session: null,
      loggedOut: false,
      seq: {
        product: maxId(products), variant: maxId(variants), image: maxId(images), category: 0, status: 0,
        order: maxId(orders), item: maxId(orderItems), history: 0, payment: maxId(payments), refund: maxId(refunds),
        article: maxId(articles), articleImage: maxId(articleImages), block: 0, customer: 0, staff: maxId(staff),
        number: orders.reduce(function (m, o) { return Math.max(m, parseInt(o.number.replace(/\D/g, ""), 10) || 0); }, 100000)
      }
    };
    db.seq.category = maxId(db.categories);
    db.seq.status = maxId(db.statuses);
    db.seq.block = maxId(home.blocks);
    db.seq.homeImage = home.blocks.reduce(function (m, b) { return Math.max(m, maxId(b.images || [])); }, 0);
    db.seq.customer = Math.max(maxId(customers), maxId(staff));
    db.seq.staff = db.seq.customer;
    return db;
  }

  // --- Каталог ---

  function category(db, id) { return byId(db.categories, id); }
  function status(db, id) { return id ? byId(db.statuses, id) : null; }
  function totalStock(p) { return p.variants.reduce(function (n, v) { return n + v.stock; }, 0); }
  function coverUrl(p) {
    var first = p.images.slice().sort(function (a, b) { return a.position - b.position; })[0];
    return first ? first.url : null;
  }
  function categoryActive(db, id) {
    var c = category(db, id);
    if (!c || !c.is_active) return false;
    return c.parent ? categoryActive(db, c.parent) : true;
  }
  function isLive(db, p) { return !!p && p.is_active && !p.deleted_at && categoryActive(db, p.category); }
  function productRow(db, p) {
    var c = category(db, p.category);
    return {
      id: p.id, name: p.name, slug: p.slug, category: p.category, category_name: c ? c.name : "",
      price_kopecks: p.price_kopecks, compare_at_kopecks: p.compare_at_kopecks, status: p.status || null,
      is_active: p.is_active, deleted_at: p.deleted_at, total_stock: totalStock(p), cover_url: coverUrl(p),
      created_at: p.created_at, updated_at: p.updated_at
    };
  }
  function productDetail(db, p) {
    var row = productRow(db, p);
    row.description = p.description || "";
    row.variants = p.variants.slice().sort(function (a, b) { return a.position - b.position || a.id - b.id; }).map(function (v) {
      return { id: v.id, size: v.size, sku: v.sku, stock: v.stock, position: v.position };
    });
    row.images = p.images.slice().sort(function (a, b) { return a.position - b.position || a.id - b.id; }).map(function (i) {
      return { id: i.id, url: i.url, position: i.position };
    });
    return row;
  }
  // Товар для покупателя (витрина, подборки главной).
  function publicProduct(db, p) {
    var c = category(db, p.category);
    var s = status(db, p.status);
    return {
      id: p.id, slug: p.slug, name: p.name, price_kopecks: p.price_kopecks, price_on_request: p.price_kopecks === null,
      compare_at_kopecks: p.compare_at_kopecks, in_stock: totalStock(p) > 0, cover_url: coverUrl(p),
      category: c ? { id: c.id, slug: c.slug, name: c.name } : null,
      status: s ? { id: s.id, name: s.name, hint: s.hint, tone: s.tone } : null,
      created_at: p.created_at
    };
  }
  function liveProducts(db) {
    return db.products.filter(function (p) { return isLive(db, p); }).sort(function (a, b) {
      return a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : b.id - a.id;
    });
  }
  function descendants(db, id) {
    var ids = [Number(id)];
    db.categories.forEach(function (c) { if (c.parent === Number(id)) ids.push(c.id); });
    return ids;
  }
  function categoryRow(db, c) {
    var row = clone(c);
    row.products_count = db.products.filter(function (p) { return p.category === c.id && !p.deleted_at; }).length;
    row.children_count = db.categories.filter(function (x) { return x.parent === c.id; }).length;
    return row;
  }
  function statusRow(db, s) {
    var row = clone(s);
    row.products_count = db.products.filter(function (p) { return p.status === s.id && !p.deleted_at; }).length;
    return row;
  }
  function findVariant(db, id) {
    id = Number(id);
    for (var i = 0; i < db.products.length; i++) {
      var p = db.products[i];
      for (var j = 0; j < p.variants.length; j++) if (p.variants[j].id === id) return { product: p, variant: p.variants[j] };
    }
    return null;
  }
  function maxQuantity(db, found) {
    if (!found || !isLive(db, found.product) || found.product.price_kopecks === null) return 0;
    return Math.min(found.variant.stock, CART_MAX_QUANTITY);
  }

  // --- Заказы ---

  function allowedTransitions(o) {
    var flow = {
      awaiting_payment: ["cancelled"],
      confirmed: ["assembled", "cancelled"],
      paid: ["assembled", "cancelled"],
      assembled: [o.delivery_method === "pickup" ? "ready_for_pickup" : "shipped", "cancelled"],
      shipped: ["delivered"],
      ready_for_pickup: ["delivered", "cancelled"],
      delivered: [],
      cancelled: []
    };
    return (flow[o.status] || []).map(function (s) { return { status: s, label: STATUS_LABELS[s] }; });
  }
  function orderDetail(o) {
    var row = clone(o);
    row.status_display = STATUS_LABELS[o.status];
    row.allowed_transitions = allowedTransitions(o);
    row.can_retry_refund = o.payments.some(function (p) {
      return p.refunds.some(function (r) { return r.status === "canceled"; });
    });
    row.items.forEach(function (item) { delete item.product_id; delete item.variant_id; });
    return row;
  }
  function orderRow(o) {
    return {
      id: o.id, number: o.number, status: o.status, status_display: STATUS_LABELS[o.status], customer: clone(o.customer),
      recipient_name: o.recipient_name, recipient_phone: o.recipient_phone, payment_method: o.payment_method,
      delivery_method: o.delivery_method, total_kopecks: o.total_kopecks,
      items_count: o.items.reduce(function (n, i) { return n + i.quantity; }, 0), created_at: o.created_at
    };
  }
  function setStatus(db, o, to, by, actor, comment, notify) {
    var from = o.status;
    if (from === to) return o;
    o.status_history.push({
      from_status: from, to_status: to, to_status_display: STATUS_LABELS[to], changed_by: by,
      comment: comment || "", created_at: now(), actor_email: actor || null, notified: notify !== false
    });
    o.status = to;
    o.status_display = STATUS_LABELS[to];
    o.updated_at = now();
    if (to === "cancelled") {
      // Остатки возвращаются на склад, оплаченный онлайн-заказ — возврат денег.
      o.items.forEach(function (item) {
        var found = item.variant_id ? findVariant(db, item.variant_id) : null;
        if (found) found.variant.stock += item.quantity;
      });
      o.pay_until = null;
      o.payments.forEach(function (p) {
        if (p.status === "succeeded") {
          p.status = "refunded";
          p.status_display = "Возвращён";
          p.refunds.push({
            id: next(db, "refund"), amount_kopecks: p.amount_kopecks, status: "succeeded", status_display: "Выполнен",
            reason: "order_cancelled", reason_display: "Заказ отменён", provider_refund_id: "ref-sim-" + db.seq.refund,
            cancellation_reason: "", created_at: now()
          });
        } else if (p.status === "pending") {
          p.status = "canceled";
          p.status_display = "Отменён";
          p.cancellation_reason = "canceled_by_merchant";
        }
      });
    }
    return o;
  }

  function deliveryOptions(db, itemsTotal) {
    var s = effectiveSettings(db);
    var courier = itemsTotal >= s.free_from ? 0 : s.courier;
    var list = [{ method: "courier", title: "Курьером", cost_kopecks: courier, address: "" }];
    if (s.pickup_enabled && s.pickup_address) list.push({ method: "pickup", title: "Самовывоз", cost_kopecks: 0, address: s.pickup_address });
    return list;
  }
  function effectiveSettings(db) {
    var s = db.settings;
    var d = s.defaults || {};
    var pick = function (key) { return s[key] === null || s[key] === "" || s[key] === undefined ? d[key] : s[key]; };
    return {
      courier: pick("delivery_courier_kopecks"),
      free_from: pick("delivery_free_from_kopecks"),
      pickup_enabled: !!s.pickup_enabled,
      pickup_address: pick("pickup_address") || "",
      cash: !!s.cash_on_delivery_enabled,
      online: s.online_payment_available !== false,
      timeout: pick("unpaid_timeout_minutes") || 30,
      seller: {
        name: pick("seller_name") || "", inn: pick("seller_inn") || "", ogrn: pick("seller_ogrn") || "",
        address: pick("seller_address") || "", phone: pick("seller_phone") || "", email: pick("seller_email") || ""
      }
    };
  }

  // --- Сводка ---

  function summary(db) {
    var start = new Date();
    start.setHours(0, 0, 0, 0);
    var since = function (days) { return new Date(start.getTime() - (days - 1) * 86400000); };
    var period = function (from) {
      var orders = db.orders.filter(function (o) { return new Date(o.created_at) >= from && o.status !== "cancelled"; });
      return {
        orders: orders.length,
        turnover_kopecks: orders.filter(function (o) { return o.status !== "awaiting_payment"; })
          .reduce(function (n, o) { return n + o.total_kopecks; }, 0)
      };
    };
    var count = function (list) { return db.orders.filter(function (o) { return list.indexOf(o.status) >= 0; }).length; };
    var low = [];
    db.products.forEach(function (p) {
      if (p.deleted_at) return;
      p.variants.forEach(function (v) {
        if (v.stock <= LOW_STOCK) low.push({ product_id: p.id, product_name: p.name, size: v.size, sku: v.sku, stock: v.stock });
      });
    });
    low.sort(function (a, b) { return a.stock - b.stock || (a.product_name < b.product_name ? -1 : 1); });
    return {
      generated_at: now(), today: period(start), last_7_days: period(since(7)), last_30_days: period(since(30)),
      awaiting_payment: count(["awaiting_payment"]), to_assemble: count(["confirmed", "paid"]),
      to_deliver: count(["assembled", "shipped", "ready_for_pickup"]), low_stock_threshold: LOW_STOCK,
      low_stock_count: low.length, low_stock: low.slice(0, 8)
    };
  }

  // --- Главная из блоков ---

  function blockProducts(db, b) {
    var live = liveProducts(db);
    var list;
    if (b.source === "category" && b.category) {
      var ids = descendants(db, b.category);
      list = live.filter(function (p) { return ids.indexOf(p.category) >= 0; });
    } else if (b.source === "manual") {
      list = (b.product_ids || []).map(function (id) { return byId(db.products, id); }).filter(function (p) { return isLive(db, p); });
    } else {
      list = live;
    }
    return list.slice(0, 12).map(function (p) { return publicProduct(db, p); });
  }
  // Картинки баннера: [{id, url}]; снимок до галерей хранил одну картинку (image_url).
  function bannerImages(b) {
    if (b.images) return b.images;
    return b.image_url ? [{ id: 0, url: b.image_url }] : [];
  }
  var LINK_PAGES = { products: ["Все товары", "/products/"], contacts: ["Контакты", "/contacts/"], delivery: ["Доставка и оплата", "/legal/delivery/"] };
  function resolveLinks(db, links) {
    var out = [];
    (links || []).forEach(function (l) {
      if (l.kind === "category") {
        var c = byId(db.categories, l.id);
        if (c && c.is_active) out.push({ kind: "category", title: l.title || c.name, url: "/category/" + c.slug + "/", slug: c.slug });
      } else if (l.kind === "article") {
        var a = byId(db.articles, l.id);
        if (a && a.is_published && !a.deleted_at) out.push({ kind: "article", title: l.title || a.title, url: "/articles/" + a.slug + "/", slug: a.slug });
      } else if (l.kind === "page" && LINK_PAGES[l.key]) {
        out.push({ kind: "page", title: l.title || LINK_PAGES[l.key][0], url: LINK_PAGES[l.key][1], slug: l.key });
      } else if (l.kind === "url") {
        out.push({ kind: "url", title: l.title, url: l.url, slug: "" });
      }
    });
    return out;
  }
  function homeBlock(db, b) {
    var row = clone(b);
    row.ink = inkFor(b.color);
    row.preview_products = b.kind === "collection" ? blockProducts(db, b) : [];
    var images = bannerImages(b);
    row.images = clone(images);
    row.image_ids = images.map(function (x) { return x.id; });
    row.image_url = images.length ? images[0].url : null;
    row.product = b.product || null;
    var product = b.kind === "banner" && b.product ? byId(db.products, b.product) : null;
    row.preview_product = product && isLive(db, product) ? publicProduct(db, product) : null;
    row.preview_images = b.kind !== "banner" ? [] : images.length ? images.map(function (x) { return x.url; }) :
      row.preview_product ? product.images.slice().sort(function (x, y) { return x.position - y.position; }).slice(0, 6).map(function (x) { return x.url; }) : [];
    row.links = clone(b.links || []);
    row.preview_links = b.kind === "categories" ? resolveLinks(db, b.links) : [];
    return row;
  }
  function homeState(db) {
    return {
      blocks: db.home.blocks.slice().sort(function (a, b) { return a.position - b.position; }).map(function (b) { return homeBlock(db, b); }),
      has_changes: db.home.has_changes, published_at: db.home.published_at
    };
  }
  function touchHome(db) { db.home.has_changes = true; }

  // --- Фото: файл → уменьшенная копия data:URL (localStorage вмещает несколько мегабайт) ---

  function readImage(file, allowGif) {
    return new Promise(function (resolve, reject) {
      if (!file || !/^image\//.test(file.type || "")) return reject(new Error("type"));
      if (file.type === "image/gif") {
        // GIF баннера — как есть (иначе пропадёт анимация); большой не влезет в хранилище.
        if (!allowGif) return reject(new Error("type"));
        if (file.size > 1500000) return reject(new Error("size"));
        var reader = new FileReader();
        reader.onload = function () { resolve(reader.result); };
        reader.onerror = function () { reject(new Error("decode")); };
        reader.readAsDataURL(file);
        return;
      }
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        var max = 900;
        var scale = Math.min(1, max / Math.max(img.naturalWidth, img.naturalHeight));
        var canvas = document.createElement("canvas");
        canvas.width = Math.round(img.naturalWidth * scale);
        canvas.height = Math.round(img.naturalHeight * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/jpeg", 0.8));
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("decode")); };
      img.src = url;
    });
  }

  // --- API панели: метод + путь + тело → { status, body } (как у Django REST framework) ---

  function paginate(list, page, path, query) {
    page = Math.max(1, parseInt(page, 10) || 1);
    var pages = Math.max(1, Math.ceil(list.length / PAGE));
    var link = function (n) {
      var q = new URLSearchParams(query);
      q.set("page", n);
      return path + "?" + q.toString();
    };
    return {
      count: list.length, next: page < pages ? link(page + 1) : null, previous: page > 1 ? link(page - 1) : null,
      results: list.slice((page - 1) * PAGE, page * PAGE)
    };
  }

  function validateProduct(db, body, current) {
    var errors = {};
    var name = body.name !== undefined ? String(body.name).trim() : current ? current.name : "";
    if (!name) errors.name = ["Обязательное поле."];
    var catId = body.category !== undefined ? body.category : current ? current.category : null;
    var cat = catId ? category(db, catId) : null;
    if (!cat) errors.category = ["Выберите категорию."];
    else if (db.categories.some(function (c) { return c.parent === cat.id; })) errors.category = ["Товары — только в конечных категориях."];
    var price = body.price_kopecks !== undefined ? body.price_kopecks : current ? current.price_kopecks : null;
    var compare = body.compare_at_kopecks !== undefined ? body.compare_at_kopecks : current ? current.compare_at_kopecks : null;
    if (price !== null && price !== undefined && !(price > 0)) errors.price_kopecks = ["Цена должна быть больше нуля."];
    if (compare !== null && compare !== undefined) {
      if (price === null || price === undefined) errors.compare_at_kopecks = ["Старая цена — только вместе с ценой."];
      else if (compare <= price) errors.compare_at_kopecks = ["Старая цена должна быть больше текущей."];
    }
    if (body.slug) {
      if (!/^[-a-zA-Z0-9_]+$/.test(body.slug)) errors.slug = ["Только латиница, цифры, дефис и подчёркивание."];
      else if (db.products.some(function (p) { return p.slug === body.slug && (!current || p.id !== current.id); })) errors.slug = ["Такой адрес уже занят."];
    }
    return Object.keys(errors).length ? errors : null;
  }

  function newVariant(db, p, v, index) {
    var size = String(v.size || "").trim();
    var id = next(db, "variant");
    return {
      id: id, size: size, sku: String(v.sku || "").trim() || "DD-" + p.id + (size ? "-" + size.replace(/\s+/g, "") : ""),
      stock: Math.max(0, parseInt(v.stock, 10) || 0), position: v.position !== undefined ? v.position : index
    };
  }

  function checkVariant(p, size, selfId) {
    var others = p.variants.filter(function (v) { return v.id !== selfId; });
    if (others.some(function (v) { return v.size === size; })) return size ? "Такой размер уже есть." : "Вариант без размера уже есть.";
    if (size === "" && others.length) return "«Без размера» нельзя сочетать с размерами.";
    if (size !== "" && others.some(function (v) { return v.size === ""; })) return "Сначала удалите вариант «Без размера».";
    return "";
  }

  function articleRow(a) {
    var row = clone(a);
    delete row.body;
    delete row.images;
    row.images_count = a.images.length;
    row.cover_url = a.images.length ? a.images.slice().sort(function (x, y) { return x.position - y.position; })[0].url : null;
    return row;
  }
  function articleDetail(a) {
    var row = articleRow(a);
    row.body = a.body;
    row.images = a.images.slice().sort(function (x, y) { return x.position - y.position; });
    return row;
  }

  function customerRow(c) {
    var row = clone(c);
    delete row.password;
    return row;
  }

  function staffMember(m) { return clone(m); }

  function themeState(db) { return clone(db.theme); }

  var routes = [];
  function route(method, pattern, handler) { routes.push({ method: method, re: new RegExp("^" + A + pattern + "$"), handler: handler }); }

  route("GET", "/auth/me/", function (db) {
    return signedIn() ? ok(db.me) : fail(401, { detail: "Нужен вход." });
  });
  route("POST", "/auth/login/", function (db, m, q, body) {
    if (lower(body.email) === db.login.email && body.password === db.login.password) {
      setSignedIn(true);
      return ok(db.me);
    }
    return bad("Неверный email или пароль.");
  });
  route("POST", "/auth/logout/", function () { setSignedIn(false); return ok(null, 204); });
  route("GET", "/auth/csrf/", function () { return ok(null, 204); });

  route("GET", "/summary/", function (db) { return ok(summary(db)); });

  // Заказы
  route("GET", "/orders/", function (db, m, q) {
    var list = db.orders.slice();
    var s = lower(q.get("search"));
    if (s) {
      var d = digits(s);
      list = list.filter(function (o) {
        return lower(o.number).indexOf(s) >= 0 || lower(o.customer.email).indexOf(s) >= 0 ||
          lower(o.recipient_name).indexOf(s) >= 0 || (d.length >= 3 && digits(o.recipient_phone).indexOf(d) >= 0);
      });
    }
    if (q.get("status")) list = list.filter(function (o) { return o.status === q.get("status"); });
    if (q.get("unfinished") === "true") list = list.filter(function (o) { return UNFINISHED.indexOf(o.status) >= 0; });
    if (q.get("payment_method")) list = list.filter(function (o) { return o.payment_method === q.get("payment_method"); });
    if (q.get("delivery_method")) list = list.filter(function (o) { return o.delivery_method === q.get("delivery_method"); });
    var from = q.get("created_from");
    var to = q.get("created_to");
    if (from) list = list.filter(function (o) { return new Date(o.created_at) >= new Date(from + "T00:00:00"); });
    if (to) list = list.filter(function (o) { return new Date(o.created_at) <= new Date(to + "T23:59:59"); });
    list.sort(function (a, b) { return a.created_at < b.created_at ? 1 : -1; });
    return ok(paginate(list.map(orderRow), q.get("page"), A + "/orders/", q));
  });
  route("GET", "/orders/(\\d+)/", function (db, m) {
    var o = byId(db.orders, m[1]);
    return o ? ok(orderDetail(o)) : fail(404, { detail: "Не найдено." });
  });
  route("POST", "/orders/(\\d+)/transition/", function (db, m, q, body) {
    var o = byId(db.orders, m[1]);
    if (!o) return fail(404, { detail: "Не найдено." });
    if (o.status === body.status) return ok(orderDetail(o));
    var allowed = allowedTransitions(o).map(function (t) { return t.status; });
    if (allowed.indexOf(body.status) < 0) return bad(transitionError(o, body.status));
    setStatus(db, o, body.status, "admin", db.me.email, String(body.comment || "").trim(), body.notify !== false);
    return { status: 200, body: orderDetail(o), save: true };
  });
  function transitionError(o, to) {
    return "Нельзя перевести заказ из статуса «" + STATUS_LABELS[o.status] + "» в «" + (STATUS_LABELS[to] || to) + "».";
  }
  // Групповая обработка: каждый заказ проверяется отдельно, неподходящие — в skipped.
  route("POST", "/orders/bulk-transition/", function (db, m, q, body) {
    var ids = Array.isArray(body.ids) ? body.ids.map(Number) : [];
    if (!ids.length) return fail(400, { ids: ["Отметьте хотя бы один заказ."] });
    if (ids.length > 100) return fail(400, { ids: ["Не больше 100 заказов за раз."] });
    if (!STATUS_LABELS[body.status]) return fail(400, { status: ["Неизвестный статус."] });
    var comment = String(body.comment || "").replace(/\s+/g, " ").trim();
    var updated = [];
    var skipped = [];
    db.orders.filter(function (o) { return ids.indexOf(o.id) >= 0; })
      .sort(function (a, b) { return a.created_at < b.created_at ? -1 : 1; })
      .forEach(function (o) {
        var allowed = allowedTransitions(o).map(function (t) { return t.status; });
        if (o.status === body.status) skipped.push({ id: o.id, number: o.number, reason: "Уже в этом статусе." });
        else if (allowed.indexOf(body.status) < 0) skipped.push({ id: o.id, number: o.number, reason: transitionError(o, body.status) });
        else {
          setStatus(db, o, body.status, "admin", db.me.email, comment, body.notify !== false);
          updated.push(o.id);
        }
      });
    return { status: 200, body: { updated: updated, skipped: skipped }, save: updated.length > 0 };
  });
  route("POST", "/orders/(\\d+)/refund/", function (db, m) {
    var o = byId(db.orders, m[1]);
    if (!o) return fail(404, { detail: "Не найдено." });
    o.payments.forEach(function (p) {
      p.refunds.forEach(function (r) { if (r.status === "canceled") { r.status = "succeeded"; r.status_display = "Выполнен"; p.status = "refunded"; } });
    });
    return { status: 200, body: orderDetail(o), save: true };
  });
  route("POST", "/orders/(\\d+)/payment-sync/", function (db, m) {
    var o = byId(db.orders, m[1]);
    return o ? ok(orderDetail(o)) : fail(404, { detail: "Не найдено." });
  });

  // Клиенты
  route("GET", "/customers/", function (db, m, q) {
    var list = db.customers.slice();
    var s = lower(q.get("search"));
    if (s) list = list.filter(function (c) { return lower(c.email + " " + c.first_name + " " + c.last_name).indexOf(s) >= 0; });
    if (q.get("status")) list = list.filter(function (c) { return c.status === q.get("status"); });
    list.sort(function (a, b) { return a.date_joined < b.date_joined ? 1 : -1; });
    return ok(paginate(list.map(customerRow), q.get("page"), A + "/customers/", q));
  });
  route("POST", "/customers/(\\d+)/(block|unblock|delete)/", function (db, m) {
    var c = byId(db.customers, m[1]);
    if (!c) return fail(404, { detail: "Не найдено." });
    if (m[2] === "delete") {
      var open = db.orders.some(function (o) { return o.customer.id === c.id && UNFINISHED.indexOf(o.status) >= 0; });
      if (open) return bad("У клиента есть незавершённые заказы — удалить нельзя.");
      c.status = "deleted";
      c.deleted_at = now();
      c.email = "deleted-" + c.id + "@deleted.invalid";
      c.first_name = "";
      c.last_name = "";
      db.orders.forEach(function (o) {
        if (o.customer.id === c.id) { o.customer.is_deleted = true; o.customer.email = c.email; }
      });
    } else {
      c.status = m[2] === "block" ? "blocked" : "active";
    }
    return { status: 200, body: customerRow(c), save: true };
  });

  // Категории
  route("GET", "/catalog/categories/", function (db) {
    return ok(db.categories.slice().sort(function (a, b) { return a.position - b.position || a.id - b.id; }).map(function (c) { return categoryRow(db, c); }));
  });
  route("POST", "/catalog/categories/", function (db, m, q, body) {
    var name = String(body.name || "").trim();
    if (!name) return fields({ name: ["Обязательное поле."] });
    var parent = body.parent ? category(db, body.parent) : null;
    if (body.parent && !parent) return fields({ parent: ["Нет такой категории."] });
    if (parent && parent.parent) return fields({ parent: ["Не больше двух уровней."] });
    if (parent && db.products.some(function (p) { return p.category === parent.id; })) return fields({ parent: ["В категории есть товары — подкатегорию создать нельзя."] });
    var c = {
      id: next(db, "category"), name: name, slug: body.slug || uniqueSlug(db.categories, name), parent: parent ? parent.id : null,
      position: body.position !== undefined ? body.position : db.categories.length, is_active: body.is_active !== false,
      created_at: now(), updated_at: now()
    };
    db.categories.push(c);
    return { status: 201, body: categoryRow(db, c), save: true };
  });
  route("PATCH", "/catalog/categories/(\\d+)/", function (db, m, q, body) {
    var c = category(db, m[1]);
    if (!c) return fail(404, { detail: "Не найдено." });
    if (body.name !== undefined) {
      if (!String(body.name).trim()) return fields({ name: ["Обязательное поле."] });
      c.name = String(body.name).trim();
    }
    ["slug", "position", "is_active"].forEach(function (k) { if (body[k] !== undefined) c[k] = body[k]; });
    if (body.parent !== undefined) c.parent = body.parent;
    c.updated_at = now();
    return { status: 200, body: categoryRow(db, c), save: true };
  });
  route("DELETE", "/catalog/categories/(\\d+)/", function (db, m) {
    var c = category(db, m[1]);
    if (!c) return fail(404, { detail: "Не найдено." });
    if (db.products.some(function (p) { return p.category === c.id; })) return bad("В категории есть товары (в том числе удалённые) — её можно только скрыть.");
    if (db.categories.some(function (x) { return x.parent === c.id; })) return bad("Сначала удалите подкатегории.");
    db.categories.splice(db.categories.indexOf(c), 1);
    return { status: 204, body: null, save: true };
  });

  // Статусы товаров
  route("GET", "/catalog/statuses/", function (db) {
    return ok(db.statuses.slice().sort(function (a, b) { return a.position - b.position || a.id - b.id; }).map(function (s) { return statusRow(db, s); }));
  });
  route("POST", "/catalog/statuses/", function (db, m, q, body) {
    var name = String(body.name || "").trim();
    if (!name) return fields({ name: ["Обязательное поле."] });
    if (db.statuses.some(function (s) { return lower(s.name) === lower(name); })) return fields({ name: ["Такой статус уже есть."] });
    var s = { id: next(db, "status"), name: name, hint: String(body.hint || ""), tone: body.tone || "neutral", position: body.position !== undefined ? body.position : db.statuses.length };
    db.statuses.push(s);
    return { status: 201, body: statusRow(db, s), save: true };
  });
  route("PATCH", "/catalog/statuses/(\\d+)/", function (db, m, q, body) {
    var s = status(db, m[1]);
    if (!s) return fail(404, { detail: "Не найдено." });
    ["name", "hint", "tone", "position"].forEach(function (k) { if (body[k] !== undefined) s[k] = body[k]; });
    return { status: 200, body: statusRow(db, s), save: true };
  });
  route("DELETE", "/catalog/statuses/(\\d+)/", function (db, m) {
    var s = status(db, m[1]);
    if (!s) return fail(404, { detail: "Не найдено." });
    db.products.forEach(function (p) { if (p.status === s.id) p.status = null; });
    db.statuses.splice(db.statuses.indexOf(s), 1);
    return { status: 204, body: null, save: true };
  });

  // Товары
  route("GET", "/catalog/products/", function (db, m, q) {
    var list = db.products.slice();
    var st = q.get("status");
    if (st === "deleted") list = list.filter(function (p) { return p.deleted_at; });
    else {
      list = list.filter(function (p) { return !p.deleted_at; });
      if (st === "active") list = list.filter(function (p) { return p.is_active; });
      if (st === "inactive") list = list.filter(function (p) { return !p.is_active; });
    }
    var s = lower(q.get("search"));
    if (s) list = list.filter(function (p) {
      return lower(p.name).indexOf(s) >= 0 || p.variants.some(function (v) { return lower(v.sku).indexOf(s) >= 0; });
    });
    if (q.get("category")) {
      var ids = descendants(db, q.get("category"));
      list = list.filter(function (p) { return ids.indexOf(p.category) >= 0; });
    }
    var label = q.get("label");
    if (label === "none") list = list.filter(function (p) { return !p.status; });
    else if (label) list = list.filter(function (p) { return p.status === Number(label); });
    if (q.get("stock") === "in_stock") list = list.filter(function (p) { return totalStock(p) > 0; });
    if (q.get("stock") === "out_of_stock") list = list.filter(function (p) { return totalStock(p) === 0; });
    list.sort(function (a, b) { return a.created_at < b.created_at ? 1 : a.created_at > b.created_at ? -1 : b.id - a.id; });
    return ok(paginate(list.map(function (p) { return productRow(db, p); }), q.get("page"), A + "/catalog/products/", q));
  });
  route("GET", "/catalog/products/(\\d+)/", function (db, m) {
    var p = byId(db.products, m[1]);
    return p ? ok(productDetail(db, p)) : fail(404, { detail: "Не найдено." });
  });
  route("POST", "/catalog/products/", function (db, m, q, body) {
    var errors = validateProduct(db, body, null);
    if (errors) return fields(errors);
    var id = next(db, "product");
    var p = {
      id: id, name: String(body.name).trim(), slug: body.slug || uniqueSlug(db.products, body.name), category: Number(body.category),
      price_kopecks: body.price_kopecks === undefined ? null : body.price_kopecks,
      compare_at_kopecks: body.compare_at_kopecks || null, status: body.status || null,
      is_active: body.is_active !== false, deleted_at: null, description: String(body.description || ""),
      created_at: now(), updated_at: now(), variants: [], images: []
    };
    var sizes = Array.isArray(body.variants) && body.variants.length ? body.variants : [{ size: "" }];
    var seen = {};
    sizes.forEach(function (v, i) {
      var size = String(v.size || "").trim();
      if (seen[size]) return;
      seen[size] = true;
      p.variants.push(newVariant(db, p, v, i));
    });
    if (p.variants.length > 1) p.variants = p.variants.filter(function (v) { return v.size !== ""; });
    db.products.push(p);
    return { status: 201, body: productDetail(db, p), save: true };
  });
  route("PATCH", "/catalog/products/(\\d+)/", function (db, m, q, body) {
    var p = byId(db.products, m[1]);
    if (!p) return fail(404, { detail: "Не найдено." });
    var errors = validateProduct(db, body, p);
    if (errors) return fields(errors);
    ["name", "description", "price_kopecks", "compare_at_kopecks", "status", "is_active", "slug"].forEach(function (k) {
      if (body[k] !== undefined) p[k] = k === "name" ? String(body[k]).trim() : body[k];
    });
    if (body.category !== undefined) p.category = Number(body.category);
    if (p.price_kopecks === null) p.compare_at_kopecks = null;
    p.updated_at = now();
    return { status: 200, body: productDetail(db, p), save: true };
  });
  route("DELETE", "/catalog/products/(\\d+)/", function (db, m) {
    var p = byId(db.products, m[1]);
    if (!p) return fail(404, { detail: "Не найдено." });
    p.deleted_at = now();
    return { status: 204, body: null, save: true };
  });
  route("POST", "/catalog/products/(\\d+)/restore/", function (db, m) {
    var p = byId(db.products, m[1]);
    if (!p) return fail(404, { detail: "Не найдено." });
    p.deleted_at = null;
    return { status: 200, body: productDetail(db, p), save: true };
  });
  route("POST", "/catalog/products/bulk/", function (db, m, q, body) {
    var ids = (body.ids || []).map(Number);
    if (!ids.length) return fields({ ids: ["Выберите товары."] });
    if (body.category !== undefined && body.category !== null) {
      var c = category(db, body.category);
      if (!c) return fields({ category: ["Нет такой категории."] });
    }
    var updated = 0;
    db.products.forEach(function (p) {
      if (ids.indexOf(p.id) < 0) return;
      if (body.status !== undefined) p.status = body.status || null;
      if (body.category !== undefined && body.category !== null) p.category = Number(body.category);
      if (body.is_active !== undefined) p.is_active = !!body.is_active;
      p.updated_at = now();
      updated++;
    });
    return { status: 200, body: { updated: updated }, save: true };
  });
  route("POST", "/catalog/products/(\\d+)/variants/", function (db, m, q, body) {
    var p = byId(db.products, m[1]);
    if (!p) return fail(404, { detail: "Не найдено." });
    var size = String(body.size || "").trim();
    var error = checkVariant(p, size, null);
    if (error) return fields({ size: [error] });
    if (body.sku && db.products.some(function (x) { return x.variants.some(function (v) { return v.sku === body.sku; }); })) return fields({ sku: ["Такой артикул уже есть."] });
    var v = newVariant(db, p, body, p.variants.length);
    p.variants.push(v);
    p.updated_at = now();
    return { status: 201, body: clone(v), save: true };
  });
  route("PATCH", "/catalog/variants/(\\d+)/", function (db, m, q, body) {
    var found = findVariant(db, m[1]);
    if (!found) return fail(404, { detail: "Не найдено." });
    var v = found.variant;
    if (body.size !== undefined) {
      var size = String(body.size).trim();
      var error = checkVariant(found.product, size, v.id);
      if (error) return fields({ size: [error] });
      v.size = size;
    }
    if (body.stock !== undefined) {
      var stock = parseInt(body.stock, 10);
      if (!(stock >= 0)) return fields({ stock: ["Остаток — целое число от нуля."] });
      v.stock = stock;
    }
    if (body.sku !== undefined) v.sku = String(body.sku).trim() || v.sku;
    if (body.position !== undefined) v.position = body.position;
    found.product.updated_at = now();
    return { status: 200, body: clone(v), save: true };
  });
  route("DELETE", "/catalog/variants/(\\d+)/", function (db, m) {
    var found = findVariant(db, m[1]);
    if (!found) return fail(404, { detail: "Не найдено." });
    if (found.product.variants.length <= 1) return bad("Последний вариант удалить нельзя.");
    found.product.variants.splice(found.product.variants.indexOf(found.variant), 1);
    return { status: 204, body: null, save: true };
  });
  route("POST", "/catalog/products/(\\d+)/images/reorder/", function (db, m, q, body) {
    var p = byId(db.products, m[1]);
    if (!p) return fail(404, { detail: "Не найдено." });
    (body.ids || []).forEach(function (id, index) { var img = byId(p.images, id); if (img) img.position = index; });
    return { status: 200, body: productDetail(db, p).images, save: true };
  });
  route("DELETE", "/catalog/images/(\\d+)/", function (db, m) {
    var id = Number(m[1]);
    for (var i = 0; i < db.products.length; i++) {
      var img = byId(db.products[i].images, id);
      if (img) {
        db.products[i].images.splice(db.products[i].images.indexOf(img), 1);
        return { status: 204, body: null, save: true };
      }
    }
    return fail(404, { detail: "Не найдено." });
  });

  // Статьи
  route("GET", "/content/articles/", function (db, m, q) {
    var list = db.articles.slice();
    var st = q.get("status");
    if (st === "deleted") list = list.filter(function (a) { return a.deleted_at; });
    else {
      list = list.filter(function (a) { return !a.deleted_at; });
      if (st === "published") list = list.filter(function (a) { return a.is_published; });
      if (st === "draft") list = list.filter(function (a) { return !a.is_published; });
    }
    var s = lower(q.get("search"));
    if (s) list = list.filter(function (a) { return lower(a.title).indexOf(s) >= 0; });
    list.sort(function (a, b) { return a.created_at < b.created_at ? 1 : -1; });
    return ok(paginate(list.map(articleRow), q.get("page"), A + "/content/articles/", q));
  });
  route("GET", "/content/articles/(\\d+)/", function (db, m) {
    var a = byId(db.articles, m[1]);
    return a ? ok(articleDetail(a)) : fail(404, { detail: "Не найдено." });
  });
  function validateArticle(body, current) {
    var errors = {};
    var title = body.title !== undefined ? String(body.title).trim() : current ? current.title : "";
    if (!title) errors.title = ["Обязательное поле."];
    if (body.excerpt && String(body.excerpt).length > 300) errors.excerpt = ["Не больше 300 символов."];
    return Object.keys(errors).length ? errors : null;
  }
  route("POST", "/content/articles/", function (db, m, q, body) {
    var errors = validateArticle(body, null);
    if (errors) return fields(errors);
    var a = {
      id: next(db, "article"), slug: uniqueSlug(db.articles, body.title), title: String(body.title).trim(),
      excerpt: String(body.excerpt || ""), body: String(body.body || ""), is_published: !!body.is_published,
      published_at: body.is_published ? now() : null, created_at: now(), updated_at: now(), deleted_at: null, images: []
    };
    db.articles.push(a);
    return { status: 201, body: articleDetail(a), save: true };
  });
  route("PATCH", "/content/articles/(\\d+)/", function (db, m, q, body) {
    var a = byId(db.articles, m[1]);
    if (!a) return fail(404, { detail: "Не найдено." });
    var errors = validateArticle(body, a);
    if (errors) return fields(errors);
    ["title", "excerpt", "body", "is_published"].forEach(function (k) { if (body[k] !== undefined) a[k] = body[k]; });
    if (a.is_published && !a.published_at) a.published_at = now();
    a.updated_at = now();
    return { status: 200, body: articleDetail(a), save: true };
  });
  route("DELETE", "/content/articles/(\\d+)/", function (db, m) {
    var a = byId(db.articles, m[1]);
    if (!a) return fail(404, { detail: "Не найдено." });
    a.deleted_at = now();
    return { status: 204, body: null, save: true };
  });
  route("POST", "/content/articles/(\\d+)/restore/", function (db, m) {
    var a = byId(db.articles, m[1]);
    if (!a) return fail(404, { detail: "Не найдено." });
    a.deleted_at = null;
    return { status: 200, body: articleDetail(a), save: true };
  });
  route("POST", "/content/articles/(\\d+)/images/reorder/", function (db, m, q, body) {
    var a = byId(db.articles, m[1]);
    if (!a) return fail(404, { detail: "Не найдено." });
    (body.ids || []).forEach(function (id, index) { var img = byId(a.images, id); if (img) img.position = index; });
    return { status: 200, body: articleDetail(a).images, save: true };
  });
  route("DELETE", "/content/article-images/(\\d+)/", function (db, m) {
    var id = Number(m[1]);
    for (var i = 0; i < db.articles.length; i++) {
      var img = byId(db.articles[i].images, id);
      if (img) {
        db.articles[i].images.splice(db.articles[i].images.indexOf(img), 1);
        return { status: 204, body: null, save: true };
      }
    }
    return fail(404, { detail: "Не найдено." });
  });

  // Главная
  route("GET", "/content/home/", function (db) { return ok(homeState(db)); });
  route("POST", "/content/home/blocks/", function (db, m, q, body) {
    var titles = { banner: "Новый баннер", collection: "Подборка", categories: "Категории", text: "Новый текст" };
    if (!titles[body.kind]) return fields({ kind: ["Неизвестный тип блока."] });
    if (db.home.blocks.length >= 20) return bad("Не больше 20 блоков на главной.");
    var b = {
      id: next(db, "block"), kind: body.kind, position: db.home.blocks.length, is_visible: true, title: titles[body.kind],
      text: body.kind === "banner" ? "Короткое описание" : body.kind === "text" ? "Первый абзац.\n\nВторой абзац." : "",
      color: body.kind === "banner" ? "#DDF38A" : "", ink: "#13261C", images: [], product: null, category: null,
      source: "new", product_ids: [], links: []
    };
    db.home.blocks.push(b);
    touchHome(db);
    return { status: 201, body: homeBlock(db, b), save: true };
  });
  route("PATCH", "/content/home/blocks/(\\d+)/", function (db, m, q, body) {
    var b = byId(db.home.blocks, m[1]);
    if (!b) return fail(404, { detail: "Не найдено." });
    var errors = {};
    if (body.title !== undefined && String(body.title).length > 60) errors.title = ["Не больше 60 символов."];
    if (body.text !== undefined && b.kind === "banner" && String(body.text).length > 120) errors.text = ["Не больше 120 символов."];
    if (body.color !== undefined && body.color && !/^#[0-9a-fA-F]{6}$/.test(body.color)) errors.color = ["Цвет — в формате #RRGGBB."];
    if (body.product_ids !== undefined && body.product_ids.length > 12) errors.product_ids = ["Не больше 12 товаров."];
    if (body.image_ids !== undefined) {
      var own = bannerImages(b);
      var ownIds = own.map(function (x) { return x.id; });
      var bad = body.image_ids.some(function (id, i) { return ownIds.indexOf(id) < 0 || body.image_ids.indexOf(id) !== i; });
      if (bad) errors.image_ids = ["Картинки — только из загруженных к баннеру."];
      else b.images = body.image_ids.map(function (id) { return own[ownIds.indexOf(id)]; });
    }
    if (body.product !== undefined && body.product !== null && !byId(db.products, body.product)) errors.product = ["Товар не найден."];
    if (body.links !== undefined) {
      if (body.links.length > 12) errors.links = ["В ленте — не больше 12 вкладок."];
      body.links.forEach(function (l) {
        if (l.kind === "url" && (!/^(\/(?!\/)|https?:\/\/)\S+$/.test(l.url || "") || !String(l.title || "").trim())) errors.links = ["Адрес — путь на сайте (/…) или https://…, и подпись."];
        if ((l.kind === "category" || l.kind === "article") && !l.id) errors.links = ["Выберите категорию или статью."];
      });
    }
    if (Object.keys(errors).length) return fields(errors);
    ["is_visible", "title", "text", "color", "category", "source", "product_ids", "product", "links"].forEach(function (k) { if (body[k] !== undefined) b[k] = body[k]; });
    if (b.kind === "banner" && !b.title && !b.text && !bannerImages(b).length && !b.product) return fields({ title: ["У баннера нужен заголовок, описание, картинка или товар."] });
    if (b.color) b.color = b.color.toUpperCase();
    touchHome(db);
    return { status: 200, body: homeBlock(db, b), save: true };
  });
  route("DELETE", "/content/home/blocks/(\\d+)/", function (db, m) {
    var b = byId(db.home.blocks, m[1]);
    if (!b) return fail(404, { detail: "Не найдено." });
    db.home.blocks.splice(db.home.blocks.indexOf(b), 1);
    db.home.blocks.sort(function (x, y) { return x.position - y.position; }).forEach(function (x, i) { x.position = i; });
    touchHome(db);
    return { status: 204, body: null, save: true };
  });
  route("DELETE", "/content/home/blocks/(\\d+)/image/", function (db, m) {
    var b = byId(db.home.blocks, m[1]);
    if (!b) return fail(404, { detail: "Не найдено." });
    b.image_url = null;
    b.images = [];
    touchHome(db);
    return { status: 200, body: homeBlock(db, b), save: true };
  });
  route("POST", "/content/home/reorder/", function (db, m, q, body) {
    (body.ids || []).forEach(function (id, index) { var b = byId(db.home.blocks, id); if (b) b.position = index; });
    touchHome(db);
    return { status: 200, body: homeState(db), save: true };
  });
  route("POST", "/content/home/publish/", function (db) {
    db.home.published = clone(db.home.blocks);
    db.home.has_changes = false;
    db.home.published_at = now();
    return { status: 200, body: homeState(db), save: true };
  });

  // Тема
  route("GET", "/content/theme/", function (db) { return ok(themeState(db)); });
  route("PUT", "/content/theme/", function (db, m, q, body) {
    var keys = db.theme.palettes.map(function (p) { return p.key; });
    var palettes = (body.palettes || []).filter(function (k) { return keys.indexOf(k) >= 0; });
    if (!palettes.length) return fields({ palettes: ["Оставьте покупателям хотя бы одну палитру."] });
    if (palettes.indexOf(body.default_palette) < 0) return fields({ default_palette: ["Палитра по умолчанию должна быть среди доступных."] });
    db.theme.enabled = keys.filter(function (k) { return palettes.indexOf(k) >= 0; });
    db.theme.default_palette = body.default_palette;
    db.theme.default_mode = body.default_mode || "system";
    db.theme.default_radius = body.default_radius || "normal";
    if (body.nav_style) db.theme.nav_style = body.nav_style;
    if (body.default_text) db.theme.default_text = body.default_text;
    // Как на сервере: личный выбор оформления в этом браузере сбрасывается — магазин сразу
    // показывает то, что задал администратор.
    ["theme", "palette", "accent", "radius", "text_size"].forEach(function (name) {
      document.cookie = name + "=; path=/; max-age=0; samesite=lax";
    });
    return { status: 200, body: themeState(db), save: true };
  });

  // Настройки магазина
  route("GET", "/content/settings/", function (db) { return ok(clone(db.settings)); });
  route("PUT", "/content/settings/", function (db, m, q, body) {
    var errors = {};
    ["delivery_courier_kopecks", "delivery_free_from_kopecks"].forEach(function (k) {
      if (body[k] !== null && body[k] !== undefined && !(body[k] >= 0)) errors[k] = ["Сумма — от нуля."];
    });
    if (body.unpaid_timeout_minutes !== null && body.unpaid_timeout_minutes !== undefined &&
      !(body.unpaid_timeout_minutes >= 10 && body.unpaid_timeout_minutes <= 1440)) errors.unpaid_timeout_minutes = ["От 10 минут до суток."];
    var inn = digits(body.seller_inn);
    if (inn && inn.length !== 10 && inn.length !== 12) errors.seller_inn = ["ИНН — 10 или 12 цифр."];
    var ogrn = digits(body.seller_ogrn);
    if (ogrn && ogrn.length !== 13 && ogrn.length !== 15) errors.seller_ogrn = ["ОГРН — 13 цифр, ОГРНИП — 15."];
    if (body.seller_email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(body.seller_email)) errors.seller_email = ["Введите правильный адрес электронной почты."];
    if (Object.keys(errors).length) return fields(errors);
    Object.keys(body).forEach(function (k) { if (k in db.settings && k !== "defaults") db.settings[k] = body[k]; });
    db.settings.updated_at = now();
    return { status: 200, body: clone(db.settings), save: true };
  });

  // Сотрудники
  route("GET", "/staff/", function (db) { return ok(db.staff.map(staffMember)); });
  route("POST", "/staff/", function (db, m, q, body) {
    var email = lower(body.email);
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return fields({ email: ["Введите правильный адрес электронной почты."] });
    if (db.staff.some(function (s) { return s.email === email; })) return fields({ email: ["Этот сотрудник уже есть."] });
    var perms = clone(body.permissions || {});
    perms.settings = "none";
    perms.staff = "none";
    var member = {
      id: next(db, "staff"), email: email, first_name: String(body.first_name || ""), last_name: "", is_superuser: false,
      is_owner: false, permissions: perms, is_active: true, invited: true, last_login: null, date_joined: now()
    };
    db.staff.push(member);
    return { status: 201, body: staffMember(member), save: true };
  });
  route("PATCH", "/staff/(\\d+)/", function (db, m, q, body) {
    var member = byId(db.staff, m[1]);
    if (!member) return fail(404, { detail: "Не найдено." });
    if (member.is_owner) return bad("Права владельца не меняются.");
    if (body.first_name !== undefined) member.first_name = body.first_name;
    if (body.is_active !== undefined) member.is_active = !!body.is_active;
    if (body.permissions) {
      Object.keys(body.permissions).forEach(function (k) { member.permissions[k] = body.permissions[k]; });
    }
    return { status: 200, body: staffMember(member), save: true };
  });
  route("POST", "/staff/(\\d+)/resend/", function (db, m) {
    return byId(db.staff, m[1]) ? ok(null, 204) : fail(404, { detail: "Не найдено." });
  });

  // Загрузка фото (multipart): товар, статья, баннер главной.
  var uploads = [
    {
      re: new RegExp("^" + A + "/catalog/products/(\\d+)/images/$"),
      apply: function (db, m, url) {
        var p = byId(db.products, m[1]);
        if (!p) return fail(404, { detail: "Не найдено." });
        if (p.images.length >= 10) return fields({ image: ["Не больше 10 фото у товара."] });
        var img = { id: next(db, "image"), url: url, position: p.images.length };
        p.images.push(img);
        return { status: 201, body: clone(img), save: true };
      }
    },
    {
      re: new RegExp("^" + A + "/content/articles/(\\d+)/images/$"),
      apply: function (db, m, url) {
        var a = byId(db.articles, m[1]);
        if (!a) return fail(404, { detail: "Не найдено." });
        if (a.images.length >= 6) return fields({ image: ["Не больше 6 фото у статьи."] });
        var img = { id: next(db, "articleImage"), url: url, position: a.images.length };
        a.images.push(img);
        return { status: 201, body: clone(img), save: true };
      }
    },
    {
      re: new RegExp("^" + A + "/content/home/blocks/(\\d+)/image/$"),
      gif: true,
      apply: function (db, m, url) {
        var b = byId(db.home.blocks, m[1]);
        if (!b) return fail(404, { detail: "Не найдено." });
        if (b.kind !== "banner") return fields({ image: ["Картинка есть только у баннера."] });
        var images = bannerImages(b);
        if (images.length >= 6) return fields({ image: ["У баннера — не больше 6 картинок."] });
        var img = { id: next(db, "homeImage"), url: url };
        b.images = images.concat([img]);
        b.image_ids = b.images.map(function (x) { return x.id; });
        touchHome(db);
        return { status: 200, body: homeBlock(db, b), save: true };
      }
    }
  ];

  function signedIn() {
    try { return localStorage.getItem(ADMIN_SESSION) === "1"; } catch (e) { return false; }
  }
  function setSignedIn(value) {
    try {
      if (value) localStorage.setItem(ADMIN_SESSION, "1");
      else localStorage.removeItem(ADMIN_SESSION);
    } catch (e) { /* без хранилища вход не запомнится */ }
  }

  function commit(db, result) {
    if (result.save && !save(db)) {
      cache = null; // изменение не записалось — перечитать прежнее состояние
      return fail(507, { detail: "Хранилище браузера переполнено — удалите лишние фото или сбросьте демо-данные (Настройки)." });
    }
    return result;
  }

  /** Запрос панели: method, путь (+query), тело (объект или FormData). → Promise<{status, body}> */
  function api(method, url, body) {
    return ready().then(function (db) {
      var parsed = new URL(url, location.href);
      var path = parsed.pathname;
      var q = parsed.searchParams;
      if (path !== A + "/auth/login/" && path !== A + "/auth/csrf/" && path !== A + "/auth/me/" && !signedIn()) {
        return fail(401, { detail: "Нужен вход." });
      }
      if (method === "POST" && body instanceof FormData) {
        for (var u = 0; u < uploads.length; u++) {
          var um = path.match(uploads[u].re);
          if (!um) continue;
          var file = body.get("image");
          var upload = uploads[u];
          return readImage(file, upload.gif).then(function (dataUrl) {
            var fresh = load();
            return commit(fresh, upload.apply(fresh, um, dataUrl));
          }, function (error) {
            if (error && error.message === "size") return fields({ image: ["GIF в демо — до 1,5 МБ."] });
            return fields({ image: [upload.gif ? "Загрузите JPEG, PNG, WebP или GIF." : "Загрузите JPEG, PNG или WebP."] });
          });
        }
      }
      for (var i = 0; i < routes.length; i++) {
        var r = routes[i];
        if (r.method !== method) continue;
        var m = path.match(r.re);
        if (!m) continue;
        return commit(db, r.handler(db, m, q, body || {}));
      }
      return fail(404, { detail: "В демо-режиме этого действия нет." });
    });
  }

  // --- Витрина: покупатель ---

  function session(db) { return db.session; }
  function customerByEmail(db, email) {
    email = lower(email);
    return db.customers.filter(function (c) { return c.email === email; })[0] || null;
  }
  function cartKey(db) { return db.session ? "u:" + db.session.email : "guest"; }
  function cartLines(db) { return db.carts[cartKey(db)] || []; }
  function setCart(db, lines) { db.carts[cartKey(db)] = lines; }

  function mergeCart(db, from, to) {
    var source = db.carts[from] || [];
    var target = db.carts[to] || [];
    source.forEach(function (line) {
      var found = findVariant(db, line[0]);
      var max = maxQuantity(db, found);
      if (!max) return;
      var existing = target.filter(function (t) { return t[0] === line[0]; })[0];
      if (existing) existing[1] = Math.min(max, existing[1] + line[1]);
      else if (target.length < CART_MAX_ITEMS) target.push([line[0], Math.min(max, line[1])]);
    });
    db.carts[to] = target;
    delete db.carts[from];
  }

  /** Корзина как на сервере (store.services.cart.get_summary): статусы позиций, итог. */
  function cartSummary(db, lines) {
    var items = (lines || cartLines(db)).map(function (line) {
      var found = findVariant(db, line[0]);
      var p = found && found.product;
      var live = isLive(db, p) && p.price_kopecks !== null;
      var max = maxQuantity(db, found);
      var st = !found || !live ? "unavailable" : found.variant.stock <= 0 ? "out_of_stock" : line[1] > max ? "exceeds_stock" : "ok";
      var unit = p ? p.price_kopecks : null;
      return {
        variant_id: line[0], quantity: line[1], product: p ? publicProduct(db, p) : null, size: found ? found.variant.size : "",
        sku: found ? found.variant.sku : "", status: st, max_quantity: max, unit_price_kopecks: unit,
        line_total_kopecks: st === "ok" ? unit * line[1] : 0
      };
    });
    var ok_ = items.filter(function (i) { return i.status === "ok"; });
    return {
      lines: items,
      items_count: ok_.reduce(function (n, i) { return n + i.quantity; }, 0),
      total_kopecks: ok_.reduce(function (n, i) { return n + i.line_total_kopecks; }, 0),
      can_checkout: items.length > 0 && ok_.length === items.length
    };
  }

  function cartAdd(variantId, quantity) {
    var db = load();
    var found = findVariant(db, variantId);
    var max = maxQuantity(db, found);
    if (!max) return { error: "Товара нет в наличии." };
    var lines = cartLines(db).slice();
    var existing = lines.filter(function (l) { return l[0] === Number(variantId); })[0];
    var want = (existing ? existing[1] : 0) + (quantity || 1);
    if (want > max) return { error: "Больше добавить нельзя: доступно " + max + " шт." };
    if (!existing && lines.length >= CART_MAX_ITEMS) return { error: "В корзине уже " + CART_MAX_ITEMS + " позиций." };
    if (existing) existing[1] = want; else lines.push([Number(variantId), quantity || 1]);
    setCart(db, lines);
    save(db);
    return { ok: true, quantity: want };
  }
  function cartSet(variantId, quantity) {
    var db = load();
    var lines = cartLines(db).filter(function (l) { return quantity > 0 || l[0] !== Number(variantId); });
    lines.forEach(function (l) {
      if (l[0] === Number(variantId)) l[1] = Math.max(1, Math.min(maxQuantity(db, findVariant(db, variantId)) || 1, quantity));
    });
    setCart(db, lines);
    save(db);
  }
  function cartCount() {
    var db = load();
    return db ? cartLines(db).reduce(function (n, l) { return n + l[1]; }, 0) : 0;
  }

  function login(email, password) {
    var db = load();
    email = lower(email);
    if (db.login && email === db.login.email) {
      if (password !== db.login.password) return { error: "Неверный email или пароль." };
      setSignedIn(true);
      return { admin: true };
    }
    var c = customerByEmail(db, email);
    if (!c || c.status === "deleted") return { error: "Неверный email или пароль." };
    if (c.password && c.password !== password) return { error: "Неверный email или пароль." };
    if (!c.password && !password) return { error: "Введите пароль." };
    if (c.status === "blocked") return { error: "Аккаунт заблокирован. Напишите в поддержку магазина." };
    c.last_login = now();
    db.session = { id: c.id, email: c.email };
    db.loggedOut = false;
    mergeCart(db, "guest", cartKey(db));
    save(db);
    return { ok: true };
  }
  function register(email, password, firstName) {
    var db = load();
    email = lower(email);
    var errors = {};
    if (!/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) errors.email = "Введите правильный адрес электронной почты.";
    else if (customerByEmail(db, email) || (db.login && db.login.email === email)) errors.email = "Пользователь с таким email уже есть.";
    if (String(password || "").length < 8) errors.password = "Пароль — не короче 8 символов.";
    if (Object.keys(errors).length) return { errors: errors };
    var c = {
      id: next(db, "customer"), email: email, first_name: String(firstName || "").trim(), last_name: "", status: "active",
      date_joined: now(), last_login: now(), deleted_at: null, password: password
    };
    db.customers.push(c);
    db.session = { id: c.id, email: c.email };
    db.loggedOut = false;
    mergeCart(db, "guest", cartKey(db));
    save(db);
    return { ok: true };
  }
  function logout() {
    var db = load();
    db.session = null;
    db.loggedOut = true;
    save(db);
  }
  /** Покупатель на страницах /me/: вошедший, иначе демо-покупатель (Анна). */
  function ensureCustomer() {
    var db = load();
    if (db.session && customerByEmail(db, db.session.email)) return db.session;
    if (db.loggedOut) return null; // вышел сам — страницы /me/ ведут на вход
    var anna = customerByEmail(db, "anna@example.ru") || db.customers.filter(function (c) { return c.status === "active"; })[0];
    if (!anna) return null;
    db.session = { id: anna.id, email: anna.email };
    mergeCart(db, "guest", cartKey(db));
    save(db);
    return db.session;
  }
  function currentCustomer() {
    var db = load();
    return db && db.session ? customerByEmail(db, db.session.email) : null;
  }
  function updateCustomer(changes) {
    var db = load();
    var c = currentCustomer();
    if (!c) return;
    c = customerByEmail(db, c.email);
    if (changes.first_name !== undefined) c.first_name = String(changes.first_name).trim();
    if (changes.last_name !== undefined) c.last_name = String(changes.last_name).trim();
    if (changes.password) c.password = changes.password;
    save(db);
  }
  function deleteAccount() {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    if (!c) return { error: "Нужно войти." };
    if (db.orders.some(function (o) { return o.customer.id === c.id && UNFINISHED.indexOf(o.status) >= 0; })) {
      return { error: "Есть незавершённые заказы — удалить аккаунт можно после их получения или отмены." };
    }
    c.status = "deleted";
    c.deleted_at = now();
    c.email = "deleted-" + c.id + "@deleted.invalid";
    c.first_name = "";
    db.session = null;
    db.loggedOut = true;
    save(db);
    return { ok: true };
  }

  // Фото профиля (accounts.services.set_avatar): квадрат 320 по центру, как на сервере.
  function readAvatar(file) {
    return new Promise(function (resolve, reject) {
      if (!file || !/^image\/(jpeg|png|webp)$/.test(file.type || "")) return reject(new Error("type"));
      if (file.size > 5 * 1024 * 1024) return reject(new Error("size"));
      var url = URL.createObjectURL(file);
      var img = new Image();
      img.onload = function () {
        var side = Math.min(img.naturalWidth, img.naturalHeight);
        var canvas = document.createElement("canvas");
        canvas.width = canvas.height = 320;
        canvas.getContext("2d").drawImage(img, (img.naturalWidth - side) / 2, (img.naturalHeight - side) / 2, side, side, 0, 0, 320, 320);
        URL.revokeObjectURL(url);
        resolve(canvas.toDataURL("image/jpeg", 0.85));
      };
      img.onerror = function () { URL.revokeObjectURL(url); reject(new Error("decode")); };
      img.src = url;
    });
  }
  function setAvatar(file) {
    return readAvatar(file).then(function (dataUrl) {
      var db = load();
      var c = db.session && customerByEmail(db, db.session.email);
      if (!c) return false;
      c.avatar = dataUrl;
      return save(db);
    });
  }
  function removeAvatar() {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    if (c) { delete c.avatar; save(db); }
  }

  // Журнал просмотров (store.services.history): последние 30 товаров, свежие — первыми.
  function recordView(slug) {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    var p = db.products.filter(function (x) { return x.slug === slug; })[0];
    if (!c || !p) return;
    c.viewed = [p.id].concat((c.viewed || []).filter(function (id) { return id !== p.id; })).slice(0, 30);
    save(db);
  }
  function viewed(limit) {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    if (!c) return [];
    return (c.viewed || []).map(function (id) { return byId(db.products, id); })
      .filter(function (p) { return p && isLive(db, p); })
      .slice(0, limit || 12)
      .map(function (p) { return publicProduct(db, p); });
  }
  function clearViewed() {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    if (c) { c.viewed = []; save(db); }
  }

  // «Похожие» (store.services.storefront.similar_products): та же категория, затем соседние
  // подкатегории того же корня; в наличии — первыми, затем новые.
  function similar(slug, limit) {
    var db = load();
    var p = db.products.filter(function (x) { return x.slug === slug; })[0];
    var cat = p && category(db, p.category);
    if (!cat) return [];
    var root = cat.parent || cat.id;
    var list = liveProducts(db).filter(function (x) {
      if (x.id === p.id) return false;
      var c = category(db, x.category);
      return c && (c.id === root || c.parent === root);
    });
    var rank = function (x) { return (x.category === cat.id ? 0 : 2) + (totalStock(x) > 0 ? 0 : 1); };
    return list.map(function (x, i) { return { x: x, i: i }; })
      .sort(function (a, b) { return rank(a.x) - rank(b.x) || a.i - b.i; })
      .slice(0, limit || 12)
      .map(function (e) { return publicProduct(db, e.x); });
  }

  function myOrders() {
    var db = load();
    if (!db.session) return [];
    return db.orders.filter(function (o) { return o.customer.id === db.session.id; })
      .sort(function (a, b) { return a.created_at < b.created_at ? 1 : -1; });
  }
  function myOrder(number) {
    return myOrders().filter(function (o) { return o.number === number; })[0] || null;
  }

  /** Оформление (orders.services.checkout): проверки формы, списание остатков, заказ. */
  function checkout(form, buyNow) {
    var db = load();
    var c = db.session && customerByEmail(db, db.session.email);
    if (!c) return { error: "Войдите, чтобы оформить заказ." };
    var lines = buyNow ? [[Number(buyNow.variant), Number(buyNow.quantity) || 1]] : cartLines(db);
    var cart = cartSummary(db, lines);
    if (!cart.lines.length) return { error: "Корзина пуста." };
    if (!cart.can_checkout) return { error: "Некоторые товары закончились или изменились — проверьте корзину." };
    var s = effectiveSettings(db);
    var options = deliveryOptions(db, cart.total_kopecks);
    var errors = {};
    var name = String(form.recipient_name || "").trim();
    if (!name) errors.recipient_name = "Укажите получателя.";
    var phone = digits(form.recipient_phone);
    if (phone.length === 10) phone = "7" + phone;
    if (phone.length === 11 && phone[0] === "8") phone = "7" + phone.slice(1);
    if (!(phone.length === 11 && phone[0] === "7")) errors.recipient_phone = "Телефон — российский номер, например +7 900 123-45-67.";
    var delivery = options.filter(function (o) { return o.method === form.delivery_method; })[0];
    if (!delivery) errors.delivery_method = "Выберите способ получения.";
    var address = String(form.delivery_address || "").trim();
    if (delivery && delivery.method === "courier" && !address) errors.delivery_address = "Укажите адрес доставки.";
    var payment = form.payment_method;
    if (payment !== "online" && payment !== "on_delivery") errors.payment_method = "Выберите способ оплаты.";
    else if (payment === "online" && !s.online) errors.payment_method = "Онлайн-оплата сейчас недоступна.";
    else if (payment === "on_delivery" && !s.cash) errors.payment_method = "Оплата при получении сейчас недоступна.";
    if (Object.keys(errors).length) return { errors: errors };

    var created = now();
    var order = {
      id: next(db, "order"), customer: { id: c.id, email: c.email, is_deleted: false }, number: "DD-" + next(db, "number"),
      status: payment === "online" ? "awaiting_payment" : "confirmed", payment_method: payment,
      payment_method_display: PAYMENT_LABELS[payment], delivery_method: delivery.method,
      delivery_method_display: DELIVERY_LABELS[delivery.method], items_total_kopecks: cart.total_kopecks,
      delivery_kopecks: delivery.cost_kopecks, total_kopecks: cart.total_kopecks + delivery.cost_kopecks,
      recipient_name: name, recipient_phone: "+" + phone,
      delivery_address: delivery.method === "pickup" ? delivery.address : address,
      comment: String(form.comment || "").trim(), created_at: created, updated_at: created, items: [], status_history: [],
      pay_until: payment === "online" ? new Date(Date.now() + s.timeout * 60000).toISOString() : null,
      payments: [], can_retry_refund: false
    };
    order.status_display = STATUS_LABELS[order.status];
    cart.lines.forEach(function (line) {
      var found = findVariant(db, line.variant_id);
      found.variant.stock -= line.quantity;
      var st = status(db, found.product.status);
      order.items.push({
        id: next(db, "item"), product_slug: found.product.slug, product_name: found.product.name, size: found.variant.size,
        sku: found.variant.sku, status_name: st ? st.name : "", price_kopecks: line.unit_price_kopecks, quantity: line.quantity,
        line_total_kopecks: line.line_total_kopecks, cover_url: coverUrl(found.product), product_id: found.product.id,
        variant_id: found.variant.id
      });
    });
    order.status_history.push({
      from_status: "", to_status: order.status, to_status_display: STATUS_LABELS[order.status], changed_by: "customer",
      comment: "", created_at: created, actor_email: c.email, notified: true
    });
    if (payment === "online") {
      order.payments.push({
        id: next(db, "payment"), amount_kopecks: order.total_kopecks, status: "pending", status_display: "Ожидает оплаты",
        provider_payment_id: "pay-sim-" + db.seq.payment, cancellation_reason: "", created_at: created, paid_at: null, refunds: []
      });
    }
    db.orders.push(order);
    if (!buyNow) setCart(db, []);
    if (!save(db)) return { error: "Хранилище браузера переполнено — сбросьте демо-данные." };
    return { order: order };
  }

  function payOrder(number) {
    var db = load();
    var o = db.orders.filter(function (x) { return x.number === number; })[0];
    if (!o || o.status !== "awaiting_payment") return null;
    var p = o.payments.filter(function (x) { return x.status === "pending"; })[0];
    if (!p) {
      p = { id: next(db, "payment"), amount_kopecks: o.total_kopecks, status: "pending", status_display: "Ожидает оплаты",
        provider_payment_id: "pay-sim-" + db.seq.payment, cancellation_reason: "", created_at: now(), paid_at: null, refunds: [] };
      o.payments.push(p);
    }
    p.status = "succeeded";
    p.status_display = "Оплачен";
    p.paid_at = now();
    o.pay_until = null;
    setStatus(db, o, "paid", "system", null, "", true);
    save(db);
    return o;
  }
  function cancelOrder(number) {
    var db = load();
    var o = db.orders.filter(function (x) { return x.number === number; })[0];
    if (!o || CUSTOMER_CANCEL.indexOf(o.status) < 0) return null;
    setStatus(db, o, "cancelled", "customer", o.customer.email, "", true);
    save(db);
    return o;
  }
  function canCancel(o) { return CUSTOMER_CANCEL.indexOf(o.status) >= 0; }
  function lastRecipient() {
    var o = myOrders()[0];
    return o ? { name: o.recipient_name, phone: o.recipient_phone, address: o.delivery_method === "courier" ? o.delivery_address : "" } : null;
  }

  function publishedHome() {
    var db = load();
    return db.home.published.filter(function (b) { return b.is_visible; })
      .sort(function (a, b) { return a.position - b.position; })
      .map(function (b) { return homeBlock(db, b); });
  }

  window.DidiSim = {
    BASE: BASE,
    ready: ready,
    reset: reset,
    api: api,
    db: load,
    inkFor: inkFor,
    statusLabel: function (s) { return STATUS_LABELS[s] || s; },
    deliveryLabel: function (d) { return DELIVERY_LABELS[d] || d; },
    paymentLabel: function (p) { return PAYMENT_LABELS[p] || p; },
    // каталог
    isLive: function (p) { return isLive(load(), p); },
    liveProducts: function () { var db = load(); return liveProducts(db).map(function (p) { return publicProduct(db, p); }); },
    product: function (slug) { var db = load(); return db.products.filter(function (p) { return p.slug === slug; })[0] || null; },
    productById: function (id) { return byId(load().products, id); },
    publicProduct: function (p) { return publicProduct(load(), p); },
    category: function (id) { return byId(load().categories, id); },
    categoryBySlug: function (slug) { return load().categories.filter(function (c) { return c.slug === slug; })[0] || null; },
    categories: function () {
      var db = load();
      return db.categories.filter(function (c) { return categoryActive(db, c.id); }).sort(function (a, b) { return a.position - b.position || a.id - b.id; });
    },
    descendants: function (id) { return descendants(load(), id); },
    status: function (id) { return status(load(), id); },
    maxQuantity: function (variantId) { var db = load(); return maxQuantity(db, findVariant(db, variantId)); },
    imageSources: function (url) { var db = load(); return (db.imageSources || {})[url] || null; },
    articles: function () {
      return load().articles.filter(function (a) { return a.is_published && !a.deleted_at; })
        .sort(function (a, b) { return a.published_at < b.published_at ? 1 : -1; });
    },
    article: function (slug) { return load().articles.filter(function (a) { return a.slug === slug; })[0] || null; },
    publishedHome: publishedHome,
    settings: function () { return effectiveSettings(load()); },
    deliveryOptions: function (itemsTotal) { return deliveryOptions(load(), itemsTotal); },
    // корзина и покупатель
    cart: function (lines) { return cartSummary(load(), lines); },
    cartAdd: cartAdd,
    cartSet: cartSet,
    cartCount: cartCount,
    login: login,
    register: register,
    logout: logout,
    ensureCustomer: ensureCustomer,
    currentCustomer: currentCustomer,
    updateCustomer: updateCustomer,
    deleteAccount: deleteAccount,
    myOrders: myOrders,
    myOrder: myOrder,
    checkout: checkout,
    payOrder: payOrder,
    cancelOrder: cancelOrder,
    canCancel: canCancel,
    lastRecipient: lastRecipient,
    setAvatar: setAvatar,
    removeAvatar: removeAvatar,
    recordView: recordView,
    viewed: viewed,
    clearViewed: clearViewed,
    similar: similar,
    adminSignedIn: signedIn
  };
})();
