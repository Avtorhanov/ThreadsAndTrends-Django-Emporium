import { type ReactNode, useState } from "react";
import { Link } from "react-router";

import type { AdminSummary } from "../api/summary";
import { Icon, type IconName } from "../components/Icon";
import { OrderStatusBadge } from "../components/orders/OrderStatusBadge";
import { PageTools, ToolButton } from "../components/PageTools";
import { useOrders } from "../hooks/useOrders";
import { useSummary } from "../hooks/useSummary";
import { formatKopecks } from "../lib/money";
import {
  type SummaryLayout,
  type WidgetId,
  type WidgetSize,
  WIDGETS,
  defaultLayout,
  loadLayout,
  saveLayout,
} from "./summaryLayout";

const dayFormat = new Intl.DateTimeFormat("ru-RU", { weekday: "long", day: "numeric", month: "long" });
const dateFormat = new Intl.DateTimeFormat("ru-RU", { day: "numeric", month: "short", hour: "2-digit", minute: "2-digit" });

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

const SIZE_LABEL: Record<WidgetSize, string> = { s: "S", m: "M", l: "L" };
const SIZE_HINT: Record<WidgetSize, string> = { s: "Маленький", m: "Средний", l: "Во всю ширину" };

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

/** Целые рубли без копеек для крупных цифр сводки (копейки — в «Обороте» по строкам). */
function rublesShort(kopecks: number): string {
  return `${new Intl.NumberFormat("ru-RU").format(Math.round(kopecks / 100))} ₽`;
}

/** Плитка очереди: число, подпись, иконка; ведёт в заказы. */
function QueueTile({ to, icon, label, value, note, alert }: {
  to: string;
  icon: IconName;
  label: string;
  value: number;
  note: string;
  alert?: boolean;
}) {
  return (
    <Link to={to} className={alert && value > 0 ? "dash-tile is-alert" : "dash-tile"}>
      <span className="dash-tile-icon" aria-hidden="true">
        <Icon name={icon} size={20} />
      </span>
      <span className="dash-tile-value">{value}</span>
      <span className="dash-tile-label">{label}</span>
      <span className="dash-tile-note">{note}</span>
    </Link>
  );
}

function TodayWidget({ data }: { data: AdminSummary }) {
  // Средний день недели — с чем сравнивать сегодняшний оборот.
  const weekAvg = Math.round(data.last_7_days.turnover_kopecks / 7);
  const share = weekAvg > 0 ? Math.min(100, Math.round((data.today.turnover_kopecks / weekAvg) * 100)) : 0;
  return (
    <div className="dash-hero">
      <span className="dash-hero-label">Сегодня</span>
      <span className="dash-hero-value">{rublesShort(data.today.turnover_kopecks)}</span>
      <span className="dash-hero-note">{ordersText(data.today.orders)}</span>
      <span className="dash-meter" aria-hidden="true">
        <span style={{ width: `${share}%` }} />
      </span>
      <span className="dash-hero-note">
        {weekAvg > 0 ? `${share}% от среднего дня недели (${rublesShort(weekAvg)})` : "За неделю продаж ещё не было"}
      </span>
    </div>
  );
}

function TurnoverWidget({ data }: { data: AdminSummary }) {
  const rows = [
    { label: "Сегодня", value: data.today },
    { label: "7 дней", value: data.last_7_days },
    { label: "30 дней", value: data.last_30_days },
  ];
  const max = Math.max(1, ...rows.map((row) => row.value.turnover_kopecks));
  return (
    <div className="dash-card">
      <div className="dash-card-head">
        <h2>Оборот</h2>
      </div>
      <ul className="dash-bars">
        {rows.map((row) => (
          <li key={row.label}>
            <span className="dash-bars-label">
              {row.label}
              <span className="muted small">{ordersText(row.value.orders)}</span>
            </span>
            <span className="dash-bars-track" aria-hidden="true">
              <span style={{ width: `${Math.max(2, Math.round((row.value.turnover_kopecks / max) * 100))}%` }} />
            </span>
            <span className="dash-bars-value">{formatKopecks(row.value.turnover_kopecks)}</span>
          </li>
        ))}
      </ul>
      <p className="muted small dash-note">
        Без отменённых и ждущих онлайн-оплаты; оплата при получении — сразу после оформления.
      </p>
    </div>
  );
}

function RecentWidget() {
  const recent = useOrders(RECENT_QUERY);
  return (
    <div className="dash-card">
      <div className="dash-card-head">
        <h2>Заказы в работе</h2>
        <Link className="dash-more" to="/orders">
          Все <Icon name="right" size={14} />
        </Link>
      </div>
      {recent.error ? <p className="alert">{recent.error}</p> : null}
      {recent.data && recent.data.results.length === 0 ? <p className="muted">Незавершённых заказов нет.</p> : null}
      <ul className="dash-list">
        {recent.data?.results.slice(0, RECENT_LIMIT).map((order) => (
          <li key={order.id}>
            <Link to={`/orders/${order.id}`} className="dash-row">
              <span className="dash-row-main">
                <strong>{order.number}</strong>
                <span className="muted small">
                  {dateFormat.format(new Date(order.created_at))} · {order.recipient_name || order.customer?.email || "Гость"}
                </span>
              </span>
              <span className="dash-row-end">
                <OrderStatusBadge status={order.status} label={order.status_display} />
                <span className="small strong">{formatKopecks(order.total_kopecks)}</span>
              </span>
            </Link>
          </li>
        ))}
      </ul>
    </div>
  );
}

