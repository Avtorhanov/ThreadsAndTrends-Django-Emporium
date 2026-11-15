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
      var shown = parseInt(value.textContent, 10);
      // Число до первого неотправленного нажатия — к нему вернёмся, если запрос не пройдёт.
      if (stepper._server == null) stepper._server = shown;
      var next = Math.min(max, Math.max(1, shown + step));
      showStep(stepper, next);
      var token = form.querySelector('input[name="csrfmiddlewaretoken"]');
      var values = { quantity: String(next), csrfmiddlewaretoken: token ? token.value : "" };
      var action = form.getAttribute("action");
      clearTimeout(stepper._send);
      pendingSteps[action] = values;
      stepper._send = setTimeout(function () {
        stepper._send = null;
        delete pendingSteps[action];
        window.htmx.ajax("POST", action, { source: form, swap: "none", values: values });
      }, 300);
    },
    true,
  );
  function showStep(stepper, quantity) {
    var max = parseInt(stepper.getAttribute("data-max"), 10) || 1;
    stepper.querySelector(".stepper__value").textContent = String(quantity);
    var minus = stepper.querySelector('[data-step="-1"] button');
    var plus = stepper.querySelector('[data-step="1"] button');
    if (minus) minus.disabled = quantity <= 1;
    if (plus) plus.disabled = quantity >= max;
    var unit = parseInt(stepper.getAttribute("data-unit"), 10);
    var price = stepper.parentNode.querySelector(".line__price");
    if (unit && price) price.textContent = formatRub(unit * quantity);
  }
  // --- Сбой запроса (нет сети, ошибка сервера, устаревшая страница): покупатель видит причину,
  // а «+/−» корзины возвращает число, которое знает сервер ---
  function requestFailed(status) {
    if (status === 403) toast("Страница устарела — обновите её и повторите");
    else if (status) toast("Не получилось — попробуйте ещё раз");
    else toast("Нет связи — проверьте интернет и повторите");
  }
  document.addEventListener("htmx:afterRequest", function (event) {
    var detail = event.detail || {};
    var stepper = detail.elt && detail.elt.closest && detail.elt.closest("[data-stepper]");
    if (detail.successful) {
      if (stepper && !stepper._send) stepper._server = null;
      return;
    }
    if (stepper && stepper._server != null && document.contains(stepper)) {
      clearTimeout(stepper._send);
      stepper._send = null;
      delete pendingSteps[detail.elt.getAttribute("action")];
      showStep(stepper, stepper._server);
      stepper._server = null;
    }
    requestFailed(detail.xhr ? detail.xhr.status : 0);
  });
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

  // --- Шапка: свёрнута после 24 px, у начала страницы (< 8 px) — развёрнута ---
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

  // --- Прокрутка: вниз — шапка каталога сворачивается до строки; вверх в любом месте ленты —
  // оба меню возвращаются (шапка каталога — с категориями, на стекле). Направление — по пути в
  // одну сторону (BARS_DELTA), а не по каждому событию: мелкие рывки пальца и «резинка» iOS у
  // краёв страницы меню не дёргают.
  // Нижнее меню уезжает не сразу: при медленной прокрутке пальцем оно остаётся, уезжает после
  // быстрого взмаха (скорость за последние ~120 мс) или когда лента ушла далеко. ---
  var BARS_DELTA = 16;
  var NEAR_END = 48;
  var HIDE_SPEED = 0.9; // px/мс — быстрый взмах
  var HIDE_FLICK_TRAVEL = 60; // и при этом лента ушла хотя бы на столько
  var HIDE_TRAVEL = 360; // без пальца на экране (колесо, клавиши) — уехать далеко
  var lastY = Math.max(0, window.scrollY);
  var travel = 0;
  var samples = [];
  var touching = false;
  var freeTravel = 0; // путь вниз без пальца на экране (колесо, клавиши, инерция после взмаха)
  var tabbar = document.querySelector(".tabbar");

  function speed(y, now) {
    // Средняя скорость вниз за последние ~120 мс (px/мс).
    samples.push([now, y]);
    while (samples.length > 2 && now - samples[0][0] > 120) samples.shift();
    var first = samples[0];
    var dt = now - first[0];
    return dt > 16 ? (y - first[1]) / dt : 0;
  }
  window.addEventListener("touchstart", function () { touching = true; freeTravel = 0; samples = []; }, { passive: true });
  window.addEventListener("touchend", function () { touching = false; }, { passive: true });
  window.addEventListener("touchcancel", function () { touching = false; }, { passive: true });

  function setBars(hidden) {
    if ((root.getAttribute("data-bars") === "hidden") === hidden) return;
    if (hidden) root.setAttribute("data-bars", "hidden");
    else root.removeAttribute("data-bars");
  }
  function typing() {
    // Поле ввода в фокусе — открыта клавиатура: раскладку не трогаем.
    var active = document.activeElement;
    return !!active && active.matches && active.matches("input:not([type=radio]):not([type=checkbox]), textarea, select");
  }
  function reveal(y) {
    // Раскрытая посреди ленты шапка лежит на стекле; у начала страницы — без фона.
    if (header && !fixedCompact) header.classList.toggle("is-revealed", !header.classList.contains("is-compact") && y > EXPAND_BELOW);
  }

  var ticking = false;
  function onScroll() {
    if (ticking) return;
    ticking = true;
    window.requestAnimationFrame(function () {
      ticking = false;
      var max = Math.max(0, document.documentElement.scrollHeight - window.innerHeight);
      var y = Math.min(Math.max(0, window.scrollY), max); // без «резинки» у краёв
      var dy = y - lastY;
      var v = speed(y, performance.now());
      lastY = y;
      freeTravel = touching || dy <= 0 ? 0 : freeTravel + dy;
      if (y < EXPAND_BELOW) {
        travel = 0;
        setCompact(false);
        setBars(false);
        reveal(y);
        return;
      }
      if (typing() || !dy) return;
      if ((dy > 0) !== (travel > 0)) travel = 0;
      travel += dy;
      if (travel > BARS_DELTA && y > COLLAPSE_AT) {
        setCompact(true);
        // Короткая страница и конец страницы — меню остаётся: листать дальше почти некуда.
        var flick = v > HIDE_SPEED && travel > HIDE_FLICK_TRAVEL;
        var far = freeTravel > HIDE_TRAVEL;
        if ((flick || far) && max > 240 && y < max - NEAR_END) setBars(true);
      } else if (travel < -BARS_DELTA) {
        setCompact(false);
        setBars(false);
      }
      if (y >= max - NEAR_END) setBars(false);
      reveal(y);
    });
  }
  if (header && !fixedCompact && window.scrollY > COLLAPSE_AT) setCompact(true);
  window.addEventListener("scroll", onScroll, { passive: true });
  // Клавиатурой или диктором в меню — оно возвращается.
  if (tabbar) tabbar.addEventListener("focusin", function () { setBars(false); });
  // Товар добавлен в корзину — меню показывается: виден новый счётчик и путь в корзину.
  document.addEventListener("htmx:oobAfterSwap", function (event) {
    var target = event.detail && event.detail.target;
    if (target && /^cart-badge/.test(target.id || "")) setBars(false);
  });
  document.addEventListener("didi:cart-changed", function () { setBars(false); });

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
  // Safari замечает новый тег надёжнее, чем смену content у прежнего: старые теги заменяются
  // одним новым (без media — выбор темы явный). Повтор после растворения темы — на случай,
  // если браузер перечитал цвет, пока страница ещё менялась.
  function syncThemeColor() {
    var color = getComputedStyle(root).getPropertyValue("--bg").trim();
    if (!color) return;
    var metas = document.querySelectorAll('meta[name="theme-color"]');
    var fresh = document.createElement("meta");
    fresh.name = "theme-color";
    fresh.content = color;
    if (metas.length) metas[0].parentNode.insertBefore(fresh, metas[0]);
    else document.head.appendChild(fresh);
    metas.forEach(function (meta) { meta.remove(); });
  }
  function syncThemeColorSoon() {
    syncThemeColor();
    clearTimeout(syncThemeColorSoon.timer);
    syncThemeColorSoon.timer = setTimeout(function () {
      syncThemeColor();
      // Safari перечитывает цвет полос браузера при прокрутке: сдвиг на 1 px и обратно.
      if (document.documentElement.scrollHeight > window.innerHeight + 1) {
        window.scrollBy(0, 1);
        requestAnimationFrame(function () { window.scrollBy(0, -1); });
      }
    }, 500);
  }

  function applyTheme(value) {
    // value: "light" | "dark" | "system"; «как в системе» тоже хранится — иначе тема магазина.
    if (value === "light" || value === "dark") root.setAttribute("data-theme", value);
    else root.removeAttribute("data-theme");
    setCookie("theme", value === "light" || value === "dark" ? value : "system", YEAR);
    var scheme = document.querySelector('meta[name="color-scheme"]');
    if (scheme) scheme.content = value === "system" ? "light dark" : value;
    syncThemeColorSoon();
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
  // Палитра, акцент «Своей», углы, масштаб, нижнее меню: атрибут <html> + cookie (сервер проверяет
  // значения по белому списку; значение по умолчанию — без атрибута).
  var LOOK = {
    palette: { attr: "data-palette", cookie: "palette", plain: "lime" },
    accent: { attr: "data-accent", cookie: "accent", plain: null },
    radius: { attr: "data-radius", cookie: "radius", plain: "normal" },
    text: { attr: "data-text", cookie: "text_size", plain: "100" },
    nav: { attr: "data-nav", cookie: "nav", plain: "solid" }
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
    syncThemeColorSoon();
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
  // «Назад» со своего сайта — шаг по истории (сохраняет прокрутку ленты), иначе — ссылка.
  if (document.referrer && document.referrer.indexOf(location.origin + "/") === 0 && history.length > 1) {
    document.querySelectorAll("[data-back]").forEach(function (back) {
      back.addEventListener("click", function (event) {
        event.preventDefault();
        history.back();
      });
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

  // --- Фото товара на весь экран: PhotoSwipe (свайп между фото, щипок и двойной тап —
  // увеличение, свайп вниз или Esc — закрыть). Скрипт и стили грузятся при первом нажатии. ---
  // Обработчик делегирован: галерея и список фото берутся в момент нажатия (разметку могут
  // перерисовать после загрузки страницы).
  var pswpLoading = null;
  function loadPhotoSwipe(gallery) {
    if (window.PhotoSwipe) return Promise.resolve(window.PhotoSwipe);
    if (pswpLoading) return pswpLoading;
    pswpLoading = new Promise(function (resolve, reject) {
      var css = document.createElement("link");
      css.rel = "stylesheet";
      css.href = gallery.getAttribute("data-pswp-css");
      document.head.appendChild(css);
      var js = document.createElement("script");
      js.src = gallery.getAttribute("data-pswp-js");
      js.onload = function () { resolve(window.PhotoSwipe); };
      js.onerror = function () { pswpLoading = null; css.remove(); js.remove(); reject(new Error("photoswipe")); };
      document.head.appendChild(js);
    });
    return pswpLoading;
  }
  document.addEventListener("click", function (event) {
    var link = event.target.closest && event.target.closest("[data-zoom]");
    var gallery = link && link.closest("[data-zoom-gallery]");
    if (!gallery || event.metaKey || event.ctrlKey || event.shiftKey || event.button) return;
    event.preventDefault();
    var links = Array.prototype.slice.call(gallery.querySelectorAll("[data-zoom]"));
    loadPhotoSwipe(gallery).then(function (PhotoSwipe) {
      var items = links.map(function (a) {
        var img = a.querySelector("img");
        // Размеры оригинала — из модели; если их нет — по загруженному превью.
        var w = parseInt(a.getAttribute("data-w"), 10) || (img && img.naturalWidth) || 1200;
        var h = parseInt(a.getAttribute("data-h"), 10) || (img && img.naturalHeight) || 1500;
        return { src: a.href, width: w, height: h, msrc: img ? img.currentSrc || img.src : undefined, alt: img ? img.alt : "", element: a };
      });
      var pswp = new PhotoSwipe({
        dataSource: items,
        index: Math.max(0, links.indexOf(link)),
        bgOpacity: 1,
        showHideAnimationType: reduced.matches ? "none" : "zoom",
        initialZoomLevel: "fit",
        secondaryZoomLevel: 2,
        maxZoomLevel: 4,
        wheelToZoom: true,
        closeTitle: "Закрыть",
        zoomTitle: "Увеличить",
        arrowPrevTitle: "Предыдущее фото",
        arrowNextTitle: "Следующее фото",
        errorMsg: "Фото не загрузилось",
        indexIndicatorSep: " из ",
      });
      // Миниатюра для анимации открытия/закрытия — фото в галерее страницы.
      pswp.addFilter("thumbEl", function (thumbEl, data) {
        var img = data.element && data.element.querySelector("img");
        return img || thumbEl;
      });
      // Закрыли на другом фото — галерея страницы встаёт на него же.
      pswp.on("close", function () {
        var target = links[pswp.currIndex];
        if (target) gallery.scrollTo({ left: target.parentElement.offsetLeft, behavior: "auto" });
      });
      pswp.init();
    }, function () { window.location.href = link.href; });
  });

  // --- «Поделиться»: системное меню (телефон), иначе — ссылка копируется в буфер ---
  var toastTimer = null;
  function toast(text) {
    var el = document.querySelector(".toast");
    if (!el) {
      el = document.createElement("div");
      el.className = "toast";
      el.setAttribute("role", "status");
      el.setAttribute("aria-live", "polite");
      document.body.appendChild(el);
    }
    el.textContent = text;
    void el.offsetWidth;
    el.classList.add("is-on");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(function () { el.classList.remove("is-on"); }, 2200);
  }
  document.addEventListener("click", function (event) {
    var button = event.target.closest && event.target.closest("[data-share]");
    if (!button) return;
    event.preventDefault();
    var url = button.href || location.href;
    var title = button.getAttribute("data-share-title") || document.title;
    if (navigator.share) {
      navigator.share({ title: title, url: url }).catch(function () {}); // отмена — не ошибка
      return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
      navigator.clipboard.writeText(url).then(
        function () { toast("Ссылка скопирована"); },
        function () { window.prompt("Ссылка на товар", url); }
      );
    } else {
      window.prompt("Ссылка на товар", url);
    }
  });

  // --- Заказ «по согласованию»: текст продавцу копируется в буфер (Telegram и ВКонтакте не
  // принимают текст в ссылке). Ссылка при этом открывается как обычно, в новой вкладке. ---
  document.addEventListener("click", function (event) {
    var el = event.target.closest && event.target.closest("[data-copy-text]");
    if (!el) return;
    var text = el.getAttribute("data-copy-text");
    var isLink = el.tagName === "A";
    if (!navigator.clipboard || !navigator.clipboard.writeText) {
      if (!isLink) window.prompt("Скопируйте текст", text);
      return;
    }
    navigator.clipboard.writeText(text).then(
      function () { toast(isLink ? "Текст заказа скопирован — вставьте его в чат" : "Текст скопирован"); },
      function () { if (!isLink) window.prompt("Скопируйте текст", text); }
    );
  });

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

  // --- Стрелки листания на компьютере (мышь): галерея товара, карусель, подборки, ленты ---
  // На сенсорных экранах — свайп, кнопок нет. Шаг — видимая ширина ленты (одно фото, один
  // баннер, ряд карточек); scroll-snap доводит до ближайшей карточки. У края кнопка скрыта.
  var finePointer = window.matchMedia("(hover: hover) and (pointer: fine)");
  var SCROLLERS = [
    ["[data-gallery]", "Предыдущее фото", "Следующее фото"],
    ["[data-carousel-track]", "Предыдущий баннер", "Следующий баннер"],
    [".hblock-rail__track", "Предыдущие товары", "Следующие товары"],
    [".hblock-cats__list", "Предыдущие категории", "Следующие категории"]
  ];
  function scrollButton(dir, label) {
    var button = document.createElement("button");
    button.type = "button";
    button.className = "scroll-btn scroll-btn--" + dir;
    button.setAttribute("aria-label", label);
    button.hidden = true;
    var ns = "http://www.w3.org/2000/svg";
    var svg = document.createElementNS(ns, "svg");
    svg.setAttribute("class", "ic");
    svg.setAttribute("width", "20");
    svg.setAttribute("height", "20");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS(ns, "use");
    use.setAttribute("href", "#i-chevron");
    svg.appendChild(use);
    button.appendChild(svg);
    return button;
  }
  function scrollPage(track) {
    var style = getComputedStyle(track);
    var page = track.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    return page + (parseFloat(style.columnGap) || 0);
  }
  function syncScroller(track) {
    var max = track.scrollWidth - track.clientWidth;
    track._prev.hidden = track.scrollLeft <= 2;
    track._next.hidden = track.scrollLeft >= max - 2;
  }
  function bindScroller(track, labels) {
    if (track._prev) return syncScroller(track);
    // Фото товара — кнопки внутри рамки фото; ленты — в обёртке по контуру ленты
    // (у лент отрицательные поля под тень, кнопки должны стоять по колонке страницы).
    var host = track.closest(".hero");
    if (!host) {
      host = document.createElement("div");
      host.className = "scroller";
      track.parentNode.insertBefore(host, track);
      host.appendChild(track);
    }
    host.classList.add("has-scroll-btns");
    track._prev = scrollButton("prev", labels[0]);
    track._next = scrollButton("next", labels[1]);
    host.appendChild(track._prev);
    host.appendChild(track._next);
    [[track._prev, -1], [track._next, 1]].forEach(function (pair) {
      pair[0].addEventListener("click", function () {
        track.scrollBy({ left: pair[1] * scrollPage(track), behavior: reduced.matches ? "auto" : "smooth" });
      });
    });
    var ticking = false;
    track.addEventListener("scroll", function () {
      if (ticking) return;
      ticking = true;
      requestAnimationFrame(function () { ticking = false; syncScroller(track); });
    }, { passive: true });
    if ("ResizeObserver" in window) new ResizeObserver(function () { syncScroller(track); }).observe(track);
    syncScroller(track);
  }
  function initScrollers(scope) {
    SCROLLERS.forEach(function (spec) {
      scope.querySelectorAll(spec[0]).forEach(function (track) { bindScroller(track, spec.slice(1)); });
    });
  }
  // Ленты появляются и после загрузки (htmx, «Вы смотрели», демо на Pages перерисовывает
  // страницы): новые подхватываются, у прежних пересчитывается край.
  function startScrollers() {
    initScrollers(document);
    if (!("MutationObserver" in window)) return;
    var queued = false;
    new MutationObserver(function () {
      if (queued) return;
      queued = true;
      requestAnimationFrame(function () { queued = false; initScrollers(document); });
    }).observe(document.body, { childList: true, subtree: true });
  }
  if (finePointer.matches) startScrollers();
  else if (finePointer.addEventListener) {
    finePointer.addEventListener("change", function onChange(event) {
      if (!event.matches) return;
      finePointer.removeEventListener("change", onChange);
      startScrollers();
    });
  }

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
    // Не disabled: по нажатию на «+» у предела покупатель видит сообщение.
    var plus = stepper.querySelector('[data-incart-step="1"]');
    var atLimit = !current || quantity >= current.max;
    plus.classList.toggle("is-limit", atLimit);
    if (atLimit) plus.setAttribute("aria-disabled", "true");
    else plus.removeAttribute("aria-disabled");
  }
  function showStockLimit(form) {
    var stepper = form.querySelector("[data-incart-stepper]");
    toast((stepper && stepper.getAttribute("data-limit-text")) || "Больше таких размеров не осталось");
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
    }).then(function (response) {
      // 400 — отказ с текстом (остаток закончился); остальное — сбой, обрабатывает catch.
      if (!response.ok && response.status !== 400) throw response.status;
      return response.json();
    });
  }
  // Нажатия копятся: уходит последнее значение, следующий запрос — после ответа на прошлый.
  var incartWanted = {};
  var incartBusy = {};
  var incartServer = {}; // количество, подтверждённое сервером: к нему откат при сбое
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
        incartServer[id] = data.quantity;
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
      .catch(function (status) {
        // Сбой: отложенные нажатия отменяются, на экране — то, что в корзине на самом деле.
        delete incartWanted[id];
        var state = incartState();
        if (state && state[id] && id in incartServer) state[id].q = incartServer[id];
        renderIncart(form);
        requestFailed(typeof status === "number" ? status : 0);
      })
      .then(function () {
        incartBusy[id] = false;
        flushCartLine(form, id);
      });
  }
  // Демо на Pages может запустить этот файл повторно на той же странице — без двойных шагов.
  if (!window.__didiIncartBound) {
    window.__didiIncartBound = true;
    // Размер не выбран: своё сообщение у блока размеров вместо системной подсказки.
    // invalid не всплывает — слушаем на перехвате; приходит по разу на каждую радиокнопку.
    document.addEventListener("invalid", function (event) {
      var input = event.target;
      if (input.name !== "variant" || !input.closest("[data-buy]")) return;
      event.preventDefault();
      var box = input.closest(".sizes");
      var message = box && box.querySelector("[data-size-error]");
      if (!message || !message.hidden) return;
      message.hidden = false;
      box.classList.add("is-invalid");
      box.scrollIntoView({ block: "center", behavior: reduced.matches ? "auto" : "smooth" });
    }, true);
    document.addEventListener("change", function (event) {
      if (event.target.name !== "variant") return;
      var box = event.target.closest(".sizes");
      var message = box && box.querySelector("[data-size-error]");
      if (!message) return;
      message.hidden = true;
      box.classList.remove("is-invalid");
    });
    document.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-incart-step]");
      if (!button) return;
      var form = button.closest("[data-buy]");
      var state = incartState();
      var id = form && chosenVariant(form);
      if (!state || !state[id]) return;
      var step = parseInt(button.getAttribute("data-incart-step"), 10);
      var current = state[id];
      if (step > 0 && current.q >= current.max) {
        showStockLimit(form);
        return;
      }
      if (!(id in incartServer)) incartServer[id] = current.q;
      current.q = Math.max(0, Math.min(current.max, current.q + step));
      incartWanted[id] = current.q;
      renderIncart(form);
      flushCartLine(form, id);
    });
    // «Добавить ещё» у предела: сообщение вместо запроса (на перехвате — раньше отправки формы).
    document.addEventListener("click", function (event) {
      var button = event.target.closest && event.target.closest("[data-cta]");
      var form = button && button.closest("[data-buy]");
      var state = form && incartState();
      var current = state && state[chosenVariant(form)];
      if (!current || !current.q || current.q < current.max) return;
      event.preventDefault();
      event.stopPropagation();
      showStockLimit(form);
    }, true);
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
