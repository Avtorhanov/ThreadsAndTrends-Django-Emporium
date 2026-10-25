import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";

/** Результат визита на страницу оплаты: вернулся по ссылке или закрыл браузер. */
export type PaymentPageOutcome = "returned" | "closed";

/**
 * Страница оплаты во встроенном браузере. `start` получает адрес возврата и отдаёт ссылку
 * провайдера. В сборке возврат — didishop://orders/<номер>, в Expo Go — exp://…/--/orders/<номер>.
 */
export async function openPaymentPage(
  number: string,
  start: (returnUrl: string) => Promise<string>,
): Promise<PaymentPageOutcome> {
  const returnUrl = Linking.createURL(`orders/${number}`);
  const confirmationUrl = await start(returnUrl);
  const result = await WebBrowser.openAuthSessionAsync(confirmationUrl, returnUrl);
  return result.type === "success" ? "returned" : "closed";
}
