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

  // --- Шапка: сворачивание с гистерезисом 24/8 px (как в приложении) ---
  var header = document.querySelector("[data-header]");
  var quick = document.querySelector("[data-quick]");
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
  if (quickOpenBtn) quickOpenBtn.addEventListener("click", openQuick);
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

  function applyTheme(value) {
    // value: "light" | "dark" | "system"
    if (value === "light" || value === "dark") {
      root.setAttribute("data-theme", value);
      setCookie("theme", value, YEAR);
    } else {
      root.removeAttribute("data-theme");
      setCookie("theme", "", 0);
    }
    var scheme = document.querySelector('meta[name="color-scheme"]');
    if (scheme) scheme.content = value === "system" ? "light dark" : value;
    var colors = document.querySelectorAll('meta[name="theme-color"]');
    var color = effectiveTheme() === "dark" ? "#070E0A" : "#EBF1E2";
    colors.forEach(function (meta) { meta.content = color; meta.removeAttribute("media"); });
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
  document.querySelectorAll("[data-theme-select]").forEach(function (form) {
    form.addEventListener("change", function (event) {
      if (event.target.name === "theme") applyTheme(event.target.value);
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
