import { StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../components/theme";
import { Button, Message } from "../components/ui";
import { formatKopecks } from "../lib/money";
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
  const inProgress = isPaymentInProgress(order);
  const refund = order.refund_status ? REFUND_TEXT[order.refund_status] : null;

  if (!order.can_pay && !inProgress && !refund) return null;

  return (
    <View style={styles.card}>
      {order.can_pay && order.pay_until ? (
        <Text style={styles.text}>
          Оплатите заказ до {formatDateTime(order.pay_until)} — иначе он будет отменён, а товары
          вернутся в продажу.
        </Text>
      ) : null}
      {order.payment_status === "canceled" && order.can_pay ? (
        <Message text="Оплата не прошла. Попробуйте ещё раз или другим способом." />
      ) : null}
      {inProgress ? (
        <Text style={styles.muted}>
          Если вы уже оплатили, статус обновится в течение пары минут.
        </Text>
      ) : null}
      <Message text={error} />
      {order.can_pay ? (
        <Button
          title={`Оплатить ${formatKopecks(order.total_kopecks)}`}
          onPress={onPay}
          loading={paying}
          disabled={checking}
        />
      ) : null}
      {inProgress ? (
        <Button
          title="Проверить оплату"
          variant="secondary"
          onPress={onCheck}
          loading={checking}
          disabled={paying}
        />
      ) : null}
      {refund ? <Text style={styles.text}>{refund}</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  card: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  text: { fontSize: 15, color: colors.text },
  muted: { fontSize: 13, color: colors.muted },
});
