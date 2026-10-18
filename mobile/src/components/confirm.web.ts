import type { ConfirmOptions } from "./confirm";

/** Alert с кнопками в react-native-web не работает — в браузере стандартный confirm. */
export function confirmAction({ title, message }: ConfirmOptions): Promise<boolean> {
  return Promise.resolve(window.confirm(`${title}\n\n${message}`));
}
