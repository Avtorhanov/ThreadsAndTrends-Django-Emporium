import * as Linking from "expo-linking";
import * as WebBrowser from "expo-web-browser";

import { type OrderDetail, orderService } from "./orderService";

// После возврата со страницы оплаты банк может подтвердить платёж не сразу.
const POLL_ATTEMPTS = 5;
const POLL_DELAY_MS = 2000;

const sleep = (ms: number) => new Promise((resolve) => setTimeout(resolve, ms));

/** Платёж начат, но провайдер ещё не сообщил результат. */
export function isPaymentInProgress(order: OrderDetail): boolean {
  return order.status === "awaiting_payment" && order.payment_status === "pending";
}

/** Сверка оплаты на сервере; при `wait` — несколько повторов, пока платёж в обработке. */
export async function checkPayment(number: string, wait: boolean): Promise<OrderDetail> {
  let order = await orderService.refreshPayment(number);
  for (let attempt = 1; wait && attempt < POLL_ATTEMPTS && isPaymentInProgress(order); attempt++) {
    await sleep(POLL_DELAY_MS);
    order = await orderService.refreshPayment(number);
  }
  return order;
}

/** Оплата заказа на странице провайдера во встроенном браузере. Статус заказа меняет только
 * сервер по подтверждению провайдера — приложение лишь просит его сверить оплату. */
export async function payOrder(number: string): Promise<OrderDetail> {
  // В сборке — didishop://orders/<номер>, в Expo Go — exp://…/--/orders/<номер>.
  const returnUrl = Linking.createURL(`orders/${number}`);
  const { confirmation_url } = await orderService.pay(number, returnUrl);
  const result = await WebBrowser.openAuthSessionAsync(confirmation_url, returnUrl);
  // Вернулся по ссылке — платёж скорее всего прошёл, ждём подтверждения; закрыл браузер — одна сверка.
  return checkPayment(number, result.type === "success");
}
