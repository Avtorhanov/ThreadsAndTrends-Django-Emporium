import { api, unwrap } from "./client";
import type { components } from "./schema";

type Schemas = components["schemas"];

export type AdminOrder = Schemas["AdminOrderList"];
export type AdminOrderDetail = Schemas["AdminOrderDetail"];
export type AdminOrderPage = Schemas["PaginatedAdminOrderListList"];
export type OrderStatus = Schemas["OrderStatusEnum"];
export type PaymentMethod = Schemas["PaymentMethodEnum"];
export type DeliveryMethod = Schemas["DeliveryMethodEnum"];
export type AdminPayment = Schemas["AdminPayment"];
export type PaymentStatus = Schemas["PaymentStatusEnum"];
export type RefundStatus = Schemas["RefundStatusEnum"];
export type BulkTransitionResult = Schemas["AdminBulkTransitionResult"];

export type OrderQuery = {
  search: string;
  status: OrderStatus | "";
  unfinished: boolean;
  payment: PaymentMethod | "";
  delivery: DeliveryMethod | "";
  createdFrom: string;
  createdTo: string;
  page: number;
};

export const PAGE_SIZE = 20;

export const STATUS_LABELS: Record<OrderStatus, string> = {
  awaiting_payment: "Ожидает оплаты",
  confirmed: "Принят",
  paid: "Оплачен",
  assembled: "Собран",
  shipped: "Отправлен",
  ready_for_pickup: "Готов к выдаче",
  delivered: "Получен",
  cancelled: "Отменён",
};

export const PAYMENT_LABELS: Record<PaymentMethod, string> = {
  online: "Онлайн",
  on_delivery: "При получении",
};

export const DELIVERY_LABELS: Record<DeliveryMethod, string> = {
  courier: "Курьер",
  pickup: "Самовывоз",
};

export const ordersService = {
  list(query: OrderQuery): Promise<AdminOrderPage> {
    return unwrap(
      api.GET("/api/v1/admin/orders/", {
        params: {
          query: {
            search: query.search || undefined,
            status: query.status || undefined,
            unfinished: query.unfinished || undefined,
            payment_method: query.payment || undefined,
            delivery_method: query.delivery || undefined,
            created_from: query.createdFrom || undefined,
            created_to: query.createdTo || undefined,
            page: query.page,
          },
        },
      }),
    );
  },

  get(id: number): Promise<AdminOrderDetail> {
    return unwrap(api.GET("/api/v1/admin/orders/{id}/", { params: { path: { id } } }));
  },

  /** comment виден клиенту (история и письмо); notify=false — без письма. */
  transition(id: number, status: OrderStatus, comment = "", notify = true): Promise<AdminOrderDetail> {
    return unwrap(
      api.POST("/api/v1/admin/orders/{id}/transition/", {
        params: { path: { id } },
        body: { status, comment, notify },
      }),
    );
  },

  /** Групповая смена статуса: неподходящие заказы возвращаются в skipped с причиной. */
  bulkTransition(ids: number[], status: OrderStatus, comment = "", notify = true): Promise<BulkTransitionResult> {
    return unwrap(
      api.POST("/api/v1/admin/orders/bulk-transition/", { body: { ids, status, comment, notify } }),
    );
  },

  /** Повторить возврат после отказа провайдера. */
  refund(id: number): Promise<AdminOrderDetail> {
    return unwrap(api.POST("/api/v1/admin/orders/{id}/refund/", { params: { path: { id } } }));
  },

  /** Сверить незавершённые платежи с провайдером (если уведомление не дошло). */
  syncPayment(id: number): Promise<AdminOrderDetail> {
    return unwrap(
      api.POST("/api/v1/admin/orders/{id}/payment-sync/", { params: { path: { id } } }),
    );
  },
};
