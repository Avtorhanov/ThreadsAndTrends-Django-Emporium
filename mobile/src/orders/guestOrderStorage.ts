import * as SecureStore from "expo-secure-store";

import { guestOrderService } from "./orderService";

export type GuestOrderRef = { number: string; token: string };

const KEY = "didi.guest_orders.v1";
// Значение SecureStore ограничено ~2 КБ: одна запись ~90 байт.
const MAX_ORDERS = 15;

async function read(): Promise<GuestOrderRef[]> {
  try {
    const parsed: unknown = JSON.parse((await SecureStore.getItemAsync(KEY)) ?? "[]");
    return Array.isArray(parsed) ? (parsed as GuestOrderRef[]) : [];
  } catch {
    return [];
  }
}

/** Заказы, оформленные на устройстве без аккаунта. Токен — как пароль, поэтому в SecureStore. */
export const guestOrderStorage = {
  list: read,
  async tokenFor(number: string): Promise<string | null> {
    return (await read()).find((item) => item.number === number)?.token ?? null;
  },
  async add(number: string, token: string): Promise<void> {
    const rest = (await read()).filter((item) => item.number !== number);
    await SecureStore.setItemAsync(
      KEY,
      JSON.stringify([{ number, token }, ...rest].slice(0, MAX_ORDERS)),
    );
  },
  clear: () => SecureStore.deleteItemAsync(KEY),
};

/** После входа: заказы с устройства — в аккаунт. При ошибке сети токены остаются до следующего входа. */
export async function claimGuestOrders(): Promise<void> {
  const items = await read();
  if (items.length === 0) return;
  try {
    await guestOrderService.claim(items.map((item) => item.token));
    await guestOrderStorage.clear();
  } catch {
    // повторим при следующем запуске
  }
}
