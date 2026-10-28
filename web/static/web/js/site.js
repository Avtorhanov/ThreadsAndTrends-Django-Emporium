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

  // --- «В корзину»: заливка и «Добавлено в корзину» после ответа htmx ---
  var buy = document.querySelector("[data-buy]");
  if (buy) {
    var cta = buy.querySelector("[data-cta]");
    var label = cta && cta.querySelector(".cta__label");
    buy.addEventListener("htmx:afterSwap", function () {
      if (!cta) return;
      var added = !!buy.querySelector("[data-added]");
      cta.classList.toggle("is-done", added);
      label.textContent = added ? "Добавлено в корзину" : "В корзину";
    });
    buy.addEventListener("change", function () {
      if (!cta) return;
      cta.classList.remove("is-done");
      label.textContent = "В корзину";
      var result = buy.querySelector("#buy-result");
      if (result) result.innerHTML = "";
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
})();
