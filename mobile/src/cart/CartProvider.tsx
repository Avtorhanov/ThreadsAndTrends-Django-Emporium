import {
  createContext,
  type ReactNode,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";

import { ApiError } from "../api/errors";
import { useAuth } from "../auth/AuthProvider";
import {
  type Cart,
  type CartLine,
  type CartMergeNotice,
  cartService,
  EMPTY_CART,
} from "./cartService";
import { type GuestLine, guestCartStorage } from "./guestCartStorage";

type CartContextValue = {
  /** Корзина в одном виде для гостя и клиента; null — ещё не загружена. */
  cart: Cart | null;
  count: number;
  loading: boolean;
  error: string | null;
  /** Сообщение после переноса гостевой корзины при входе. */
  notice: string | null;
  refresh: () => Promise<void>;
  /** Ошибки (лимит, нет в наличии) пробрасываются как ApiError — показывает экран. */
  add: (variantId: number, priceKopecks: number) => Promise<void>;
  setQuantity: (line: CartLine, quantity: number) => Promise<void>;
  remove: (line: CartLine) => Promise<void>;
  ackPrices: () => Promise<void>;
  dismissNotice: () => void;
};

const CartContext = createContext<CartContextValue | null>(null);

function errorText(error: unknown): string {
  return error instanceof ApiError ? error.message : "Не удалось загрузить корзину.";
}

function guestLineError(line: CartLine | undefined): string {
  switch (line?.status) {
    case "out_of_stock":
      return "Товара нет в наличии.";
    case "exceeds_stock":
      return `Можно добавить не больше ${line.max_quantity} шт.`;
    default:
      return "Товар недоступен для заказа.";
  }
}

function noticeText(notices: CartMergeNotice[]): string | null {
  if (notices.length === 0) return null;
  const skipped = notices.filter((notice) => notice.reason !== "quantity_limited").length;
  const limited = notices.length - skipped;
  const parts = [];
  if (skipped) parts.push(`${skipped} из товаров гостевой корзины недоступны и не перенесены`);
  if (limited) parts.push(`количество ${limited} товаров уменьшено до доступного`);
  return `Корзина перенесена в аккаунт: ${parts.join(", ")}.`;
}

/**
 * Корзина приложения. Гость хранит позиции на устройстве, расчёт делает сервер (quote).
 * После входа или регистрации гостевая корзина переносится на сервер (merge) и очищается.
 */
export function CartProvider({ children }: { children: ReactNode }) {
  const { status } = useAuth();
  const signedIn = status === "signedIn";
  const ready = status === "signedIn" || status === "signedOut";

  const [cart, setCart] = useState<Cart | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [notice, setNotice] = useState<string | null>(null);
  const guest = useRef<GuestLine[] | null>(null);
  // Ответы, пришедшие после смены пользователя, отбрасываются.
  const generation = useRef(0);

  const loadGuest = useCallback(async () => {
    if (guest.current === null) guest.current = await guestCartStorage.load();
    return guest.current;
  }, []);

  const saveGuest = useCallback(async (lines: GuestLine[]) => {
    guest.current = lines;
    await guestCartStorage.save(lines);
  }, []);

  // Один перенос гостевой корзины за раз: экран корзины и провайдер могут вызвать
  // refresh одновременно, а повторный merge удвоил бы количества.
  const merging = useRef<Promise<Cart> | null>(null);

  const mergeGuest = useCallback(
    async (lines: GuestLine[]): Promise<Cart> => {
      let next: Cart;
      try {
        const result = await cartService.merge(lines);
        next = result.cart;
        setNotice(noticeText(result.notices));
      } catch (err) {
        // Некорректные данные гостевой корзины не должны блокировать корзину навсегда;
        // при ошибке сети гостевая корзина остаётся и переносится при следующей попытке.
        if (!(err instanceof ApiError && err.status === 400)) throw err;
        setNotice("Не удалось перенести гостевую корзину.");
        next = await cartService.get();
      }
      await saveGuest([]);
      return next;
    },
    [saveGuest],
  );

  const refresh = useCallback(async () => {
    if (!ready) return;
    const current = ++generation.current;
    setLoading(true);
    setError(null);
    try {
      await loadGuest();
      // guest.current, а не снимок до await: другой refresh мог уже перенести корзину.
      const local = guest.current ?? [];
      let next: Cart;
      if (signedIn && local.length > 0) {
        merging.current ??= mergeGuest(local).finally(() => {
          merging.current = null;
        });
        next = await merging.current;
      } else if (signedIn && merging.current) {
        next = await merging.current;
      } else {
        next = signedIn ? await cartService.get() : await cartService.quote(local);
      }
      if (current === generation.current) setCart(next);
    } catch (err) {
      if (current === generation.current) setError(errorText(err));
    } finally {
      if (current === generation.current) setLoading(false);
    }
  }, [ready, signedIn, loadGuest, mergeGuest]);

  useEffect(() => {
    if (!signedIn) setNotice(null);
    void refresh();
  }, [signedIn, refresh]);

  /** Изменение корзины клиента: ответ сервера — новое состояние корзины. */
  const applyServer = useCallback(
    async (request: Promise<Cart>) => {
      generation.current++;
      try {
        setCart(await request);
      } catch (err) {
        // Позиция могла измениться на другом устройстве — показываем актуальное состояние.
        if (err instanceof ApiError && err.status === 404) void refresh();
        throw err;
      }
    },
    [refresh],
  );

  /** Изменение гостевой корзины: сохраняется, только если сервер подтвердил позицию. */
  const applyGuest = useCallback(
    async (lines: GuestLine[], check?: { variantId: number; message?: string }) => {
      const quoted = await cartService.quote(lines);
      if (check) {
        const line = quoted.items.find((item) => item.variant_id === check.variantId);
        if (line?.status !== "ok") {
          throw new ApiError(400, check.message ?? guestLineError(line));
        }
      }
      generation.current++;
      await saveGuest(lines);
      setCart(quoted);
    },
    [saveGuest],
  );

  const value = useMemo<CartContextValue>(
    () => ({
      cart,
      count: cart?.items_count ?? 0,
      loading,
      error,
      notice,
      refresh,
      dismissNotice: () => setNotice(null),

      add: async (variantId, priceKopecks) => {
        if (signedIn) return applyServer(cartService.add(variantId));
        const lines = await loadGuest();
        const exists = lines.some((line) => line.variant_id === variantId);
        const next = exists
          ? lines.map((line) =>
              line.variant_id === variantId
                ? { ...line, quantity: line.quantity + 1, seen_price_kopecks: priceKopecks }
                : line,
            )
          : [...lines, { variant_id: variantId, quantity: 1, seen_price_kopecks: priceKopecks }];
        return applyGuest(next, { variantId });
      },

      setQuantity: async (line, quantity) => {
        if (signedIn && line.id !== null) {
          return applyServer(cartService.setQuantity(line.id, quantity));
        }
        const lines = await loadGuest();
        const next = lines.map((item) =>
          item.variant_id === line.variant_id ? { ...item, quantity } : item,
        );
        return applyGuest(next, {
          variantId: line.variant_id,
          message: `Укажите количество от 1 до ${line.max_quantity}.`,
        });
      },

      remove: async (line) => {
        if (signedIn && line.id !== null) return applyServer(cartService.remove(line.id));
        const lines = await loadGuest();
        return applyGuest(lines.filter((item) => item.variant_id !== line.variant_id));
      },

      ackPrices: async () => {
        if (signedIn) return applyServer(cartService.ackPrices());
        const prices = new Map(
          (cart?.items ?? []).map((item) => [item.variant_id, item.unit_price_kopecks]),
        );
        const lines = await loadGuest();
        return applyGuest(
          lines.map((line) => ({
            ...line,
            seen_price_kopecks: prices.get(line.variant_id) ?? line.seen_price_kopecks,
          })),
        );
      },
    }),
    [cart, loading, error, notice, refresh, signedIn, applyServer, applyGuest, loadGuest],
  );

  return <CartContext.Provider value={value}>{children}</CartContext.Provider>;
}

export function useCart(): CartContextValue {
  const context = useContext(CartContext);
  if (!context) throw new Error("useCart вызывается вне CartProvider");
  return context;
}
