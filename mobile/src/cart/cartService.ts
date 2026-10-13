import { api, unwrap } from "../api/client";
import type { components } from "../api/schema";
import type { GuestLine } from "./guestCartStorage";

type Schemas = components["schemas"];

export type Cart = Schemas["Cart"];
export type CartLine = Schemas["CartLine"];
export type CartMergeResult = Schemas["CartMergeResult"];
export type CartMergeNotice = Schemas["CartMergeNotice"];

export const EMPTY_CART: Cart = {
  items: [],
  total_kopecks: 0,
  items_count: 0,
  can_checkout: false,
  has_problems: false,
  has_price_changes: false,
};

/** Корзина на сервере (клиент) и расчёт гостевой корзины. Вся логика цен и лимитов — на сервере. */
export const cartService = {
  get(): Promise<Cart> {
    return unwrap(api.GET("/api/v1/cart/"));
  },
  add(variantId: number, quantity = 1): Promise<Cart> {
    return unwrap(api.POST("/api/v1/cart/items/", { body: { variant_id: variantId, quantity } }));
  },
  setQuantity(itemId: number, quantity: number): Promise<Cart> {
    return unwrap(
      api.PATCH("/api/v1/cart/items/{id}/", { params: { path: { id: itemId } }, body: { quantity } }),
    );
  },
  remove(itemId: number): Promise<Cart> {
    return unwrap(api.DELETE("/api/v1/cart/items/{id}/", { params: { path: { id: itemId } } }));
  },
  ackPrices(): Promise<Cart> {
    return unwrap(api.POST("/api/v1/cart/ack-prices/"));
  },
  merge(lines: GuestLine[]): Promise<CartMergeResult> {
    return unwrap(api.POST("/api/v1/cart/merge/", { body: { items: lines } }));
  },
  quote(lines: GuestLine[]): Promise<Cart> {
    if (lines.length === 0) return Promise.resolve(EMPTY_CART);
    return unwrap(api.POST("/api/v1/cart/quote/", { body: { items: lines } }));
  },
};
