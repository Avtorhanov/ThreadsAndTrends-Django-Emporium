/* Редактор витрины для администратора: подключается только вошедшему администратору (base.html).
   - Текст с рамкой при наведении: двойное нажатие — правка на месте. Enter — сохранить, Esc — отмена;
     «Скрыть» убирает текст с сайта, «Исходный» возвращает текст из шаблона.
   - Списки «Контакты», «Помощь», ссылки подвала: ✎ — изменить, × — удалить, «+ Добавить».
   Запросы — admin API панели (сессия + CSRF), страница после изменения обновляется. */
(function () {
  "use strict";

  var API = "/api/v1/admin/content/";
  var tokenMeta = document.querySelector('meta[name="csrf-token"]');
  var csrf = tokenMeta ? tokenMeta.content : "";

  function request(method, path, body) {
    return fetch(API + path, {
      method: method,
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf, Accept: "application/json" },
      body: body === undefined ? undefined : JSON.stringify(body),
    }).then(function (response) {
      if (response.status === 204) return null;
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(errorText(data) || "Не удалось сохранить (" + response.status + ").");
        return data;
      });
    });
  }

  function errorText(data) {
    if (!data || typeof data !== "object") return "";
    if (data.detail) return data.detail;
    for (var key in data) {
      var value = data[key];
      if (Array.isArray(value) && value.length) return value[0];
      if (typeof value === "string") return value;
    }
    return "";
  }

  function fail(error) {
    window.alert(error.message || "Не удалось сохранить.");
  }

  function el(tag, attrs, text) {
    var node = document.createElement(tag);
    for (var name in attrs || {}) node.setAttribute(name, attrs[name]);
    if (text) node.textContent = text;
    return node;
  }

  // --- Тексты ---

  var editing = null;
  var bar = el("div", { class: "sx-bar", role: "toolbar", "aria-label": "Правка текста" });
  [
    ["save", "Сохранить"],
    ["hide", "Скрыть"],
    ["reset", "Исходный"],
    ["cancel", "Отмена"],
  ].forEach(function (pair) {
    var button = el("button", { type: "button", "data-act": pair[0] }, pair[1]);
    bar.appendChild(button);
  });

  function placeBar(target) {
    var box = target.getBoundingClientRect();
    bar.style.top = window.scrollY + box.bottom + 8 + "px";
    bar.style.left = Math.max(8, Math.min(window.scrollX + box.left, window.scrollX + innerWidth - 320)) + "px";
  }

  function startEdit(target) {
    if (editing) return;
    editing = { node: target, html: target.innerHTML, hidden: target.classList.contains("sx--hidden") };
    if (editing.hidden) target.textContent = "";
    target.classList.add("is-editing");
    try {
      target.contentEditable = "plaintext-only";
    } catch (e) {
      target.contentEditable = "true";
    }
    if (target.contentEditable !== "plaintext-only") target.contentEditable = "true";
    target.focus();
    var range = document.createRange();
    range.selectNodeContents(target);
    var selection = window.getSelection();
    selection.removeAllRanges();
    selection.addRange(range);
    document.body.appendChild(bar);
    placeBar(target);
  }

  function stopEdit(restore) {
    if (!editing) return;
    var node = editing.node;
    node.contentEditable = "false";
    node.classList.remove("is-editing");
    if (restore) node.innerHTML = editing.html;
    if (bar.parentNode) bar.parentNode.removeChild(bar);
    editing = null;
  }

  function act(action) {
    if (!editing) return;
    var node = editing.node;
    var key = node.getAttribute("data-text");
    var path = "texts/" + encodeURIComponent(key) + "/";
    if (action === "cancel") return stopEdit(true);
    var job;
    if (action === "reset") job = request("DELETE", path);
    else if (action === "hide") job = request("PUT", path, { value: "" });
    else job = request("PUT", path, { value: node.innerText.replace(/ /g, " ").trim() });
    job
      .then(function () {
        stopEdit(false);
        location.reload();
      })
      .catch(fail);
  }

  bar.addEventListener("mousedown", function (event) {
    event.preventDefault(); // фокус остаётся в тексте
  });
  bar.addEventListener("click", function (event) {
    var button = event.target.closest("button[data-act]");
    if (button) act(button.getAttribute("data-act"));
  });

  document.addEventListener("dblclick", function (event) {
    var target = event.target.closest("[data-text]");
    if (!target) return;
    event.preventDefault();
    startEdit(target);
  });

  // Текст внутри ссылки: одно нажатие ведёт по ссылке с задержкой, двойное — правка.
  var pending = null;
  document.addEventListener(
    "click",
    function (event) {
      var text = event.target.closest("[data-text]");
      if (!text) return;
      if (text.classList.contains("is-editing")) {
        event.preventDefault();
        return;
      }
      var link = text.closest("a[href]");
      if (!link || event.detail > 1) {
        if (pending) clearTimeout(pending);
        pending = null;
        if (link) event.preventDefault();
        return;
      }
      event.preventDefault();
      var href = link.href;
      pending = setTimeout(function () {
        location.href = href;
      }, 280);
    },
    true,
  );

  document.addEventListener("keydown", function (event) {
    if (!editing) return;
    if (event.key === "Escape") {
      event.preventDefault();
      stopEdit(true);
    } else if (event.key === "Enter" && !event.shiftKey && !editing.node.hasAttribute("data-multiline")) {
      event.preventDefault();
      act("save");
    }
  });

  // --- Блоки разделов ---

  var KINDS = [
    ["telegram", "Telegram (@имя или ссылка t.me)"],
    ["whatsapp", "WhatsApp (номер телефона)"],
    ["vk", "ВКонтакте (имя или ссылка)"],
    ["phone", "Телефон"],
    ["email", "Почта"],
  ];

  // Раздел ещё не меняли (значения по умолчанию, контакты из .env): сначала переносим в БД.
  function blockIds(container) {
    var area = container.getAttribute("data-blocks");
    if (container.getAttribute("data-customized") === "1") {
      return Promise.resolve(null);
    }
    return request("POST", "blocks/customize/", { area: area }).then(function (list) {
      container.setAttribute("data-customized", "1");
      return list.map(function (block) {
        return block.id;
      });
    });
  }

  function idOf(item, ids) {
    if (item.hasAttribute("data-block-id")) return Promise.resolve(item.getAttribute("data-block-id"));
    var index = parseInt(item.getAttribute("data-block-index"), 10);
    return Promise.resolve(ids ? ids[index] : null);
  }

  function field(form, label, name, value, options) {
    var wrap = el("label", { class: "bx-field" }, label);
    var input;
    if (options) {
      input = el("select", { name: name });
      options.forEach(function (pair) {
        var option = el("option", { value: pair[0] }, pair[1]);
        if (pair[0] === value) option.selected = true;
        input.appendChild(option);
      });
    } else {
      input = el("input", { name: name, value: value || "", autocomplete: "off" });
    }
    wrap.appendChild(input);
    form.appendChild(wrap);
    return input;
  }

  // Диалог блока: контакты — канал, значение, подпись; ссылки — название и адрес.
  function openDialog(area, values, onSubmit) {
    var dialog = el("dialog", { class: "bx-dialog" });
    var form = el("form", { method: "dialog" });
    form.appendChild(el("p", { class: "bx-title" }, values.id || values.index >= 0 ? "Изменить блок" : "Новый блок"));
    var inputs = {};
    if (area === "contacts") {
      inputs.kind = field(form, "Канал", "kind", values.kind || "telegram", KINDS);
      inputs.value = field(form, "Номер, имя или адрес", "value", values.value);
      inputs.note = field(form, "Подпись (необязательно)", "note", values.note);
    } else {
      inputs.title = field(form, "Название", "title", values.title);
      inputs.value = field(form, "Ссылка: /страница/, https://…, tel:, mailto:", "value", values.value);
    }
    var actions = el("div", { class: "bx-actions" });
    var cancel = el("button", { type: "button", class: "bx-ghost" }, "Отмена");
    var save = el("button", { type: "submit" }, "Сохранить");
    actions.appendChild(cancel);
    actions.appendChild(save);
    form.appendChild(actions);
    dialog.appendChild(form);
    document.body.appendChild(dialog);
    cancel.addEventListener("click", function () {
      dialog.close();
    });
    dialog.addEventListener("close", function () {
      dialog.remove();
    });
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var data = {};
      for (var name in inputs) data[name] = inputs[name].value.trim();
      save.disabled = true;
      onSubmit(data)
        .then(function () {
          dialog.close();
          location.reload();
        })
        .catch(function (error) {
          save.disabled = false;
          fail(error);
        });
    });
    dialog.showModal();
  }

  function itemValues(item) {
    return {
      index: parseInt(item.getAttribute("data-block-index"), 10),
      kind: item.getAttribute("data-kind") || "link",
      title: item.getAttribute("data-title") || "",
      value: item.getAttribute("data-value") || "",
      note: item.getAttribute("data-note") || "",
    };
  }

  document.querySelectorAll("[data-blocks]").forEach(function (container) {
    var area = container.getAttribute("data-blocks");
    container.classList.add("bx");
    container.querySelectorAll("[data-block-index]").forEach(function (item) {
      item.classList.add("bx-item");
      var tools = el("span", { class: "bx-tools" });
      var edit = el("button", { type: "button", "aria-label": "Изменить", title: "Изменить" }, "✎");
      var remove = el("button", { type: "button", "aria-label": "Удалить", title: "Удалить" }, "×");
      tools.appendChild(edit);
      tools.appendChild(remove);
      item.appendChild(tools);
      tools.addEventListener("click", function (event) {
        event.preventDefault();
        event.stopPropagation();
      });
      edit.addEventListener("click", function () {
        openDialog(area, itemValues(item), function (data) {
          return blockIds(container)
            .then(function (ids) {
              return idOf(item, ids);
            })
            .then(function (id) {
              return request("PATCH", "blocks/" + id + "/", data);
            });
        });
      });
      remove.addEventListener("click", function () {
        if (!window.confirm("Удалить блок с сайта?")) return;
        blockIds(container)
          .then(function (ids) {
            return idOf(item, ids);
          })
          .then(function (id) {
            return request("DELETE", "blocks/" + id + "/");
          })
          .then(function () {
            location.reload();
          })
          .catch(fail);
      });
    });
    var add = el("button", { type: "button", class: "bx-add" }, "+ Добавить");
    var host = container.tagName === "UL" ? el("li", { class: "bx-add-row" }) : container;
    if (host !== container) container.appendChild(host);
    add.addEventListener("click", function (event) {
      event.preventDefault();
      openDialog(area, { index: -1 }, function (data) {
        data.area = area;
        if (area !== "contacts") data.kind = "link";
        return request("POST", "blocks/", data);
      });
    });
    host.appendChild(add);
  });
})();
