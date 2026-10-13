import type { OrderStatus } from "../../api/orders";

const TONE: Record<OrderStatus, string> = {
  awaiting_payment: "warn",
  confirmed: "new",
  paid: "new",
  assembled: "progress",
  shipped: "progress",
  ready_for_pickup: "progress",
  delivered: "active",
  cancelled: "deleted",
};

export function OrderStatusBadge({ status, label }: { status: OrderStatus; label: string }) {
  return <span className={`badge badge-${TONE[status]}`}>{label}</span>;
}
