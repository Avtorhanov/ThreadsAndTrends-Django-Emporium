import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";

type Schemas = components["schemas"];

export type CheckoutPreview = Schemas["CheckoutPreview"];
export type CheckoutInput = Schemas["CheckoutInputRequest"];
export type DeliveryOption = Schemas["DeliveryOption"];
export type OrderSummary = Schemas["OrderList"];
export type OrderDetail = Schemas["OrderDetail"];
export type OrderStatus = Schemas["OrderStatusEnum"];
export type PaymentMethod = Schemas["PaymentMethodEnum"];
export type DeliveryMethod = Schemas["DeliveryMethodEnum"];
export type OrdersPage = Schemas["PaginatedOrderListList"];

/** Ключ попытки оформления: повтор запроса с ним (обрыв сети, двойное нажатие) не создаёт
 * второй заказ. Не секрет — уникален в пределах аккаунта. */
export function newIdempotencyKey(): string {
  const random = Array.from({ length: 3 }, () =>
    Math.random().toString(36).slice(2, 10).padEnd(8, "0"),
  ).join("");
  return `m-${Date.now().toString(36)}-${random}`;
}

/** Заказы клиента. Расчёт сумм, доставка и проверки — на сервере. */
export const orderService = {
  preview(): Promise<CheckoutPreview> {
    return unwrap(api.GET("/api/v1/orders/checkout/"));
  },
  create(body: CheckoutInput, idempotencyKey: string): Promise<OrderDetail> {
    return unwrap(
      api.POST("/api/v1/orders/", {
        params: { header: { "Idempotency-Key": idempotencyKey } },
        body,
      }),
    );
  },
  list(page: number): Promise<OrdersPage> {
    return unwrap(api.GET("/api/v1/orders/", { params: { query: { page } } }));
  },
  get(number: string): Promise<OrderDetail> {
    return unwrap(api.GET("/api/v1/orders/{number}/", { params: { path: { number } } }));
  },
  cancel(number: string): Promise<OrderDetail> {
    return unwrap(
      api.POST("/api/v1/orders/{number}/cancel/", { params: { path: { number } } }),
    );
  },
};

export const PAYMENT_TITLES: Record<PaymentMethod, string> = {
  online: "Картой онлайн",
  on_delivery: "При получении",
};
