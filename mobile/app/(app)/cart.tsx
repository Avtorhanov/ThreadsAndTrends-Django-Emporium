import { router, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import {
  ActivityIndicator,
  FlatList,
  Image,
  Pressable,
  StyleSheet,
  Text,
  View,
} from "react-native";

import { ApiError } from "../../src/api/errors";
import { useAuth } from "../../src/auth/AuthProvider";
import { useCart } from "../../src/cart/CartProvider";
import type { CartLine } from "../../src/cart/cartService";
import { colors, radius, spacing } from "../../src/components/theme";
import { Button, Message } from "../../src/components/ui";
import { formatKopecks } from "../../src/lib/money";

const STATUS_TEXT: Record<CartLine["status"], string | null> = {
  ok: null,
  unavailable: "Товар больше не продаётся",
  out_of_stock: "Нет в наличии",
  exceeds_stock: null, // текст с доступным количеством — в строке
};

/** Одно действие за раз: защита от двойных нажатий и общий текст ошибки. */
function useCartAction() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inFlight = useRef(false);

  const run = useCallback(async (action: () => Promise<void>) => {
    if (inFlight.current) return;
    inFlight.current = true;
    setBusy(true);
    setError(null);
    try {
      await action();
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Что-то пошло не так. Попробуйте ещё раз.");
    } finally {
      inFlight.current = false;
      setBusy(false);
    }
  }, []);

  return { busy, error, run };
}

function Stepper({
  line,
  disabled,
  onChange,
}: {
  line: CartLine;
  disabled: boolean;
  onChange: (quantity: number) => void;
}) {
  const ok = line.status === "ok";
  const canDecrease = ok && line.quantity > 1;
  const canIncrease = ok && line.quantity < line.max_quantity;
  return (
    <View style={styles.stepper}>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Уменьшить количество"
        disabled={disabled || !canDecrease}
        onPress={() => onChange(line.quantity - 1)}
        style={[styles.stepButton, !canDecrease && styles.dimmed]}
        hitSlop={6}
      >
        <Text style={styles.stepText}>−</Text>
      </Pressable>
      <Text style={styles.quantity} accessibilityLabel={`Количество: ${line.quantity}`}>
        {line.quantity}
      </Text>
      <Pressable
        accessibilityRole="button"
        accessibilityLabel="Увеличить количество"
        disabled={disabled || !canIncrease}
        onPress={() => onChange(line.quantity + 1)}
        style={[styles.stepButton, !canIncrease && styles.dimmed]}
        hitSlop={6}
      >
        <Text style={styles.stepText}>+</Text>
      </Pressable>
    </View>
  );
}

function CartRow({
  line,
  busy,
  onQuantity,
  onRemove,
}: {
  line: CartLine;
  busy: boolean;
  onQuantity: (quantity: number) => void;
  onRemove: () => void;
}) {
  const product = line.product;
  const problem =
    line.status === "exceeds_stock"
      ? `Доступно только ${line.max_quantity} шт.`
      : STATUS_TEXT[line.status];

  return (
    <View style={[styles.row, line.status !== "ok" && styles.rowProblem]}>
      <Pressable
        disabled={!product || line.status === "unavailable"}
        onPress={() =>
          product && router.push({ pathname: "/product/[slug]", params: { slug: product.slug } })
        }
      >
        {product?.cover_url ? (
          <Image source={{ uri: product.cover_url }} style={styles.cover} resizeMode="cover" />
        ) : (
          <View style={[styles.cover, styles.coverEmpty]}>
            <Text style={styles.muted}>Нет фото</Text>
          </View>
        )}
      </Pressable>

      <View style={styles.rowBody}>
        <Text style={styles.name} numberOfLines={2}>
          {product?.name ?? "Товар удалён из каталога"}
        </Text>
        {line.size ? <Text style={styles.muted}>Размер: {line.size}</Text> : null}
        {line.unit_price_kopecks !== null ? (
          <Text style={styles.price}>{formatKopecks(line.unit_price_kopecks)}</Text>
        ) : null}
        {line.price_changed && line.seen_price_kopecks !== null ? (
          <Text style={styles.warning}>
            Цена изменилась: было {formatKopecks(line.seen_price_kopecks)}
          </Text>
        ) : null}
        {problem ? <Text style={styles.problem}>{problem}</Text> : null}

        <View style={styles.rowActions}>
          {line.status === "exceeds_stock" ? (
            <Pressable
              accessibilityRole="button"
              disabled={busy}
              onPress={() => onQuantity(line.max_quantity)}
            >
              <Text style={styles.link}>Оставить {line.max_quantity}</Text>
            </Pressable>
          ) : (
            <Stepper line={line} disabled={busy} onChange={onQuantity} />
          )}
          <Pressable accessibilityRole="button" disabled={busy} onPress={onRemove} hitSlop={6}>
            <Text style={styles.remove}>Удалить</Text>
          </Pressable>
        </View>
        {line.status === "ok" ? (
          <Text style={styles.lineTotal}>{formatKopecks(line.line_total_kopecks)}</Text>
        ) : null}
      </View>
    </View>
  );
}

