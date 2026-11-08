import type { DeliveryMethod, OrderStatus } from "../api/orders";

/** Шаги обработки заказа для полосы прогресса: третий шаг зависит от способа доставки. */
export function orderSteps(delivery: DeliveryMethod): string[] {
  return ["Принят", "Собран", delivery === "pickup" ? "В пункте выдачи" : "В пути", "Получен"];
}

/** Номер пройденного шага (0…3); отменённый заказ — -1. */
export function stepIndex(status: OrderStatus): number {
  switch (status) {
    case "assembled":
      return 1;
    case "shipped":
    case "ready_for_pickup":
      return 2;
    case "delivered":
      return 3;
    case "cancelled":
      return -1;
    default:
      return 0;
  }
}

/** Заказ «по согласованию» ещё не принят: ни один шаг не пройден. */
export function isAwaitingAgreement(status: OrderStatus): boolean {
  return status === "awaiting_agreement";
}

/** Подпись действия «Отметить: …» — словами шагов, а не служебных статусов. */
export const MARK_LABELS: Partial<Record<OrderStatus, string>> = {
  confirmed: "принят — согласовано",
  assembled: "собран",
  shipped: "в пути",
  ready_for_pickup: "в пункте выдачи",
  delivered: "получен",
};

/** Статусы, которые администратор ставит сам (групповая обработка), в порядке процесса. */
export const ADMIN_TARGETS: OrderStatus[] = [
  "confirmed",
  "assembled",
  "shipped",
  "ready_for_pickup",
  "delivered",
  "cancelled",
];

export const TARGET_LABELS: Partial<Record<OrderStatus, string>> = {
  confirmed: "Принят (согласовано)",
  assembled: "Собран",
  shipped: "В пути (курьер)",
  ready_for_pickup: "В пункте выдачи (самовывоз)",
  delivered: "Получен",
  cancelled: "Отменён",
};
