import { useState } from "react";
import { Link, useParams } from "react-router";

import { ApiError } from "../api/errors";
import { type AdminOrderDetail, type OrderStatus, ordersService } from "../api/orders";
import { OrderStatusBadge } from "../components/orders/OrderStatusBadge";
import { PaymentsCard } from "../components/orders/PaymentsCard";
import { useOrder } from "../hooks/useOrders";
import { formatKopecks } from "../lib/money";

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

const CHANGED_BY: Record<string, string> = {
  customer: "клиент",
  admin: "администратор",
  system: "система",
};

// Переходы, которые нельзя откатить, подтверждаются.
const CONFIRM: Partial<Record<OrderStatus, string>> = {
  cancelled: "Отменить заказ? Остатки вернутся на склад; оплаченный заказ уйдёт на возврат денег.",
  delivered: "Отметить заказ как полученный клиентом? Статус станет окончательным.",
};

export function OrderDetailPage() {
  const params = useParams();
  const orderId = params.id && /^\d+$/.test(params.id) ? Number(params.id) : null;
  const order = useOrder(orderId);
  const [busy, setBusy] = useState(false);
  const [actionError, setActionError] = useState<string | null>(null);

  async function run(action: (id: number) => Promise<AdminOrderDetail>, fallback: string) {
    if (orderId === null) return;
    setBusy(true);
    setActionError(null);
    try {
      order.set(await action(orderId));
    } catch (err) {
      setActionError(err instanceof ApiError ? err.message : fallback);
      order.reload(); // заказ мог измениться с другого устройства
    } finally {
      setBusy(false);
    }
  }

  function move(status: OrderStatus) {
    const question = CONFIRM[status];
    if (question && !window.confirm(question)) return;
    void run((id) => ordersService.transition(id, status), "Статус не изменён.");
  }

  function retryRefund() {
    if (!window.confirm("Отправить возврат денег покупателю ещё раз?")) return;
    void run((id) => ordersService.refund(id), "Возврат не отправлен.");
  }

  const data = order.data;

  return (
    <section className="stack">
      <div className="page-header">
        <Link to="/orders" className="muted">
          ← Заказы
        </Link>
        <h1>{data ? `Заказ ${data.number}` : "Заказ"}</h1>
        {data ? <OrderStatusBadge status={data.status} label={data.status_display} /> : null}
      </div>

      {order.error ? <p className="alert">{order.error}</p> : null}
      {actionError ? <p className="alert">{actionError}</p> : null}
      {order.loading && !data ? <p className="muted">Загрузка…</p> : null}

      {data ? (
        <>
          <div className="card">
            <h2>Статус</h2>
            {data.allowed_transitions.length > 0 ? (
              <div className="transitions">
                {data.allowed_transitions.map((option) => (
                  <button
                    key={option.status}
                    type="button"
                    className={
                      option.status === "cancelled" ? "button button-danger" : "button"
                    }
                    disabled={busy}
                    onClick={() => move(option.status)}
                  >
                    {option.status === "cancelled" ? "Отменить заказ" : `→ ${option.label}`}
                  </button>
                ))}
              </div>
            ) : (
              <p className="muted">Статус окончательный.</p>
            )}
          </div>

          {data.payment_method === "online" ? (
            <PaymentsCard
              payments={data.payments}
              canRetryRefund={data.can_retry_refund}
              busy={busy}
              onRetryRefund={retryRefund}
              onSync={() => void run((id) => ordersService.syncPayment(id), "Не удалось проверить.")}
            />
          ) : null}

          <div className="order-grid">
            <div className="card">
              <h2>Получатель</h2>
              <dl className="details">
                <dt>Имя</dt>
                <dd>{data.recipient_name || "—"}</dd>
                <dt>Телефон</dt>
                <dd>
                  {data.recipient_phone ? (
                    <a href={`tel:${data.recipient_phone}`}>{data.recipient_phone}</a>
                  ) : (
                    "—"
                  )}
                </dd>
                <dt>Клиент</dt>
                <dd>
                  {data.customer.email}
                  {data.customer.is_deleted ? " (аккаунт удалён)" : ""}
                </dd>
                <dt>{data.delivery_method_display}</dt>
                <dd>{data.delivery_address || "—"}</dd>
                <dt>Оплата</dt>
                <dd>{data.payment_method_display}</dd>
                {data.comment ? (
                  <>
                    <dt>Комментарий</dt>
                    <dd>{data.comment}</dd>
                  </>
                ) : null}
              </dl>
            </div>

            <div className="card">
              <h2>История</h2>
              <ul className="history">
                {data.status_history.map((change, index) => (
                  <li key={`${change.created_at}-${index}`}>
                    <strong>{change.to_status_display}</strong>
                    <span className="muted small">
                      {dateFormat.format(new Date(change.created_at))} ·{" "}
                      {CHANGED_BY[change.changed_by] ?? change.changed_by}
                      {change.actor_email && change.changed_by === "admin"
                        ? ` (${change.actor_email})`
                        : ""}
                    </span>
                  </li>
                ))}
              </ul>
            </div>
          </div>

          <div className="table-wrap">
            <table className="table">
              <thead>
                <tr>
                  <th>Товар</th>
                  <th>Размер</th>
                  <th>Артикул</th>
                  <th className="num">Цена</th>
                  <th className="num">Кол-во</th>
                  <th className="num">Сумма</th>
                </tr>
              </thead>
              <tbody>
                {data.items.map((item) => (
                  <tr key={item.id}>
                    <td>{item.product_name}</td>
                    <td>{item.size || "—"}</td>
                    <td>{item.sku}</td>
                    <td className="num">{formatKopecks(item.price_kopecks)}</td>
                    <td className="num">{item.quantity}</td>
                    <td className="num">{formatKopecks(item.line_total_kopecks)}</td>
                  </tr>
                ))}
                <tr>
                  <td colSpan={5} className="num muted">
                    Товары
                  </td>
                  <td className="num">{formatKopecks(data.items_total_kopecks)}</td>
                </tr>
                <tr>
                  <td colSpan={5} className="num muted">
                    Доставка
                  </td>
                  <td className="num">
                    {data.delivery_kopecks ? formatKopecks(data.delivery_kopecks) : "бесплатно"}
                  </td>
                </tr>
                <tr>
                  <td colSpan={5} className="num">
                    <strong>Итого</strong>
                  </td>
                  <td className="num">
                    <strong>{formatKopecks(data.total_kopecks)}</strong>
                  </td>
                </tr>
              </tbody>
            </table>
          </div>
          <p className="muted small">
            Оформлен {dateFormat.format(new Date(data.created_at))}, изменён{" "}
            {dateFormat.format(new Date(data.updated_at))}
          </p>
        </>
      ) : null}
    </section>
  );
}
