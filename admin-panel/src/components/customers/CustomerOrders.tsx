import { useEffect, useState } from "react";
import { Link } from "react-router";

import { ApiError } from "../../api/errors";
import { type AdminOrderPage, ordersService } from "../../api/orders";
import { formatKopecks } from "../../lib/money";
import { OrderStatusBadge } from "../orders/OrderStatusBadge";

/** Сколько последних заказов показать на карточке клиента; остальные — в «Заказах». */
export const CUSTOMER_ORDERS_PREVIEW = 5;

const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short" });

type State = { data: AdminOrderPage | null; error: string | null };

/** Последние заказы клиента (раскрываются кнопкой «Заказы · N» в «Клиентах»). */
export function CustomerOrders({ customerId, email }: { customerId: number; email: string }) {
  const [state, setState] = useState<State>({ data: null, error: null });

  useEffect(() => {
    let cancelled = false;
    ordersService
      .list({
        search: "",
        status: "",
        unfinished: false,
        payment: "",
        delivery: "",
        createdFrom: "",
        createdTo: "",
        customer: customerId,
        page: 1,
      })
      .then((data) => {
        if (!cancelled) setState({ data, error: null });
      })
      .catch((error: unknown) => {
        if (cancelled) return;
        setState({
          data: null,
          error: error instanceof ApiError ? error.message : "Не удалось загрузить заказы.",
        });
      });
    return () => {
      cancelled = true;
    };
  }, [customerId]);

  if (state.error) return <p className="alert">{state.error}</p>;
  if (!state.data) return <p className="muted small">Загрузка…</p>;

  const rows = state.data.results.slice(0, CUSTOMER_ORDERS_PREVIEW);
  const more = state.data.count - rows.length;
  return (
    <div className="customer-orders">
      {rows.length ? (
        <ul className="customer-orders-list">
          {rows.map((order) => (
            <li key={order.id}>
              <Link className="customer-order" to={`/orders/${order.id}`}>
                <span className="customer-order-num">{order.number}</span>
                <span className="muted small">{dateFormat.format(new Date(order.created_at))}</span>
                <span className="customer-order-sum">{formatKopecks(order.total_kopecks)}</span>
                <OrderStatusBadge status={order.status} label={order.status_display} />
              </Link>
            </li>
          ))}
        </ul>
      ) : (
        <p className="muted small">Заказов нет.</p>
      )}
      {more > 0 ? (
        <Link
          className="customer-orders-all"
          to={`/orders?${new URLSearchParams({ customer: String(customerId), email }).toString()}`}
        >
          Все заказы клиента · {state.data.count}
        </Link>
      ) : null}
    </div>
  );
}
