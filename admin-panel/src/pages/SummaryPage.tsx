import { Link } from "react-router";

import { OrderStatusBadge } from "../components/orders/OrderStatusBadge";
import { useOrders } from "../hooks/useOrders";
import { useSummary } from "../hooks/useSummary";
import { formatKopecks } from "../lib/money";

const dayFormat = new Intl.DateTimeFormat("ru-RU", {
  weekday: "long",
  day: "numeric",
  month: "long",
});
const dateFormat = new Intl.DateTimeFormat("ru-RU", { dateStyle: "short", timeStyle: "short" });

const RECENT_QUERY = {
  search: "",
  status: "",
  unfinished: true,
  payment: "",
  delivery: "",
  createdFrom: "",
  createdTo: "",
  page: 1,
} as const;
const RECENT_LIMIT = 6;

function plural(n: number, one: string, few: string, many: string): string {
  const mod10 = n % 10;
  const mod100 = n % 100;
  if (mod10 === 1 && mod100 !== 11) return one;
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) return few;
  return many;
}

function ordersText(n: number): string {
  return `${n} ${plural(n, "заказ", "заказа", "заказов")}`;
}

/** Главная панели: что требует внимания сейчас и как идут продажи. */
export function SummaryPage() {
  const summary = useSummary();
  const recent = useOrders(RECENT_QUERY);
  const data = summary.data;

  return (
    <section className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">{dayFormat.format(new Date())}</p>
          <h1>Сводка</h1>
        </div>
      </div>

      {summary.error ? <p className="alert">{summary.error}</p> : null}
      {summary.loading ? <p className="muted">Загрузка…</p> : null}

      {data ? (
        <div className="stats">
          <div className="stat stat-accent">
            <span className="stat-label">Сегодня</span>
            <span className="stat-value">{formatKopecks(data.today.turnover_kopecks)}</span>
            <span className="small muted">{ordersText(data.today.orders)}</span>
          </div>
          <Link
            to="/orders?status=awaiting_payment"
            className={data.awaiting_payment > 0 ? "stat stat-warning" : "stat"}
          >
            <span className="stat-label">Ждут оплаты</span>
            <span className="stat-value">{data.awaiting_payment}</span>
            <span className="small muted">онлайн-оплата не пришла</span>
          </Link>
          <Link to="/orders" className="stat">
            <span className="stat-label">Собрать</span>
            <span className="stat-value">{data.to_assemble}</span>
            <span className="small muted">приняты или оплачены</span>
          </Link>
          <Link to="/orders" className="stat">
            <span className="stat-label">Доставить</span>
            <span className="stat-value">{data.to_deliver}</span>
            <span className="small muted">собраны, в пути, в пункте выдачи</span>
          </Link>
        </div>
      ) : null}

      <div className="summary-grid">
        <div className="card">
          <div className="card-header">
            <h2>Заказы в работе</h2>
            <Link to="/orders">Все →</Link>
          </div>
          {recent.error ? <p className="alert">{recent.error}</p> : null}
          {recent.data && recent.data.results.length === 0 ? (
            <p className="muted">Незавершённых заказов нет.</p>
          ) : null}
          <ul className="list">
            {recent.data?.results.slice(0, RECENT_LIMIT).map((order) => (
              <li key={order.id}>
                <div>
                  <Link to={`/orders/${order.id}`}>{order.number}</Link>
                  <div className="muted small">
                    {dateFormat.format(new Date(order.created_at))} ·{" "}
                    {order.recipient_name || order.customer.email}
                  </div>
                </div>
                <div className="list-end">
                  <OrderStatusBadge status={order.status} label={order.status_display} />
                  <span className="small strong">{formatKopecks(order.total_kopecks)}</span>
                </div>
              </li>
            ))}
          </ul>
        </div>

        {data ? (
          <div className="card">
            <div className="card-header">
              <h2>Оборот</h2>
            </div>
            <ul className="list">
              <li>
                <div>
                  Сегодня
                  <div className="muted small">{ordersText(data.today.orders)}</div>
                </div>
                <span className="strong">{formatKopecks(data.today.turnover_kopecks)}</span>
              </li>
              <li>
                <div>
                  7 дней
                  <div className="muted small">{ordersText(data.last_7_days.orders)}</div>
                </div>
                <span className="strong">{formatKopecks(data.last_7_days.turnover_kopecks)}</span>
              </li>
              <li>
                <div>
                  30 дней
                  <div className="muted small">{ordersText(data.last_30_days.orders)}</div>
                </div>
                <span className="strong">{formatKopecks(data.last_30_days.turnover_kopecks)}</span>
              </li>
            </ul>
            <p className="muted small card-note">
              Без отменённых и ждущих онлайн-оплаты; заказы с оплатой при получении — сразу после
              оформления.
            </p>
          </div>
        ) : null}

        {data ? (
          <div className="card">
            <div className="card-header">
              <h2>Мало на складе</h2>
              <span className="muted small">остаток ≤ {data.low_stock_threshold}</span>
            </div>
            {data.low_stock.length === 0 ? (
              <p className="muted">Все остатки выше порога.</p>
            ) : (
              <ul className="list">
                {data.low_stock.map((row) => (
                  <li key={row.sku}>
                    <div>
                      <Link to={`/catalog/products/${row.product_id}`}>{row.product_name}</Link>
                      <div className="muted small">
                        {row.size ? `Размер ${row.size} · ` : ""}
                        {row.sku}
                      </div>
                    </div>
                    <span
                      className={row.stock === 0 ? "badge badge-danger" : "badge badge-warning"}
                    >
                      {row.stock === 0 ? "Нет" : `${row.stock} шт.`}
                    </span>
                  </li>
                ))}
              </ul>
            )}
            {data.low_stock_count > data.low_stock.length ? (
              <p className="muted small card-note">
                И ещё {data.low_stock_count - data.low_stock.length} — в разделе{" "}
                <Link to="/catalog/products">Товары</Link>.
              </p>
            ) : null}
          </div>
        ) : null}
      </div>
    </section>
  );
}
