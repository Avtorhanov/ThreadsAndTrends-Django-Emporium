import AsyncStorage from "@react-native-async-storage/async-storage";

/** Позиция гостевой корзины на устройстве. Цены и наличие считает сервер (POST /cart/quote/). */
export type GuestLine = {
  variant_id: number;
  quantity: number;
  /** Цена, которую гость видел при добавлении, коп. — для предупреждения «цена изменилась». */
  seen_price_kopecks: number | null;
};

const KEY = "didi.guest_cart.v1";

function isGuestLine(value: unknown): value is GuestLine {
  if (!value || typeof value !== "object") return false;
  const line = value as Record<string, unknown>;
  return (
    Number.isInteger(line.variant_id) &&
    Number.isInteger(line.quantity) &&
    (line.quantity as number) > 0 &&
    (line.seen_price_kopecks === null || Number.isInteger(line.seen_price_kopecks))
  );
}

export const guestCartStorage = {
  async load(): Promise<GuestLine[]> {
    try {
      const raw = await AsyncStorage.getItem(KEY);
      const parsed: unknown = raw ? JSON.parse(raw) : [];
      // Повреждённые данные не ломают приложение: берём только корректные позиции.
      return Array.isArray(parsed) ? parsed.filter(isGuestLine) : [];
    } catch {
      return [];
    }
  },
  async save(lines: GuestLine[]): Promise<void> {
    if (lines.length === 0) await AsyncStorage.removeItem(KEY);
    else await AsyncStorage.setItem(KEY, JSON.stringify(lines));
  },
};
