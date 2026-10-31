import { useEffect, useState } from "react";
import { Link, useSearchParams } from "react-router";

import { ApiError } from "../api/errors";
import {
  DELIVERY_LABELS,
  type DeliveryMethod,
  type OrderStatus,
  PAGE_SIZE,
  PAYMENT_LABELS,
  type PaymentMethod,
  STATUS_LABELS,
  ordersService,
} from "../api/orders";
import { OrderStatusBadge } from "../components/orders/OrderStatusBadge";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useOrders } from "../hooks/useOrders";
import { formatKopecks } from "../lib/money";
import { ADMIN_TARGETS, TARGET_LABELS } from "../lib/orderFlow";
import { Table } from "../components/Table";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

export function OrdersPage() {
  const [params, setParams] = useSearchParams();
  // ?customer=<id>&email=… — «Все заказы клиента» из «Клиентов»: все статусы, плашка с email.
  const customerId = Number(params.get("customer")) || null;
  const customerEmail = params.get("email") ?? "";
  const [search, setSearch] = useState("");
  // По умолчанию — заказы в работе: администратору важны незавершённые.
  // ?status=… задаёт начальный фильтр (ссылки со сводки).
  const [status, setStatus] = useState<OrderStatus | "" | "unfinished">(() => {
    const value = params.get("status");
    if (value && Object.prototype.hasOwnProperty.call(STATUS_LABELS, value)) {
      return value as OrderStatus;
    }
    return params.get("customer") ? "" : "unfinished";
  });
  const [payment, setPayment] = useState<PaymentMethod | "">("");
  const [delivery, setDelivery] = useState<DeliveryMethod | "">("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());

  const query = {
    search: debouncedSearch,
    status: status === "unfinished" ? ("" as const) : status,
    unfinished: status === "unfinished",
    payment,
    delivery,
    createdFrom,
    createdTo,
    customer: customerId,
    page,
  };
  const orders = useOrders(query);
  const { data, loading, error } = orders;
  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;
  const rows = data?.results ?? [];

  // Групповая обработка: выбор касается только видимых строк, фильтр или страница его сбрасывают.
  const [selected, setSelected] = useState<Set<number>>(new Set());
  const [target, setTarget] = useState<OrderStatus | "">("");
  const [bulkComment, setBulkComment] = useState("");
  const [bulkNotify, setBulkNotify] = useState(true);
  const [busy, setBusy] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [actionError, setActionError] = useState<string | null>(null);
  const queryKey = JSON.stringify(query);
  useEffect(() => setSelected(new Set()), [queryKey]);
  const allChecked = rows.length > 0 && rows.every((row) => selected.has(row.id));

  function toggle(id: number) {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }

  async function applyBulk() {
    if (!target) return;
    if (target === "cancelled" && !window.confirm(`Отменить заказы (${selected.size})? Это необратимо.`)) return;
    setBusy(true);
    setNotice(null);
    setActionError(null);
    try {
      const result = await ordersService.bulkTransition([...selected], target, bulkComment.trim(), bulkNotify);
      const skipped = result.skipped.map((row) => `${row.number} — ${row.reason.replace(/\.$/, "")}`);
      setNotice(
        `Переведено в «${TARGET_LABELS[target] ?? STATUS_LABELS[target]}»: ${result.updated.length}` +
          (skipped.length ? `. Пропущено: ${skipped.join("; ")}` : ""),
      );
      setSelected(new Set(result.skipped.map((row) => row.id)));
      setBulkComment("");
      orders.reload();
    } catch (err) {
      setActionError(
        err instanceof ApiError ? (Object.values(err.fieldErrors)[0]?.[0] ?? err.message) : "Статусы не изменены.",
      );
    } finally {
      setBusy(false);
    }
  }

  /** Любой фильтр возвращает на первую страницу. */
  function filter<T>(setter: (value: T) => void) {
    return (value: T) => {
      setter(value);
      setPage(1);
    };
  }

  return (
    <section>
      <div className="page-header">
        <h1>Заказы</h1>
        {data ? <span className="muted">Найдено: {data.count}</span> : null}
      </div>

      {customerId ? (
        <p className="filter-chip">
          Заказы клиента: <strong>{customerEmail || `№ ${customerId}`}</strong>
          <button
            type="button"
            className="filter-chip-clear"
            aria-label="Показать заказы всех клиентов"
            onClick={() => {
              setParams({}, { replace: true });
              setPage(1);
            }}
          >
            ×
          </button>
        </p>
      ) : null}

      <div className="filters">
        <input
          type="search"
          placeholder="Номер, email, имя или телефон"
          value={search}
          onChange={(event) => filter(setSearch)(event.target.value)}
        />
        <select
          value={status}
          onChange={(event) => filter(setStatus)(event.target.value as typeof status)}
        >
          <option value="unfinished">В работе</option>
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={delivery}
          onChange={(event) => filter(setDelivery)(event.target.value as DeliveryMethod | "")}
        >
          <option value="">Любая доставка</option>
          {Object.entries(DELIVERY_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select
          value={payment}
          onChange={(event) => filter(setPayment)(event.target.value as PaymentMethod | "")}
        >
          <option value="">Любая оплата</option>
          {Object.entries(PAYMENT_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        {/* Период — одним блоком: «с» и «по» не разъезжаются по строкам. */}
        <span className="date-range">
          <label className="date-filter">
            с
            <input
              type="date"
              value={createdFrom}
              onChange={(event) => filter(setCreatedFrom)(event.target.value)}
            />
          </label>
          <label className="date-filter">
            по
            <input
              type="date"
              value={createdTo}
              onChange={(event) => filter(setCreatedTo)(event.target.value)}
            />
          </label>
        </span>
      </div>

      {error ? <p className="alert">{error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {notice ? <p className="note note-success">{notice}</p> : null}

      {selected.size > 0 ? (
        <div className="bulk-bar" role="region" aria-label="Обработка отмеченных заказов">
          <strong>Выбрано: {selected.size}</strong>
          <button type="button" className="bulk-link" onClick={() => setSelected(new Set())}>
            Снять выбор
          </button>
          <span className="bulk-gap" />
          <label className="bulk-field">
            Отметить
            <select value={target} onChange={(event) => setTarget(event.target.value as OrderStatus | "")}>
              <option value="">Выберите…</option>
              {ADMIN_TARGETS.map((value) => (
                <option key={value} value={value}>
                  {TARGET_LABELS[value]}
                </option>
              ))}
            </select>
          </label>
          <input
            className="bulk-comment"
            type="text"
            maxLength={500}
            placeholder="Комментарий для покупателей"
            aria-label="Комментарий для покупателей"
            value={bulkComment}
            onChange={(event) => setBulkComment(event.target.value)}
          />
          <label className="bulk-field">
            <input type="checkbox" checked={bulkNotify} onChange={(event) => setBulkNotify(event.target.checked)} />
            Письма
          </label>
          <button
            type="button"
            className={target === "cancelled" ? "button button-danger-solid" : "button button-accent"}
            disabled={busy || !target}
            onClick={() => void applyBulk()}
          >
            Применить
          </button>
        </div>
      ) : null}

      <Table loading={loading}>
        <thead>
          <tr>
            <th className="check-cell">
              <input
                type="checkbox"
                aria-label="Отметить все на странице"
                checked={allChecked}
                onChange={() => setSelected(allChecked ? new Set() : new Set(rows.map((row) => row.id)))}
              />
            </th>
            <th>Номер</th>
            <th>Дата</th>
            <th>Статус</th>
            <th>Получатель</th>
            <th>Доставка / оплата</th>
            <th className="num">Сумма</th>
          </tr>
        </thead>
        <tbody>
          {rows.map((order) => (
            <tr key={order.id} className={selected.has(order.id) ? "is-selected" : undefined}>
              <td className="check-cell">
                <input
                  type="checkbox"
                  aria-label={`Отметить заказ ${order.number}`}
                  checked={selected.has(order.id)}
                  onChange={() => toggle(order.id)}
                />
              </td>
              <td>
                <Link to={`/orders/${order.id}`}>{order.number}</Link>
              </td>
              <td>{dateFormat.format(new Date(order.created_at))}</td>
              <td>
                <OrderStatusBadge status={order.status} label={order.status_display} />
              </td>
              <td>
                {order.recipient_name || "—"}
                <div className="muted small">
                  {order.recipient_phone || order.customer.email}
                </div>
              </td>
              <td>
                {DELIVERY_LABELS[order.delivery_method]}
                <div className="muted small">{PAYMENT_LABELS[order.payment_method]}</div>
              </td>
              <td className="num">
                {formatKopecks(order.total_kopecks)}
                <div className="muted small">{order.items_count} шт.</div>
              </td>
            </tr>
          ))}
          {data && rows.length === 0 ? (
            <tr>
              <td colSpan={7} className="empty">
                Заказов не найдено
              </td>
            </tr>
          ) : null}
        </tbody>
      </Table>

      <div className="pagination">
        <button
          type="button"
          className="button button-ghost"
          disabled={page <= 1 || loading}
          onClick={() => setPage((p) => p - 1)}
        >
          ← Назад
        </button>
        <span className="muted">
          Страница {page} из {pages}
        </span>
        <button
          type="button"
          className="button button-ghost"
          disabled={!data?.next || loading}
          onClick={() => setPage((p) => p + 1)}
        >
          Вперёд →
        </button>
      </div>
    </section>
  );
}
