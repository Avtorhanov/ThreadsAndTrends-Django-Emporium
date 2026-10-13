import type { components } from "../api/schema";
import { API_URL } from "../config";
import { tokenStorage } from "./tokenStorage";

export type TokenPair = components["schemas"]["TokenPair"];

let accessToken: string | null = null;
let refreshInFlight: Promise<string | null> | null = null;
const expiredListeners = new Set<() => void>();

export class OfflineError extends Error {}

async function doRefresh(): Promise<string | null> {
  const refresh = await tokenStorage.getRefresh();
  if (!refresh) return null;

  let response: Response;
  try {
    response = await fetch(`${API_URL}/api/v1/auth/refresh/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ refresh }),
    });
  } catch {
    // Сеть недоступна: токен не трогаем, сессия восстановится при следующей попытке.
    throw new OfflineError("Нет соединения с сервером.");
  }

  if (response.status === 401 || response.status === 400) {
    // Refresh отозван (выход на другом устройстве, смена пароля, блокировка).
    await session.clear();
    expiredListeners.forEach((listener) => listener());
    return null;
  }
  if (!response.ok) {
    throw new OfflineError("Сервер временно недоступен.");
  }
  const pair = (await response.json()) as TokenPair;
  await session.setTokens(pair);
  return pair.access;
}

export const session = {
  getAccess: () => accessToken,

  async setTokens(pair: TokenPair) {
    accessToken = pair.access;
    await tokenStorage.setRefresh(pair.refresh);
  },

  async clear() {
    accessToken = null;
    await tokenStorage.clear();
  },

  hasStoredSession: async () => (await tokenStorage.getRefresh()) !== null,

  getRefresh: () => tokenStorage.getRefresh(),

  /**
   * Новая пара токенов по refresh. Refresh одноразовый (ротация на сервере), поэтому
   * параллельные запросы, получившие 401, ждут один общий вызов.
   */
  refresh(): Promise<string | null> {
    if (!refreshInFlight) {
      refreshInFlight = doRefresh().finally(() => {
        refreshInFlight = null;
      });
    }
    return refreshInFlight;
  },

  /** Подписка на окончательную потерю сессии (refresh отозван). */
  onExpired(listener: () => void): () => void {
    expiredListeners.add(listener);
    return () => {
      expiredListeners.delete(listener);
    };
  },
};
