import { useState } from "react";
import { Link, useSearchParams } from "react-router";

import {
  DELIVERY_LABELS,
  type DeliveryMethod,
  type OrderStatus,
  PAGE_SIZE,
  PAYMENT_LABELS,
  type PaymentMethod,
  STATUS_LABELS,
} from "../api/orders";
import { OrderStatusBadge } from "../components/orders/OrderStatusBadge";
import { useDebouncedValue } from "../hooks/useDebouncedValue";
import { useOrders } from "../hooks/useOrders";
import { formatKopecks } from "../lib/money";
import { Table } from "../components/Table";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

export function OrdersPage() {
  const [params] = useSearchParams();
  const [search, setSearch] = useState("");
  // По умолчанию — заказы в работе: администратору важны незавершённые.
  // ?status=… задаёт начальный фильтр (ссылки со сводки).
  const [status, setStatus] = useState<OrderStatus | "" | "unfinished">(() => {
    const value = params.get("status");
    if (value && Object.prototype.hasOwnProperty.call(STATUS_LABELS, value)) {
      return value as OrderStatus;
    }
    return "unfinished";
  });
  const [payment, setPayment] = useState<PaymentMethod | "">("");
  const [delivery, setDelivery] = useState<DeliveryMethod | "">("");
  const [createdFrom, setCreatedFrom] = useState("");
  const [createdTo, setCreatedTo] = useState("");
  const [page, setPage] = useState(1);
  const debouncedSearch = useDebouncedValue(search.trim());

  const { data, loading, error } = useOrders({
    search: debouncedSearch,
    status: status === "unfinished" ? "" : status,
    unfinished: status === "unfinished",
    payment,
    delivery,
    createdFrom,
    createdTo,
    page,
  });
  const pages = data ? Math.max(1, Math.ceil(data.count / PAGE_SIZE)) : 1;

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
      </div>

      {error ? <p className="alert">{error}</p> : null}

      <Table loading={loading}>
        <thead>
          <tr>
            <th>Номер</th>
            <th>Дата</th>
            <th>Статус</th>
            <th>Получатель</th>
            <th>Доставка / оплата</th>
            <th className="num">Сумма</th>
          </tr>
        </thead>
        <tbody>
          {data?.results.map((order) => (
            <tr key={order.id}>
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
          {data && data.results.length === 0 ? (
            <tr>
              <td colSpan={6} className="empty">
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
