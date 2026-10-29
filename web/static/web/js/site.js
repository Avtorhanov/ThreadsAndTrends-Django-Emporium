/* Витрина DiDi-shop: поведение шапки, тема, мелкие улучшения форм.
   Всё работает и без этого файла (обычные ссылки и формы) — скрипт только добавляет плавность. */
(function () {
  "use strict";

  var root = document.documentElement;
  var reduced = window.matchMedia("(prefers-reduced-motion: reduce)");
  var YEAR = 60 * 60 * 24 * 365;

  function setCookie(name, value, maxAge) {
    var secure = location.protocol === "https:" ? "; secure" : "";
    document.cookie = name + "=" + value + "; path=/; max-age=" + maxAge + "; samesite=lax" + secure;
  }

  // iOS Safari включает :active (эффект нажатия) только при наличии обработчика касаний.
  document.addEventListener("touchstart", function () {}, { passive: true });

  // Перелёт фото: имя product-photo — только у фото нажатой карточки (имена в переходе уникальны).
  document.addEventListener("click", function (event) {
    var card = event.target.closest && event.target.closest("a.card");
    if (!card) return;
    document.querySelectorAll(".card__img").forEach(function (img) { img.style.viewTransitionName = ""; });
    var img = card.querySelector(".card__img");
    if (img) img.style.viewTransitionName = "product-photo";
  });

  // Переход на другую часть сайта (панель, резервная админка) — без анимации: у них свой каркас,
  // и браузер иначе прерывает переход с ошибкой в консоли.
  window.addEventListener("pageswap", function (event) {
    if (!event.viewTransition) return;
    var entry = event.activation && event.activation.entry;
    var path = entry && entry.url ? new URL(entry.url).pathname : "";
    if (/\/(panel|admin)\//.test(path)) event.viewTransition.skipTransition();
  });

  // --- Быстрые переходы: страница начинает грузиться при наведении или касании ссылки ---
  // (браузер кладёт ответ в кэш предзагрузки; к моменту отпускания пальца она уже в пути).
  var prefetched = {};
  var saveData = navigator.connection && navigator.connection.saveData;
  function prefetch(event) {
    var link = event.target.closest && event.target.closest("a[href]");
    if (!link || saveData || link.target || link.hasAttribute("download")) return;
    var url = new URL(link.href, location.href);
    if (url.origin !== location.origin || url.hash || url.href === location.href) return;
    // Панель и резервная админка — другие приложения; API и выход не предзагружаются.
    if (/^\/(panel|admin|api|media)\//.test(url.pathname) || /\/logout\//.test(url.pathname)) return;
    if (prefetched[url.href]) return;
    prefetched[url.href] = true;
    var hint = document.createElement("link");
    hint.rel = "prefetch";
    hint.href = url.href;
    document.head.appendChild(hint);
  }
  document.addEventListener("pointerover", prefetch, { passive: true });
  document.addEventListener("touchstart", prefetch, { passive: true });

  // --- Корзина: «+/−» без ожидания сервера ---
  // Число и сумма позиции меняются сразу; на сервер уходит один запрос с итоговым количеством
  // через 300 мс после последнего нажатия. Ответ обновляет только эту позицию, итог и счётчики
  // (hx-swap-oob) — остальная корзина не перерисовывается. Без JS — обычные формы.
  function formatRub(kopecks) {
    var rubles = String(Math.floor(kopecks / 100)).replace(/\B(?=(\d{3})+(?!\d))/g, "\u00a0");
    var rest = kopecks % 100;
    return rubles + (rest ? "," + (rest < 10 ? "0" : "") + rest : "") + "\u00a0₽";
  }
  document.addEventListener(
    "submit",
    function (event) {
      var form = event.target;
      var step = parseInt(form.getAttribute("data-step"), 10);
      var stepper = form.closest("[data-stepper]");
      if (!step || !stepper || !window.htmx) return;
      event.preventDefault();
      event.stopImmediatePropagation(); // htmx не отправляет каждое нажатие отдельно
      var value = stepper.querySelector(".stepper__value");
      var max = parseInt(stepper.getAttribute("data-max"), 10) || 1;
      var next = Math.min(max, Math.max(1, parseInt(value.textContent, 10) + step));
      value.textContent = String(next);
      var minus = stepper.querySelector('[data-step="-1"] button');
      var plus = stepper.querySelector('[data-step="1"] button');
      if (minus) minus.disabled = next <= 1;
      if (plus) plus.disabled = next >= max;
      var unit = parseInt(stepper.getAttribute("data-unit"), 10);
      var price = stepper.parentNode.querySelector(".line__price");
      if (unit && price) price.textContent = formatRub(unit * next);
      var token = form.querySelector('input[name="csrfmiddlewaretoken"]');
      var values = { quantity: String(next), csrfmiddlewaretoken: token ? token.value : "" };
      var action = form.getAttribute("action");
      clearTimeout(stepper._send);
      pendingSteps[action] = values;
      stepper._send = setTimeout(function () {
        delete pendingSteps[action];
        window.htmx.ajax("POST", action, { source: form, swap: "none", values: values });
      }, 300);
    },
    true,
  );
  // Переход сразу после «+/−» (например, «Оформить заказ»): сначала отправить отложенное.
  var pendingSteps = {};
  document.addEventListener(
    "click",
    function (event) {
      var link = event.target.closest && event.target.closest("a[href]");
      var actions = Object.keys(pendingSteps);
      if (!link || !actions.length || link.target) return;
      event.preventDefault();
      Promise.all(
        actions.map(function (action) {
          var body = new URLSearchParams(pendingSteps[action]);
          delete pendingSteps[action];
          return fetch(action, { method: "POST", body: body, credentials: "same-origin", headers: { "HX-Request": "true" } });
        }),
      ).finally(function () {
        location.href = link.href;
      });
    },
    true,
  );

  // --- «В корзине»: метка на карточках товаров, которые уже в корзине ---
  // Сетки товаров кэшируются общими для всех, поэтому список товаров корзины приходит
  // отдельно (#cart-state) и метка ставится здесь.
  var cartState = document.getElementById("cart-state");
  if (cartState) {
    var inCart = {};
    try {
      JSON.parse(cartState.textContent).forEach(function (slug) { inCart[slug] = true; });
    } catch (e) {
      inCart = {};
    }
    var markCards = function () {
      document.querySelectorAll("a.card[href]").forEach(markCard);
    };
    var markCard = function (card) {
      var match = card.getAttribute("href").match(/\/product\/([^/]+)\/$/);
      var img = card.querySelector(".card__img");
      if (!match || !img || !inCart[match[1]] || img.querySelector(".incart")) return;
      var mark = document.createElement("span");
      mark.className = "incart";
      mark.innerHTML = '<svg class="ic" width="14" height="14" aria-hidden="true"><use href="#i-bag"/></svg>В корзине';
      img.appendChild(mark);
    };
    markCards();
    document.addEventListener("htmx:afterSettle", markCards); // подгруженные страницы ленты
  }

  // --- Лента категорий: выбранная категория видна целиком ---
  // Положение ленты сохраняется между страницами, а выбранный сегмент (и нажатый — сразу при
  // нажатии) докручивается в поле зрения: название не остаётся обрезанным у края.
  var CATS_KEY = "didi:cats-x";
  function revealSeg(strip, seg, smooth) {
    var pad = 16;
    var left = seg.offsetLeft - pad;
    var right = seg.offsetLeft + seg.offsetWidth + pad - strip.clientWidth;
    var target = strip.scrollLeft;
    if (left < strip.scrollLeft) target = left;
    else if (right > strip.scrollLeft) target = right;
    if (target === strip.scrollLeft) return target;
    if (smooth && !reduced.matches && strip.scrollTo) strip.scrollTo({ left: target, behavior: "smooth" });
    else strip.scrollLeft = target;
    return target;
  }
  document.querySelectorAll(".cats").forEach(function (strip) {
    try {
      var saved = sessionStorage.getItem(CATS_KEY);
      if (saved !== null) strip.scrollLeft = parseInt(saved, 10) || 0;
    } catch (e) {
      // хранилище недоступно — просто без запоминания
    }
    var on = strip.querySelector(".seg.is-on");
    if (on) revealSeg(strip, on, false);
    strip.addEventListener("click", function (event) {
      var seg = event.target.closest(".seg");
      if (!seg) return;
      var target = revealSeg(strip, seg, true);
      try { sessionStorage.setItem(CATS_KEY, String(Math.max(0, target))); } catch (e) { /* без запоминания */ }
    });
  });

  // --- Шапка: сворачивание с гистерезисом 24/8 px (как в приложении) ---
  var header = document.querySelector("[data-header]");
  var quick = document.querySelector("[data-quick]");
  var drop = document.querySelector("[data-drop]");
  var quickOpenBtn = document.querySelector("[data-quick-open]");
  var fixedCompact = header && header.classList.contains("top--fixed");
  var COLLAPSE_AT = 24;
  var EXPAND_BELOW = 8;

  function setCompact(compact) {
    if (!header || fixedCompact) return;
    if (header.classList.contains("is-compact") === compact) return;
    header.classList.toggle("is-compact", compact);
    document.body.classList.toggle("hdr-compact", compact);
    var more = header.querySelector("[data-collapsible]");
    if (more) {
      // Свёрнутые поиск и категории не принимают фокус и не читаются диктором.
      if (compact) more.setAttribute("aria-hidden", "true");
      else more.removeAttribute("aria-hidden");
      more.inert = compact;
    }
    if (!compact) closeQuick(false);
    else closeDrop(false);
    if (quickOpenBtn && drop) quickOpenBtn.setAttribute("aria-controls", compact ? "quick-search" : "drop-search");
  }

  if (header && !fixedCompact) {
    var ticking = false;
    var onScroll = function () {
      if (ticking) return;
      ticking = true;
      window.requestAnimationFrame(function () {
        ticking = false;
        var y = window.scrollY;
        var compact = header.classList.contains("is-compact");
        if (!compact && y > COLLAPSE_AT) setCompact(true);
        else if (compact && y < EXPAND_BELOW) setCompact(false);
      });
    };
    window.addEventListener("scroll", onScroll, { passive: true });
    onScroll();
  }

  // --- Быстрый поиск: поле выезжает из лаймовой кнопки, страница не прокручивается ---
  var quickTimer = null;
  function openQuick() {
    if (!quick) return;
    clearTimeout(quickTimer);
    quick.hidden = false;
    void quick.offsetWidth; // старт анимации ширины из размера кнопки
    quick.classList.add("is-open");
    if (quickOpenBtn) quickOpenBtn.setAttribute("aria-expanded", "true");
    var input = quick.querySelector("input");
    // Фокус после того, как поле выехало: иначе клавиатура телефона дёргает раскладку.
    quickTimer = setTimeout(function () { input.focus(); }, reduced.matches ? 0 : 200);
  }
  function closeQuick(returnFocus) {
    if (!quick || quick.hidden) return;
    clearTimeout(quickTimer);
    quick.classList.remove("is-open");
    if (quickOpenBtn) quickOpenBtn.setAttribute("aria-expanded", "false");
    quickTimer = setTimeout(function () { quick.hidden = true; }, reduced.matches ? 0 : 320);
    if (returnFocus && quickOpenBtn) quickOpenBtn.focus();
  }
  // --- Выпадающий поиск: вверху каталога поле с фильтрами раскрывается под строкой шапки ---
  function openDrop() {
    drop.hidden = false;
    quickOpenBtn.setAttribute("aria-expanded", "true");
    var input = drop.querySelector("input[name='q']");
    setTimeout(function () { input.focus(); }, reduced.matches ? 0 : 120);
  }
  function closeDrop(returnFocus) {
    if (!drop || drop.hidden) return;
    drop.hidden = true;
    if (quickOpenBtn) quickOpenBtn.setAttribute("aria-expanded", "false");
    if (returnFocus && quickOpenBtn) quickOpenBtn.focus();
  }
  if (quickOpenBtn) {
    quickOpenBtn.addEventListener("click", function (event) {
      event.preventDefault(); // без JS кнопка — ссылка на страницу поиска
      var compact = !header || header.classList.contains("is-compact");
      if (!compact && drop) {
        if (drop.hidden) openDrop();
        else closeDrop(false);
        return;
      }
      if (quick && !quick.hidden && quick.classList.contains("is-open")) closeQuick(true);
      else openQuick();
    });
  }
  if (drop) {
    drop.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeDrop(true);
    });
  }
  if (quick) {
    quick.querySelector("[data-quick-close]").addEventListener("click", function () { closeQuick(true); });
    quick.addEventListener("keydown", function (event) {
      if (event.key === "Escape") closeQuick(true);
    });
    quick.addEventListener("submit", function (event) {
      if (!quick.querySelector("input").value.trim()) event.preventDefault();
    });
  }

  // --- Логотип: наверх коротким путём (с главной), без перемотки через всю ленту ---
  var SHORT_RETURN = 480;
  var toTop = document.querySelector("[data-to-top]");
  if (toTop) {
    toTop.addEventListener("click", function (event) {
      if (location.pathname !== "/" || location.search) return; // с других страниц — на главную
      event.preventDefault();
      if (window.scrollY > SHORT_RETURN && !reduced.matches) {
        window.scrollTo({ top: SHORT_RETURN, behavior: "instant" });
      }
      window.scrollTo({ top: 0, behavior: reduced.matches ? "instant" : "smooth" });
    });
  }

  // --- Тема: переключатель в шапке и выбор в профиле, без перезагрузки ---
  var darkQuery = window.matchMedia("(prefers-color-scheme: dark)");

  function effectiveTheme() {
    var explicit = root.getAttribute("data-theme");
    if (explicit) return explicit;
    return darkQuery.matches ? "dark" : "light";
  }

  // Цвет строки состояния — фон текущей палитры и темы (после смены атрибутов <html>).
  function syncThemeColor() {
    var color = getComputedStyle(root).getPropertyValue("--bg").trim();
    if (!color) return;
    document.querySelectorAll('meta[name="theme-color"]').forEach(function (meta) {
      meta.content = color;
      meta.removeAttribute("media");
    });
  }

  function applyTheme(value) {
    // value: "light" | "dark" | "system"; «как в системе» тоже хранится — иначе тема магазина.
    if (value === "light" || value === "dark") root.setAttribute("data-theme", value);
    else root.removeAttribute("data-theme");
    setCookie("theme", value === "light" || value === "dark" ? value : "system", YEAR);
    var scheme = document.querySelector('meta[name="color-scheme"]');
    if (scheme) scheme.content = value === "system" ? "light dark" : value;
    syncThemeColor();
    var hidden = document.querySelectorAll('[data-theme-form] input[name="theme"]');
    hidden.forEach(function (input) { input.value = effectiveTheme() === "dark" ? "light" : "dark"; });
    document.querySelectorAll('[data-theme-select] input[name="theme"]').forEach(function (input) {
      input.checked = input.value === value;
    });
  }

  document.querySelectorAll("[data-theme-form]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      applyTheme(effectiveTheme() === "dark" ? "light" : "dark");
    });
  });
  // Палитра, акцент «Своей», углы, размер текста: атрибут <html> + cookie (сервер проверяет
  // значения по белому списку; значение по умолчанию — без атрибута).
  var LOOK = {
    palette: { attr: "data-palette", cookie: "palette", plain: "lime" },
    accent: { attr: "data-accent", cookie: "accent", plain: null },
    radius: { attr: "data-radius", cookie: "radius", plain: "normal" },
    text: { attr: "data-text", cookie: "text_size", plain: "s" }
  };

  function applyLook(name, value, form) {
    var spec = LOOK[name];
    setCookie(spec.cookie, value, YEAR);
    if (name === "palette") {
      var accents = form.querySelector("[data-accents]");
      if (accents) accents.hidden = value !== "custom";
      if (value === "custom") {
        var checked = form.querySelector('input[name="accent"]:checked');
        if (checked) root.setAttribute("data-accent", checked.value);
      } else {
        root.removeAttribute("data-accent");
      }
    }
    if (name === "accent" && root.getAttribute("data-palette") !== "custom") return;
    if (value === spec.plain) root.removeAttribute(spec.attr);
    else root.setAttribute(spec.attr, value);
    syncThemeColor();
  }

  document.querySelectorAll("[data-theme-select]").forEach(function (form) {
    form.addEventListener("change", function (event) {
      var name = event.target.name;
      if (name === "theme") applyTheme(event.target.value);
      else if (LOOK[name]) applyLook(name, event.target.value, form);
    });
    form.addEventListener("submit", function (event) { event.preventDefault(); });
  });

  // --- Баннер приложения: закрыть без перезагрузки ---
  document.querySelectorAll("[data-banner-close]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      setCookie("app_banner", "hidden", YEAR);
      var banner = form.closest("[data-banner]");
      if (banner) banner.remove();
    });
  });

  // --- Подтверждение опасных действий (отмена заказа, удаление аккаунта) ---
  document.querySelectorAll("form[data-confirm]").forEach(function (form) {
    form.addEventListener("submit", function (event) {
      if (!window.confirm(form.getAttribute("data-confirm"))) event.preventDefault();
    });
  });

  // --- Карточка товара: «Назад» ведёт туда, откуда пришли (если с этого сайта) ---
  var back = document.querySelector("[data-back]");
  if (back && document.referrer && document.referrer.indexOf(location.origin + "/") === 0 && history.length > 1) {
    back.addEventListener("click", function (event) {
      event.preventDefault();
      history.back();
    });
  }

  // --- Галерея: активная точка по прокрутке ---
  var track = document.querySelector("[data-gallery]");
  if (track) {
    var dots = track.parentElement.querySelectorAll(".hero__dots a");
    if (dots.length) {
      track.addEventListener("scroll", function () {
        var index = Math.round(track.scrollLeft / track.clientWidth);
        dots.forEach(function (dot, i) { dot.classList.toggle("is-on", i === index); });
      }, { passive: true });
    }
  }

  // --- Главная: картинки фото-баннера сменяют друг друга, баннеры подряд — карусель ---
  // Только пока блок на экране и вкладка открыта; «уменьшить движение» — без автолистания
  // карусели (картинки баннера меняются растворением без приближения — это задаёт CSS).
  function initHomeMotion(scope) {
    var visible = new WeakMap();
    var io = "IntersectionObserver" in window ? new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) { visible.set(entry.target, entry.isIntersecting); });
    }, { threshold: 0.35 }) : null;
    function onScreen(el) { return !io || visible.get(el) === true; }

    scope.querySelectorAll("[data-slides]").forEach(function (box) {
      if (box._bound) return;
      box._bound = true;
      var slides = box.querySelectorAll(".hblock-photo__slide");
      if (slides.length < 2) return;
      if (io) io.observe(box);
      var index = 0;
      setInterval(function () {
        if (document.hidden || !onScreen(box)) return;
        slides[index].classList.remove("is-on");
        index = (index + 1) % slides.length;
        var img = slides[index].querySelector("img");
        if (img && img.loading === "lazy") img.loading = "eager";
        slides[index].classList.add("is-on");
      }, 4800);
    });

    scope.querySelectorAll("[data-carousel]").forEach(function (carousel) {
      if (carousel._bound) return;
      carousel._bound = true;
      var track = carousel.querySelector("[data-carousel-track]");
      var dots = carousel.querySelectorAll("[data-carousel-dot]");
      var count = dots.length;
      if (!track || count < 2) return;
      var current = 0;
      var pausedUntil = 0;
      function slideWidth() { return track.querySelector(".hblock-carousel__slide").getBoundingClientRect().width; }
      function step() {
        var gap = parseFloat(getComputedStyle(track).columnGap) || 0;
        return slideWidth() + gap;
      }
      function mark(index) {
        current = index;
        dots.forEach(function (dot, i) {
          dot.classList.toggle("is-on", i === index);
          if (i === index) dot.setAttribute("aria-current", "true");
          else dot.removeAttribute("aria-current");
        });
      }
      function go(index, smooth) {
        track.scrollTo({ left: index * step(), behavior: smooth && !reduced.matches ? "smooth" : "auto" });
        mark(index);
      }
      var ticking = false;
      track.addEventListener("scroll", function () {
        if (ticking) return;
        ticking = true;
        requestAnimationFrame(function () {
          ticking = false;
          mark(Math.max(0, Math.min(count - 1, Math.round(track.scrollLeft / step()))));
        });
      }, { passive: true });
      dots.forEach(function (dot, i) {
        dot.addEventListener("click", function () {
          pausedUntil = Date.now() + 10000;
          go(i, true);
        });
      });
      // Палец, мышь или фокус на карусели — пауза, чтобы баннер не уехал из-под руки.
      ["pointerdown", "wheel", "focusin", "mouseenter"].forEach(function (name) {
        carousel.addEventListener(name, function () { pausedUntil = Date.now() + 10000; }, { passive: true });
      });
      if (io) io.observe(carousel);
      setInterval(function () {
        if (reduced.matches || document.hidden || Date.now() < pausedUntil || !onScreen(carousel)) return;
        go((current + 1) % count, true);
      }, 6000);
    });
  }
  initHomeMotion(document);
  window.didiHomeMotion = initHomeMotion; // демо на Pages перерисовывает главную

  // --- Карточка товара: «В корзину» / «Добавить ещё», сколько уже в корзине и «−/+» ---
  // Обработчики делегированы документу: форму могут перерисовать (демо на Pages).
  function setCartBadges(count) {
    ["cart-badge-top", "cart-badge-tab"].forEach(function (id) {
      var badge = document.getElementById(id);
      if (!badge) return;
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.hidden = !count;
    });
  }
  function incartState() {
    var el = document.getElementById("incart-state");
    if (!el) return null;
    if (!el._data) {
      try { el._data = JSON.parse(el.textContent) || {}; } catch (e) { el._data = {}; }
    }
    return el._data;
  }
  function chosenVariant(form) {
    var input = form.querySelector('input[name="variant"]:checked') || form.querySelector('input[type="hidden"][name="variant"]');
    return input ? input.value : "";
  }
  function renderIncart(form, keepDone) {
    var state = incartState();
    var row = form.querySelector("[data-incart]");
    var cta = form.querySelector("[data-cta]");
    var current = state && state[chosenVariant(form)];
    var quantity = current ? current.q : 0;
    if (cta && !keepDone) {
      cta.classList.remove("is-done");
      cta.querySelector(".cta__label").textContent = quantity ? "Добавить ещё" : "В корзину";
    }
    if (!row || !state) return;
    var parts = [];
    Object.keys(state).forEach(function (id) {
      if (state[id].q) parts.push(state[id].size + " × " + state[id].q);
    });
    row.hidden = !parts.length;
    // Выбранный размер в корзине — его количество и «−/+»; иначе — какие размеры уже там.
    row.querySelector("[data-incart-text]").textContent = quantity ? "В корзине · " + quantity + " шт." : "В корзине: " + parts.join(", ");
    var stepper = row.querySelector("[data-incart-stepper]");
    stepper.hidden = !quantity;
    stepper.querySelector("[data-incart-qty]").textContent = String(quantity);
    stepper.querySelector('[data-incart-step="1"]').disabled = !current || quantity >= current.max;
  }
  function sendCartLine(form, id, quantity) {
    // Демо на GitHub Pages подменяет отправку (window.didiCartLine) — сервера там нет.
    if (window.didiCartLine) return Promise.resolve(window.didiCartLine(id, quantity));
    var row = form.querySelector("[data-incart]");
    var url = row.getAttribute("data-line-url").replace(/\/0\/$/, "/" + id + "/");
    var token = form.querySelector('input[name="csrfmiddlewaretoken"]');
    var body = new URLSearchParams({ quantity: String(quantity), csrfmiddlewaretoken: token ? token.value : "" });
    return fetch(url, {
      method: "POST", body: body, credentials: "same-origin", keepalive: true, headers: { Accept: "application/json" }
    }).then(function (response) { return response.json(); });
  }
  // Нажатия копятся: уходит последнее значение, следующий запрос — после ответа на прошлый.
  var incartWanted = {};
  var incartBusy = {};
  function flushCartLine(form, id) {
    if (incartBusy[id] || !(id in incartWanted)) return;
    var quantity = incartWanted[id];
    delete incartWanted[id];
    incartBusy[id] = true;
    sendCartLine(form, id, quantity)
      .then(function (data) {
        if (!data) return;
        var state = incartState();
        if (state && state[id] && !(id in incartWanted)) state[id].q = data.quantity;
        if (typeof data.count === "number") setCartBadges(data.count);
        var result = form.querySelector("#buy-result");
        if (result) {
          result.innerHTML = "";
          (data.errors || []).forEach(function (text) {
            var note = document.createElement("p");
            note.className = "note note--danger";
            note.textContent = text;
            result.appendChild(note);
          });
        }
        renderIncart(form);
      })
      .catch(function () {})
      .then(function () {
        incartBusy[id] = false;
        flushCartLine(form, id);
      });
  }
  // Демо на Pages может запустить этот файл повторно на той же странице — без двойных шагов.
  if (!window.__didiIncartBound) {
    window.__didiIncartBound = true;
    document.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-incart-step]");
      if (!button) return;
      var form = button.closest("[data-buy]");
      var state = incartState();
      var id = form && chosenVariant(form);
      if (!state || !state[id]) return;
      var step = parseInt(button.getAttribute("data-incart-step"), 10);
      var current = state[id];
      current.q = Math.max(0, Math.min(current.max, current.q + step));
      incartWanted[id] = current.q;
      renderIncart(form);
      flushCartLine(form, id);
    });
    // Добавлено («В корзину»): +1 к выбранному размеру. htmx — ответ сервера, демо — своё событие.
    function onAdded(form) {
      var state = incartState();
      var current = state && state[chosenVariant(form)];
      if (current) current.q = Math.min(current.max, current.q + 1);
      var cta = form.querySelector("[data-cta]");
      if (cta) {
        cta.classList.add("is-done");
        cta.querySelector(".cta__label").textContent = "Добавлено в корзину";
      }
      renderIncart(form, true);
    }
    document.addEventListener("htmx:afterSwap", function (event) {
      var form = event.target.closest && event.target.closest("[data-buy]");
      if (form && form.querySelector("[data-added]")) onAdded(form);
    });
    document.addEventListener("didi:cart-added", function (event) {
      var form = event.target.closest && event.target.closest("[data-buy]");
      if (form) onAdded(form);
    });
    document.addEventListener("change", function (event) {
      var form = event.target.closest && event.target.closest("[data-buy]");
      if (!form || event.target.name !== "variant") return;
      var result = form.querySelector("#buy-result");
      if (result) result.innerHTML = "";
      renderIncart(form);
    });
  }

  // --- Оформление: стоимость доставки и итог по выбранному способу, адрес — только курьеру ---
  var checkout = document.querySelector("[data-checkout]");
  if (checkout) {
    var totalEl = checkout.querySelector("[data-total]");
    var costEl = checkout.querySelector("[data-delivery-cost]");
    var address = checkout.querySelector("[data-address]");
    var items = parseInt(totalEl.getAttribute("data-items"), 10);
    var rub = function (kopecks) {
      var rubles = Math.floor(kopecks / 100);
      var rest = kopecks % 100;
      var whole = String(rubles).replace(/\B(?=(\d{3})+(?!\d))/g, " ");
      return (rest ? whole + "," + String(rest).padStart(2, "0") : whole) + " ₽";
    };
    var update = function () {
      var picked = checkout.querySelector('input[name="delivery_method"]:checked');
      if (!picked) return;
      var cost = parseInt(picked.getAttribute("data-cost"), 10) || 0;
      costEl.textContent = rub(cost);
      totalEl.textContent = rub(items + cost);
      if (address) address.hidden = picked.value === "pickup";
    };
    checkout.addEventListener("change", function (event) {
      if (event.target.name === "delivery_method") update();
    });
    update();
    // Повторное нажатие «Оформить» не уходит дважды (ключ идемпотентности всё равно защищает).
    checkout.addEventListener("submit", function () {
      var button = checkout.querySelector('button[type="submit"]');
      setTimeout(function () { button.disabled = true; }, 0);
    });
  }

  // Фото профиля: выбранный файл отправляется сразу (без JS — кнопка «Отправить» в noscript).
  document.addEventListener("change", function (event) {
    var input = event.target;
    if (!input.matches || !input.matches("[data-autosubmit]") || !input.files || !input.files.length) return;
    if (input.form.requestSubmit) input.form.requestSubmit();
    else input.form.submit();
  });
})();
