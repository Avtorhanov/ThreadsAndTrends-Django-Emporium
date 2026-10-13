import { router } from "expo-router";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";

import { ApiError } from "../../src/api/errors";
import { useAuth } from "../../src/auth/AuthProvider";
import { useCart } from "../../src/cart/CartProvider";
import { colors, radius, spacing } from "../../src/components/theme";
import { Button, Hint, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";
import { formatKopecks } from "../../src/lib/money";
import { ChoiceList } from "../../src/orders/components";
import {
  type CheckoutPreview,
  type DeliveryMethod,
  newIdempotencyKey,
  orderService,
  PAYMENT_TITLES,
  type PaymentMethod,
} from "../../src/orders/orderService";

export default function CheckoutScreen() {
  const { user } = useAuth();
  const { refresh: refreshCart } = useCart();
  const [preview, setPreview] = useState<CheckoutPreview | null>(null);
  const [loadError, setLoadError] = useState<string | null>(null);

  const [delivery, setDelivery] = useState<DeliveryMethod | null>(null);
  const [payment, setPayment] = useState<PaymentMethod | null>(null);
  const [name, setName] = useState("");
  const [phone, setPhone] = useState("");
  const [address, setAddress] = useState("");
  const [comment, setComment] = useState("");
  // Один ключ на экран: повтор после обрыва сети вернёт уже созданный заказ.
  const idempotencyKey = useRef(newIdempotencyKey());
  const prefilled = useRef(false);

  const load = useCallback(async () => {
    setLoadError(null);
    try {
      const data = await orderService.preview();
      setPreview(data);
      setDelivery((current) => current ?? data.delivery_options[0]?.method ?? null);
      setPayment((current) => current ?? data.payment_methods[0] ?? null);
      if (!prefilled.current) {
        prefilled.current = true;
        const fullName = [user?.first_name, user?.last_name].filter(Boolean).join(" ");
        setName(data.defaults.recipient_name || fullName);
        setPhone(data.defaults.recipient_phone);
        setAddress(data.defaults.delivery_address);
      }
    } catch (err) {
      setLoadError(err instanceof ApiError ? err.message : "Не удалось загрузить данные заказа.");
    }
  }, [user]);

  useEffect(() => {
    void load();
  }, [load]);

  const option = useMemo(
    () => preview?.delivery_options.find((item) => item.method === delivery) ?? null,
    [preview, delivery],
  );
  const itemsTotal = preview?.cart.total_kopecks ?? 0;
  const total = itemsTotal + (option?.cost_kopecks ?? 0);

  const submit = useSubmit(async () => {
    if (!delivery || !payment) return;
    try {
      const order = await orderService.create(
        {
          delivery_method: delivery,
          payment_method: payment,
          recipient_name: name,
          recipient_phone: phone,
          delivery_address: delivery === "courier" ? address : "",
          comment,
          expected_total_kopecks: total,
        },
        idempotencyKey.current,
      );
      void refreshCart();
      router.replace({
        pathname: "/orders/[number]",
        params: { number: order.number, created: "1" },
      });
    } catch (err) {
      // Корзина или сумма могли измениться — показываем актуальный расчёт.
      if (err instanceof ApiError && Object.keys(err.fieldErrors).every((k) => k === "non_field_errors")) {
        void load();
      }
      throw err;
    }
  });

  if (!preview) {
    return (
      <View style={styles.center}>
        {loadError ? (
          <>
            <Message text={loadError} />
            <Button title="Повторить" variant="secondary" onPress={() => void load()} />
          </>
        ) : (
          <ActivityIndicator color={colors.primary} />
        )}
      </View>
    );
  }

  if (!preview.cart.can_checkout) {
    return (
      <Screen>
        <Message
          text={
            preview.cart.items.length === 0
              ? "Корзина пуста."
              : "В корзине есть недоступные товары. Исправьте корзину, чтобы оформить заказ."
          }
        />
        <Button title="Вернуться в корзину" variant="secondary" onPress={() => router.back()} />
      </Screen>
    );
  }

  const freeFrom = preview.free_delivery_from_kopecks;
  const deliveryOptions = preview.delivery_options.map((item) => ({
    value: item.method,
    title: item.title,
    caption:
      item.method === "pickup"
        ? `${item.address} · бесплатно`
        : item.cost_kopecks === 0
          ? "Бесплатно"
          : `${formatKopecks(item.cost_kopecks)} · бесплатно от ${formatKopecks(freeFrom)}`,
  }));
  const paymentOptions = preview.payment_methods.map((method) => ({
    value: method,
    title: PAYMENT_TITLES[method],
  }));
  const errors = submit.fieldErrors;

  return (
    <Screen>
      <Text style={styles.section}>Получение</Text>
      <ChoiceList options={deliveryOptions} value={delivery} onChange={setDelivery} />
      {errors.delivery_method ? <Message text={errors.delivery_method[0] ?? null} /> : null}

      <Text style={styles.section}>Получатель</Text>
      <TextField
        label="Имя и фамилия"
        value={name}
        onChangeText={setName}
        autoComplete="name"
        textContentType="name"
        errors={errors.recipient_name}
      />
      <TextField
        label="Телефон"
        value={phone}
        onChangeText={setPhone}
        keyboardType="phone-pad"
        autoComplete="tel"
        textContentType="telephoneNumber"
        placeholder="+7 900 123-45-67"
        errors={errors.recipient_phone}
      />
      {delivery === "courier" ? (
        <TextField
          label="Адрес доставки"
          value={address}
          onChangeText={setAddress}
          autoComplete="street-address"
          textContentType="fullStreetAddress"
          placeholder="Город, улица, дом, квартира"
          multiline
          errors={errors.delivery_address}
        />
      ) : null}
      <TextField
        label="Комментарий (необязательно)"
        value={comment}
        onChangeText={setComment}
        maxLength={500}
        multiline
        errors={errors.comment}
      />

      <Text style={styles.section}>Оплата</Text>
      <ChoiceList options={paymentOptions} value={payment} onChange={setPayment} />
      {errors.payment_method ? <Message text={errors.payment_method[0] ?? null} /> : null}

      <View style={styles.summary}>
        <Row label={`Товары · ${preview.cart.items_count} шт.`} value={formatKopecks(itemsTotal)} />
        <Row
          label="Доставка"
          value={option && option.cost_kopecks > 0 ? formatKopecks(option.cost_kopecks) : "Бесплатно"}
        />
        <View style={styles.divider} />
        <Row label="Итого" value={formatKopecks(total)} strong />
      </View>
      {preview.cart.has_price_changes ? (
        <Hint>Цены на некоторые товары изменились — итог посчитан по новым ценам.</Hint>
      ) : null}

      <Message text={submit.error} />
      <Button
        title={`Подтвердить заказ · ${formatKopecks(total)}`}
        onPress={() => void submit.submit()}
        loading={submit.loading}
        disabled={!delivery || !payment}
      />
    </Screen>
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

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.background,
  },
  section: { fontSize: 18, fontWeight: "700", color: colors.text, marginTop: spacing.sm },
  summary: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  row: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  rowLabel: { fontSize: 15, color: colors.muted },
  rowValue: { fontSize: 15, color: colors.text },
  strong: { fontSize: 18, fontWeight: "700", color: colors.text },
  divider: { height: 1, backgroundColor: colors.border },
});
