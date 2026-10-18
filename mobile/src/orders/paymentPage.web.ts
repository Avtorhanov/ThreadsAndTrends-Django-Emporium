import Constants from "expo-constants";

import type { PaymentPageOutcome } from "./paymentPage";

// Веб-версия работает по адресу https://<домен>/app/ (experiments.baseUrl в app.json).
const BASE_PATH = (Constants.expoConfig?.experiments?.baseUrl ?? "").replace(/\/+$/, "");

/**
 * Веб-версия: переход на страницу оплаты в той же вкладке. Провайдер возвращает покупателя
 * на https://<домен>/app/orders/<номер>, экран заказа сам сверяет оплату (orders/[number].tsx).
 * Адрес должен входить в PAYMENTS_RETURN_URL_PREFIXES (в compose.prod.yml — https://<домен>/).
 */
export async function openPaymentPage(
  number: string,
  start: (returnUrl: string) => Promise<string>,
): Promise<PaymentPageOutcome> {
  const returnUrl = `${window.location.origin}${BASE_PATH}/orders/${encodeURIComponent(number)}`;
  const confirmationUrl = await start(returnUrl);
  window.location.assign(confirmationUrl);
  // Страница уходит к провайдеру — промис не завершается, кнопка остаётся в состоянии загрузки.
  return new Promise<PaymentPageOutcome>(() => {});
}
