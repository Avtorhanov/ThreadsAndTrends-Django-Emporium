import { router, Stack, useLocalSearchParams } from "expo-router";
import { useEffect, useRef } from "react";
import { Pressable, Text, View } from "react-native";

import { ProductImage } from "../../../src/catalog/components";
import { confirmAction } from "../../../src/components/confirm";
import {
  Button,
  Card,
  Centered,
  Divider,
  LinkButton,
  Loading,
  Message,
  Screen,
  SummaryRow,
} from "../../../src/components/ui";
import { useSubmit } from "../../../src/hooks/useSubmit";
import { formatKopecks } from "../../../src/lib/money";
import { formatDateTime, StatusBadge } from "../../../src/orders/components";
import { useOrder } from "../../../src/orders/hooks";
import { type OrderDetail, orderService } from "../../../src/orders/orderService";
import { checkPayment, isPaymentInProgress, payOrder } from "../../../src/orders/payment";
import { PaymentPanel } from "../../../src/orders/PaymentPanel";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles } from "../../../src/theme/ThemeProvider";
import { radius } from "../../../src/theme/tokens";

function Items({ order }: { order: OrderDetail }) {
  const s = useStyles();
  return (
    <Card style={s.card}>
      {order.items.map((item) => (
        <Pressable
          key={item.id}
          accessibilityRole="link"
          style={s.item}
          onPress={() => router.push({ pathname: "/product/[slug]", params: { slug: item.product_slug } })}
        >
          <ProductImage slug={item.product_slug} uri={item.cover_url} style={s.cover} />
          <View style={s.itemBody}>
            <Text style={s.itemName} numberOfLines={2}>
              {item.product_name}
            </Text>
            <Text style={s.muted}>
              {item.size ? `Размер ${item.size} · ` : ""}
              {item.status_name ? `${item.status_name} · ` : ""}
              {item.quantity} × {formatKopecks(item.price_kopecks)}
            </Text>
          </View>
          <Text style={s.itemTotal}>{formatKopecks(item.line_total_kopecks)}</Text>
        </Pressable>
      ))}
      <Divider />
      <SummaryRow label="Товары" value={formatKopecks(order.items_total_kopecks)} />
      <SummaryRow
        label="Доставка"
        value={order.delivery_kopecks ? formatKopecks(order.delivery_kopecks) : "Бесплатно"}
      />
      <SummaryRow label="Итого" value={formatKopecks(order.total_kopecks)} strong />
    </Card>
  );
}

function Field({ label, value }: { label: string; value: string }) {
  const s = useStyles();
  return (
    <View style={s.fieldBox}>
      <Text style={s.caption}>{label}</Text>
      <Text style={s.text}>{value}</Text>
    </View>
  );
}

export default function OrderScreen() {
  const s = useStyles();
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
      <Centered>
        <Stack.Screen options={{ title: `Заказ ${number}` }} />
        {loading ? <Loading /> : null}
        <Message text={error} />
        {error ? <Button title="Повторить" variant="secondary" onPress={() => void reload()} /> : null}
      </Centered>
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

      <View style={s.header}>
        <StatusBadge status={order.status} label={order.status_display} />
        <Text style={s.muted}>от {formatDateTime(order.created_at)}</Text>
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

      <Card style={s.card}>
        <Field label={order.delivery_method_display} value={order.delivery_address} />
        <Field label="Получатель" value={`${order.recipient_name}, ${order.recipient_phone}`} />
        <Field label="Оплата" value={order.payment_method_display} />
        {order.comment ? <Field label="Комментарий" value={order.comment} /> : null}
      </Card>

      <Card style={s.card}>
        <Text style={s.caption}>История</Text>
        {order.status_history.map((change) => (
          <View key={`${change.to_status}-${change.created_at}`} style={s.historyItem}>
            <View style={s.historyRow}>
              <Text style={s.text}>{change.to_status_display}</Text>
              <Text style={s.muted}>{formatDateTime(change.created_at)}</Text>
            </View>
            {change.comment ? <Text style={s.historyNote}>{change.comment}</Text> : null}
          </View>
        ))}
      </Card>

      <Message text={cancel.error} />
      {order.can_cancel ? (
        <Button title="Отменить заказ" variant="danger" onPress={confirmCancel} loading={cancel.loading} />
      ) : null}
      <LinkButton title="Все заказы" onPress={() => router.navigate("/orders")} />
    </Screen>
  );
}

const useStyles = makeStyles(({ c }) => ({
  header: { gap: 8 },
  card: { gap: 12, padding: 18 },
  item: { flexDirection: "row", alignItems: "center", gap: 12 },
  cover: { width: 56, height: 64, borderRadius: radius.control - 4 },
  itemBody: { flex: 1, gap: 2 },
  itemName: { fontFamily: fonts.text700, fontSize: 15, color: c.ink },
  itemTotal: { fontFamily: fonts.display700, fontSize: 15, color: c.ink },
  fieldBox: { gap: 2 },
  historyItem: { gap: 6 },
  historyNote: {
    fontFamily: fonts.text600,
    fontSize: 13,
    lineHeight: 19,
    color: c.ink,
    backgroundColor: c.surface,
    borderRadius: radius.control - 6,
    paddingHorizontal: 10,
    paddingVertical: 8,
    overflow: "hidden",
  },
  historyRow: { flexDirection: "row", justifyContent: "space-between", gap: 16 },
  caption: { fontFamily: fonts.text700, fontSize: 13, color: c.muted },
  text: { fontFamily: fonts.text600, fontSize: 15, lineHeight: 21, color: c.ink },
  muted: { fontFamily: fonts.text600, fontSize: 13, color: c.muted },
}));
