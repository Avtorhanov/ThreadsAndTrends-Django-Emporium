import { router, Stack, useLocalSearchParams } from "expo-router";
import { useEffect, useRef } from "react";
import { ActivityIndicator, Image, Pressable, StyleSheet, Text, View } from "react-native";

import { confirmAction } from "../../../src/components/confirm";
import { colors, radius, spacing } from "../../../src/components/theme";
import { Button, Message, Screen } from "../../../src/components/ui";
import { useSubmit } from "../../../src/hooks/useSubmit";
import { formatKopecks } from "../../../src/lib/money";
import { formatDateTime, StatusBadge } from "../../../src/orders/components";
import { useOrder } from "../../../src/orders/hooks";
import { type OrderDetail, orderService } from "../../../src/orders/orderService";
import { checkPayment, isPaymentInProgress, payOrder } from "../../../src/orders/payment";
import { PaymentPanel } from "../../../src/orders/PaymentPanel";

function Items({ order }: { order: OrderDetail }) {
  return (
    <View style={styles.card}>
      {order.items.map((item) => (
        <Pressable
          key={item.id}
          style={styles.item}
          onPress={() =>
            router.push({ pathname: "/product/[slug]", params: { slug: item.product_slug } })
          }
        >
          {item.cover_url ? (
            <Image source={{ uri: item.cover_url }} style={styles.cover} />
          ) : (
            <View style={[styles.cover, styles.coverEmpty]} />
          )}
          <View style={styles.itemBody}>
            <Text style={styles.itemName} numberOfLines={2}>
              {item.product_name}
            </Text>
            <Text style={styles.muted}>
              {item.size ? `Размер ${item.size} · ` : ""}
              {item.quantity} × {formatKopecks(item.price_kopecks)}
            </Text>
          </View>
          <Text style={styles.itemTotal}>{formatKopecks(item.line_total_kopecks)}</Text>
        </Pressable>
      ))}
      <View style={styles.divider} />
      <Row label="Товары" value={formatKopecks(order.items_total_kopecks)} />
      <Row
        label="Доставка"
        value={order.delivery_kopecks ? formatKopecks(order.delivery_kopecks) : "Бесплатно"}
      />
      <Row label="Итого" value={formatKopecks(order.total_kopecks)} strong />
    </View>
  );
}

function Row({ label, value, strong }: { label: string; value: string; strong?: boolean }) {
  return (
    <View style={styles.row}>
      <Text style={[styles.rowLabel, strong && styles.strong]}>{label}</Text>
      <Text style={[styles.rowValue, strong && styles.strong]}>{value}</Text>
    </View>
  );
}

export default function OrderScreen() {
  const { number, created } = useLocalSearchParams<{ number: string; created?: string }>();
  const { order, setOrder, loading, error, reload } = useOrder(number);

  const cancel = useSubmit(async () => {
    setOrder(await orderService.cancel(number));
  });
  const pay = useSubmit(async () => {
    setOrder(await payOrder(number));
  });
  const check = useSubmit(async () => {
    setOrder(await checkPayment(number, true));
  });

  // Экран открыт по ссылке возврата со страницы оплаты (или позже) — сверяем оплату один раз.
  const autoChecked = useRef(false);
  useEffect(() => {
    if (!order || autoChecked.current || !isPaymentInProgress(order)) return;
    autoChecked.current = true;
    void check.submit();
  }, [order, check.submit]);

  const confirmCancel = async () => {
    const confirmed = await confirmAction({
      title: "Отменить заказ?",
      message:
        order?.payment_status === "succeeded"
          ? "Деньги вернутся на карту или счёт, с которых вы платили. Отмену нельзя отменить."
          : "Товары вернутся в продажу. Отмену нельзя отменить.",
      confirmText: "Отменить заказ",
      cancelText: "Не отменять",
    });
    if (confirmed) void cancel.submit();
  };

  if (!order) {
    return (
      <View style={styles.center}>
        <Stack.Screen options={{ title: `Заказ ${number}` }} />
        {loading ? <ActivityIndicator color={colors.primary} /> : null}
        <Message text={error} />
        {error ? <Button title="Повторить" variant="secondary" onPress={() => void reload()} /> : null}
      </View>
    );
  }

  return (
    <Screen>
      <Stack.Screen options={{ title: `Заказ ${order.number}` }} />
      {created && order.status !== "cancelled" ? (
        <Message
          text={
            order.can_pay
              ? "Заказ оформлен. Оплатите его, чтобы мы начали сборку."
              : "Заказ оформлен. Мы сообщим об изменении статуса на email."
          }
          kind="success"
        />
      ) : null}

      <View style={styles.header}>
        <StatusBadge status={order.status} label={order.status_display} />
        <Text style={styles.muted}>от {formatDateTime(order.created_at)}</Text>
      </View>

      <PaymentPanel
        order={order}
        paying={pay.loading}
        checking={check.loading}
        error={pay.error ?? check.error}
        onPay={() => void pay.submit()}
        onCheck={() => void check.submit()}
      />

      <Items order={order} />

      <View style={styles.card}>
        <Text style={styles.caption}>{order.delivery_method_display}</Text>
        <Text style={styles.text}>{order.delivery_address}</Text>
        <Text style={styles.caption}>Получатель</Text>
        <Text style={styles.text}>
          {order.recipient_name}, {order.recipient_phone}
        </Text>
        <Text style={styles.caption}>Оплата</Text>
        <Text style={styles.text}>{order.payment_method_display}</Text>
        {order.comment ? (
          <>
            <Text style={styles.caption}>Комментарий</Text>
            <Text style={styles.text}>{order.comment}</Text>
          </>
        ) : null}
      </View>

      <View style={styles.card}>
        <Text style={styles.caption}>История</Text>
        {order.status_history.map((change) => (
          <View key={`${change.to_status}-${change.created_at}`} style={styles.row}>
            <Text style={styles.text}>{change.to_status_display}</Text>
            <Text style={styles.muted}>{formatDateTime(change.created_at)}</Text>
          </View>
        ))}
      </View>

      <Message text={cancel.error} />
      {order.can_cancel ? (
        <Button
          title="Отменить заказ"
          variant="secondary"
          onPress={confirmCancel}
          loading={cancel.loading}
        />
      ) : null}
      <Button title="Все заказы" variant="secondary" onPress={() => router.navigate("/orders")} />
    </Screen>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.background,
  },
  header: { gap: spacing.xs },
  card: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  item: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  cover: { width: 56, height: 56, borderRadius: radius, backgroundColor: colors.background },
  coverEmpty: { borderWidth: 1, borderColor: colors.border },
  itemBody: { flex: 1, gap: 2 },
  itemName: { fontSize: 15, color: colors.text },
  itemTotal: { fontSize: 15, fontWeight: "600", color: colors.text },
  divider: { height: 1, backgroundColor: colors.border },
  row: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  rowLabel: { fontSize: 15, color: colors.muted },
  rowValue: { fontSize: 15, color: colors.text },
  strong: { fontSize: 18, fontWeight: "700", color: colors.text },
  caption: { fontSize: 13, color: colors.muted },
  text: { fontSize: 15, color: colors.text },
  muted: { fontSize: 13, color: colors.muted },
});