export default function CartScreen() {
  const { status } = useAuth();
  const signedIn = status === "signedIn";
  const { cart, loading, error, notice, refresh, setQuantity, remove, ackPrices, dismissNotice } =
    useCart();
  const action = useCartAction();

  // При каждом открытии — актуальные цены и наличие.
  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  if (!cart) {
    return (
      <View style={styles.center}>
        {loading || !error ? <ActivityIndicator color={colors.primary} /> : null}
        <Message text={error} />
        {error ? <Button title="Повторить" variant="secondary" onPress={() => void refresh()} /> : null}
      </View>
    );
  }

  const checkout = () => {
    if (!signedIn) {
      router.push("/sign-in");
      return;
    }
    router.push("/checkout");
  };

  return (
    <FlatList
      data={cart.items}
      keyExtractor={(line) => String(line.id ?? `v${line.variant_id}`)}
      contentContainerStyle={styles.content}
      refreshing={loading && cart !== null}
      onRefresh={() => void refresh()}
      ListHeaderComponent={
        <View style={styles.header}>
          {notice ? (
            <Pressable onPress={dismissNotice} accessibilityRole="button" accessibilityHint="Скрыть">
              <Message text={notice} kind="success" />
            </Pressable>
          ) : null}
          <Message text={error ?? action.error} />
          {cart.has_price_changes ? (
            <View style={styles.banner}>
              <Text style={styles.bannerText}>
                Цены на некоторые товары изменились. Итог посчитан по новым ценам.
              </Text>
              <Button
                title="Понятно"
                variant="secondary"
                disabled={action.busy}
                onPress={() => void action.run(ackPrices)}
              />
            </View>
          ) : null}
        </View>
      }
      renderItem={({ item }) => (
        <CartRow
          line={item}
          busy={action.busy}
          onQuantity={(quantity) => void action.run(() => setQuantity(item, quantity))}
          onRemove={() => void action.run(() => remove(item))}
        />
      )}
      ListEmptyComponent={
        <View style={styles.empty}>
          <Text style={styles.emptyText}>Корзина пуста</Text>
          <Button title="Перейти в каталог" variant="secondary" onPress={() => router.navigate("/")} />
        </View>
      }
      ListFooterComponent={
        cart.items.length > 0 ? (
          <View style={styles.footer}>
            <View style={styles.totalRow}>
              <Text style={styles.totalLabel}>Итого · {cart.items_count} шт.</Text>
              <Text style={styles.total}>{formatKopecks(cart.total_kopecks)}</Text>
            </View>
            {cart.has_problems ? (
              <Text style={styles.problem}>
                Часть товаров недоступна или их меньше, чем в корзине. Удалите их или измените
                количество, чтобы оформить заказ.
              </Text>
            ) : null}
            <Button
              title={signedIn ? "Оформить заказ" : "Войти и оформить"}
              onPress={checkout}
              disabled={action.busy || (signedIn && !cart.can_checkout)}
            />
          </View>
        ) : null
      }
    />
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
  content: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background, flexGrow: 1 },
  header: { gap: spacing.sm },
  banner: {
    gap: spacing.sm,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  bannerText: { color: colors.text, fontSize: 15 },
  row: {
    flexDirection: "row",
    gap: spacing.md,
    padding: spacing.sm,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  rowProblem: { borderColor: colors.danger },
  cover: { width: 88, height: 88, borderRadius: radius, backgroundColor: colors.background },
  coverEmpty: { alignItems: "center", justifyContent: "center" },
  rowBody: { flex: 1, gap: spacing.xs },
  name: { fontSize: 15, color: colors.text },
  muted: { color: colors.muted, fontSize: 13 },
  price: { fontSize: 15, fontWeight: "600", color: colors.text },
  warning: { fontSize: 13, color: colors.muted },
  problem: { fontSize: 13, color: colors.danger },
  rowActions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: spacing.xs,
  },
  stepper: { flexDirection: "row", alignItems: "center", gap: spacing.sm },
  stepButton: {
    width: 32,
    height: 32,
    borderRadius: 16,
    borderWidth: 1,
    borderColor: colors.border,
    alignItems: "center",
    justifyContent: "center",
  },
  stepText: { fontSize: 18, color: colors.text },
  quantity: { minWidth: 24, textAlign: "center", fontSize: 16, color: colors.text },
  dimmed: { opacity: 0.4 },
  link: { color: colors.primary, fontSize: 15 },
  remove: { color: colors.danger, fontSize: 14 },
  lineTotal: { alignSelf: "flex-end", fontSize: 15, fontWeight: "700", color: colors.text },
  empty: { alignItems: "center", gap: spacing.md, marginTop: spacing.xl },
  emptyText: { color: colors.muted, fontSize: 16 },
  footer: { gap: spacing.md, paddingTop: spacing.sm },
  totalRow: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" },
  totalLabel: { fontSize: 16, color: colors.muted },
  total: { fontSize: 22, fontWeight: "700", color: colors.text },
});
