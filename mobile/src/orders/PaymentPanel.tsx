import { Text } from "react-native";

import { Button, Card, Message } from "../components/ui";
import { formatKopecks } from "../lib/money";
import { fonts } from "../theme/fonts";
import { makeStyles } from "../theme/ThemeProvider";
import { formatDateTime } from "./components";
import type { OrderDetail } from "./orderService";
import { isPaymentInProgress } from "./payment";

type Props = {
  order: OrderDetail;
  paying: boolean;
  checking: boolean;
  error: string | null;
  onPay: () => void;
  onCheck: () => void;
};

const REFUND_TEXT = {
  pending: "Возвращаем деньги на карту или счёт, с которых вы платили.",
  succeeded: "Деньги возвращены. Срок зачисления зависит от банка.",
  canceled: "Возврат задерживается — мы свяжемся с вами по email.",
} as const;

/** Блок оплаты на экране заказа: кнопка «Оплатить», проверка платежа и статус возврата. */
export function PaymentPanel({ order, paying, checking, error, onPay, onCheck }: Props) {
  const s = useStyles();
  const inProgress = isPaymentInProgress(order);
  const refund = order.refund_status ? REFUND_TEXT[order.refund_status] : null;

  if (!order.can_pay && !inProgress && !refund) return null;

  return (
    <Card style={s.card}>
      {order.can_pay && order.pay_until ? (
        <Text style={s.text}>
          Оплатите заказ до {formatDateTime(order.pay_until)} — иначе он будет отменён, а товары вернутся в
          продажу.
        </Text>
      ) : null}
      {order.payment_status === "canceled" && order.can_pay ? (
        <Message text="Оплата не прошла. Попробуйте ещё раз или другим способом." />
      ) : null}
      {inProgress ? <Text style={s.muted}>Если вы уже оплатили, статус обновится в течение пары минут.</Text> : null}
      <Message text={error} />
      {order.can_pay ? (
        <Button
          title="Оплатить"
          trailing={formatKopecks(order.total_kopecks)}
          variant="accent"
          onPress={onPay}
          loading={paying}
          disabled={checking}
        />
      ) : null}
      {inProgress ? (
        <Button title="Проверить оплату" variant="secondary" onPress={onCheck} loading={checking} disabled={paying} />
      ) : null}
      {refund ? <Message text={refund} kind={order.refund_status === "canceled" ? "warning" : "info"} /> : null}
    </Card>
  );
}

const useStyles = makeStyles(({ c }) => ({
  card: { gap: 12, padding: 18 },
  text: { fontFamily: fonts.text600, fontSize: 15, lineHeight: 21, color: c.ink },
  muted: { fontFamily: fonts.text500, fontSize: 13, color: c.muted },
}));
