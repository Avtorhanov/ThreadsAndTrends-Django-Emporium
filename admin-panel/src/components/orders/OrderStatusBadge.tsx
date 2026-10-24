import type { OrderStatus } from "../../api/orders";

// Цвета статусов — решение дизайна «Лайм-тек» (сессия 8): ожидает оплаты — warning,
// принят/оплачен/собран — tag, в пути/готов к выдаче — info, получен — success, отменён — neutral.
const TONE: Record<OrderStatus, string> = {
  awaiting_payment: "warning",
  confirmed: "tag",
  paid: "tag",
  assembled: "tag",
  shipped: "info",
  ready_for_pickup: "info",
  delivered: "success",
  cancelled: "neutral",
};

export function OrderStatusBadge({ status, label }: { status: OrderStatus; label: string }) {
  return <span className={`badge badge-${TONE[status]}`}>{label}</span>;
}