function StockWidget({ data }: { data: AdminSummary }) {
  return (
    <div className="dash-card">
      <div className="dash-card-head">
        <h2>Мало на складе</h2>
        <span className="muted small">остаток ≤ {data.low_stock_threshold}</span>
      </div>
      {data.low_stock.length === 0 ? (
        <p className="muted">Все остатки выше порога.</p>
      ) : (
        <ul className="dash-list">
          {data.low_stock.map((row) => (
            <li key={row.sku}>
              <Link to={`/catalog/products/${row.product_id}`} className="dash-row">
                <span className="dash-row-main">
                  <strong>{row.product_name}</strong>
                  <span className="muted small">
                    {row.size ? `Размер ${row.size} · ` : ""}
                    {row.sku}
                  </span>
                </span>
                <span className={row.stock === 0 ? "badge badge-danger" : "badge badge-warning"}>
                  {row.stock === 0 ? "Нет" : `${row.stock} шт.`}
                </span>
              </Link>
            </li>
          ))}
        </ul>
      )}
      {data.low_stock_count > data.low_stock.length ? (
        <p className="muted small dash-note">
          И ещё {data.low_stock_count - data.low_stock.length} — в разделе <Link to="/catalog/products">Товары</Link>.
        </p>
      ) : null}
    </div>
  );
}

function renderWidget(id: WidgetId, data: AdminSummary): ReactNode {
  switch (id) {
    case "today":
      return <TodayWidget data={data} />;
    case "agreement":
      return (
        <QueueTile
          to="/orders?status=awaiting_agreement"
          icon="orders"
          label="Ждут согласования"
          value={data.awaiting_agreement}
          note="договоритесь в мессенджере"
          alert
        />
      );
    case "awaiting":
      return (
        <QueueTile
          to="/orders?status=awaiting_payment"
          icon="orders"
          label="Ждут оплаты"
          value={data.awaiting_payment}
          note="онлайн-оплата не пришла"
          alert
        />
      );
    case "assemble":
      return (
        <QueueTile to="/orders" icon="products" label="Собрать" value={data.to_assemble} note="приняты или оплачены" />
      );
    case "deliver":
      return (
        <QueueTile to="/orders" icon="arrow" label="Доставить" value={data.to_deliver} note="собраны, в пути, в пункте выдачи" />
      );
    case "turnover":
      return <TurnoverWidget data={data} />;
    case "recent":
      return <RecentWidget />;
    case "stock":
      return <StockWidget data={data} />;
  }
}

/**
 * Главная панели: что требует внимания сейчас и как идут продажи. Блоки можно переставлять и
 * менять им размер («Настроить»); раскладка — личная, в этом браузере (summaryLayout).
 */
export function SummaryPage() {
  const summary = useSummary();
  const data = summary.data;
  const [layout, setLayout] = useState<SummaryLayout>(loadLayout);
  const [editing, setEditing] = useState(false);

  function update(next: SummaryLayout) {
    setLayout(next);
    saveLayout(next);
  }

  function move(id: WidgetId, delta: number) {
    const order = [...layout.order];
    const from = order.indexOf(id);
    const to = from + delta;
    if (from < 0 || to < 0 || to >= order.length) return;
    order.splice(from, 1);
    order.splice(to, 0, id);
    update({ ...layout, order });
  }

  return (
    <section className="stack">
      <div className="page-header">
        <div>
          <p className="eyebrow">{dayFormat.format(new Date())}</p>
          <h1>Сводка</h1>
        </div>
        <PageTools>
          {editing ? (
            <ToolButton icon="undo" label="Как было" onClick={() => update(defaultLayout())} />
          ) : null}
          <ToolButton
            icon={editing ? "check" : "settings"}
            label={editing ? "Готово" : "Настроить"}
            tone={editing ? "accent" : undefined}
            onClick={() => setEditing((value) => !value)}
          />
        </PageTools>
      </div>

      {editing ? (
        <p className="note note-info small">
          Стрелки — переставить блок, S · M · L — размер. Раскладка сохраняется в этом браузере.
        </p>
      ) : null}
      {summary.error ? <p className="alert">{summary.error}</p> : null}
      {summary.loading ? <p className="muted">Загрузка…</p> : null}

      {data ? (
        <div className={editing ? "dash is-editing" : "dash"}>
          {layout.order.map((id, index) => {
            const widget = WIDGETS[id];
            const size = layout.size[id];
            return (
              <div key={id} className={`dash-cell dash-${size}`}>
                {editing ? (
                  <div className="dash-edit" role="group" aria-label={`Блок «${widget.title}»`}>
                    <button
                      type="button"
                      aria-label={`«${widget.title}» раньше`}
                      disabled={index === 0}
                      onClick={() => move(id, -1)}
                    >
                      <Icon name="left" size={16} />
                    </button>
                    <span className="dash-edit-title">{widget.title}</span>
                    {widget.sizes.map((option) => (
                      <button
                        key={option}
                        type="button"
                        className={option === size ? "is-on" : undefined}
                        aria-pressed={option === size}
                        title={SIZE_HINT[option]}
                        onClick={() => update({ ...layout, size: { ...layout.size, [id]: option } })}
                      >
                        {SIZE_LABEL[option]}
                      </button>
                    ))}
                    <button
                      type="button"
                      aria-label={`«${widget.title}» позже`}
                      disabled={index === layout.order.length - 1}
                      onClick={() => move(id, 1)}
                    >
                      <Icon name="right" size={16} />
                    </button>
                  </div>
                ) : null}
                {renderWidget(id, data)}
              </div>
            );
          })}
        </div>
      ) : null}
    </section>
  );
}
