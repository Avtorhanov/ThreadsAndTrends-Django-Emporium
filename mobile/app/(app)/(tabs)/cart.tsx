import { router, useFocusEffect } from "expo-router";
import { useCallback, useRef, useState } from "react";
import { FlatList, Pressable, Text, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { ApiError } from "../../../src/api/errors";
import { useAuth } from "../../../src/auth/AuthProvider";
import { useCart } from "../../../src/cart/CartProvider";
import type { CartLine } from "../../../src/cart/cartService";
import { ProductImage } from "../../../src/catalog/components";
import { Icon } from "../../../src/components/Icon";
import {
  Button,
  Card,
  Centered,
  LinkButton,
  Loading,
  Message,
  PressScale,
  ScreenTitle,
  SummaryRow,
  TAB_BAR_SPACE,
} from "../../../src/components/ui";
import { formatKopecks } from "../../../src/lib/money";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";
import { radius, space } from "../../../src/theme/tokens";

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
  const s = useStyles();
  const { c } = useTheme();
  const ok = line.status === "ok";
  const canDecrease = ok && line.quantity > 1;
  const canIncrease = ok && line.quantity < line.max_quantity;
  return (
    <View style={s.stepper}>
      <PressScale
        accessibilityRole="button"
        accessibilityLabel="Уменьшить количество"
        accessibilityState={{ disabled: disabled || !canDecrease }}
        disabled={disabled || !canDecrease}
        onPress={() => onChange(line.quantity - 1)}
        scale={0.9}
        hitSlop={4}
        style={[s.stepButton, !canDecrease && s.dimmed]}
      >
        <Icon name="minus" size={18} color={c.ink} />
      </PressScale>
      <Text style={s.quantity} accessibilityLabel={`Количество: ${line.quantity}`}>
        {line.quantity}
      </Text>
      <PressScale
        accessibilityRole="button"
        accessibilityLabel="Увеличить количество"
        accessibilityState={{ disabled: disabled || !canIncrease }}
        disabled={disabled || !canIncrease}
        onPress={() => onChange(line.quantity + 1)}
        scale={0.9}
        hitSlop={4}
        style={[s.stepButton, !canIncrease && s.dimmed]}
      >
        <Icon name="plus" size={18} color={c.ink} />
      </PressScale>
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
  const s = useStyles();
  const product = line.product;
  const problem =
    line.status === "exceeds_stock" ? `Доступно только ${line.max_quantity} шт.` : STATUS_TEXT[line.status];

  return (
    <Card style={[s.row, line.status !== "ok" && s.rowProblem]}>
      <Pressable
        accessibilityRole="link"
        accessibilityLabel={product?.name ?? "Товар удалён"}
        disabled={!product || line.status === "unavailable"}
        onPress={() => product && router.push({ pathname: "/product/[slug]", params: { slug: product.slug } })}
      >
        <ProductImage slug={product?.slug ?? String(line.variant_id)} uri={product?.cover_url} style={s.cover} />
      </Pressable>

      <View style={s.rowBody}>
        <Text style={s.name} numberOfLines={2}>
          {product?.name ?? "Товар удалён из каталога"}
        </Text>
        {line.size ? <Text style={s.muted}>Размер {line.size}</Text> : null}
        {line.unit_price_kopecks !== null ? (
          <Text style={s.price}>{formatKopecks(line.unit_price_kopecks)}</Text>
        ) : null}
        {line.price_changed && line.seen_price_kopecks !== null ? (
          <Text style={s.warning}>Цена изменилась: было {formatKopecks(line.seen_price_kopecks)}</Text>
        ) : null}
        {problem ? <Text style={s.problem}>{problem}</Text> : null}

        <View style={s.rowActions}>
          {line.status === "exceeds_stock" ? (
            <LinkButton title={`Оставить ${line.max_quantity}`} onPress={() => !busy && onQuantity(line.max_quantity)} />
          ) : (
            <Stepper line={line} disabled={busy} onChange={onQuantity} />
          )}
          <LinkButton title="Удалить" tone="danger" onPress={() => !busy && onRemove()} />
        </View>
      </View>
    </Card>
  );
}

export default function CartScreen() {
  const s = useStyles();
  const { c } = useTheme();
  const { status } = useAuth();
  const signedIn = status === "signedIn";
  const { cart, loading, error, notice, refresh, setQuantity, remove, ackPrices, dismissNotice } = useCart();
  const action = useCartAction();

  // При каждом открытии — актуальные цены и наличие.
  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  if (!cart) {
    return (
      <Centered>
        {loading || !error ? <Loading /> : null}
        <Message text={error} />
        {error ? <Button title="Повторить" variant="secondary" onPress={() => void refresh()} /> : null}
      </Centered>
    );
  }

  const checkout = () => router.push(signedIn ? "/checkout" : "/sign-in");

  return (
    <SafeAreaView style={s.screen} edges={["top"]}>
      <FlatList
        data={cart.items}
        keyExtractor={(line) => String(line.id ?? `v${line.variant_id}`)}
        contentContainerStyle={s.content}
        refreshing={loading && cart !== null}
        onRefresh={() => void refresh()}
        ListHeaderComponent={
          <View style={s.header}>
            <ScreenTitle
              overline={cart.items_count ? `Товаров: ${cart.items_count}` : "Корзина"}
              title="Корзина"
            />
            {notice ? (
              <Pressable onPress={dismissNotice} accessibilityRole="button" accessibilityHint="Скрыть">
                <Message text={notice} kind="success" />
              </Pressable>
            ) : null}
            <Message text={error ?? action.error} />
            {cart.has_price_changes ? (
              <Card style={s.banner}>
                <Text style={s.bannerText}>Цены на некоторые товары изменились. Итог посчитан по новым ценам.</Text>
                <Button
                  title="Понятно"
                  variant="secondary"
                  disabled={action.busy}
                  onPress={() => void action.run(ackPrices)}
                />
              </Card>
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
          <Card style={s.empty}>
            <View style={s.emptyIcon}>
              <Icon name="bag" size={30} color={c.tagInk} />
            </View>
            <Text style={s.emptyTitle}>Корзина пуста</Text>
            <Text style={s.muted}>Загляните в каталог — там новинки.</Text>
            <Button title="Перейти в каталог" variant="accent" onPress={() => router.navigate("/")} />
          </Card>
        }
        ListFooterComponent={
          cart.items.length > 0 ? (
            <Card style={s.footer}>
              <SummaryRow label={`Итого · ${cart.items_count} шт.`} value={formatKopecks(cart.total_kopecks)} strong />
              {cart.has_problems ? (
                <Text style={s.problem}>
                  Часть товаров недоступна или их меньше, чем в корзине. Удалите их или измените количество,
                  чтобы оформить заказ.
                </Text>
              ) : null}
              <Button
                title={signedIn ? "Оформить заказ" : "Войти и оформить"}
                onPress={checkout}
                disabled={action.busy || (signedIn && !cart.can_checkout)}
              />
            </Card>
          ) : null
        }
      />
    </SafeAreaView>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  screen: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: space.feedSide + 6, paddingBottom: TAB_BAR_SPACE, gap: 12, flexGrow: 1 },
  header: { gap: 12, paddingHorizontal: 4, paddingTop: 8, paddingBottom: 4 },
  banner: { gap: 12, padding: 16 },
  bannerText: { fontFamily: fonts.text600, color: c.ink, fontSize: 15, lineHeight: 21 },
  row: { flexDirection: "row", gap: 14, padding: 8, borderRadius: radius.card },
  rowProblem: { borderWidth: 1.5, borderColor: c.danger },
  cover: { width: 96, height: 112, borderRadius: radius.image - 3 },
  rowBody: { flex: 1, gap: 4, paddingVertical: 4, paddingRight: 4 },
  name: { fontFamily: fonts.text700, fontSize: 15, lineHeight: 19, color: c.ink },
  muted: { fontFamily: fonts.text600, color: c.muted, fontSize: 13 },
  price: { fontFamily: fonts.display700, fontSize: 16, color: c.ink },
  warning: { fontFamily: fonts.text600, fontSize: 13, color: c.warning },
  problem: { fontFamily: fonts.text600, fontSize: 13, lineHeight: 18, color: c.danger },
  rowActions: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginTop: "auto",
  },
  stepper: { flexDirection: "row", alignItems: "center", gap: 10 },
  stepButton: {
    width: 40,
    height: 40,
    borderRadius: 13,
    backgroundColor: c.surface,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: shadow.control,
  },
  quantity: { minWidth: 22, textAlign: "center", fontFamily: fonts.display700, fontSize: 16, color: c.ink },
  dimmed: { opacity: 0.4 },
  empty: { alignItems: "center", gap: 10, padding: 24, marginTop: 8 },
  emptyIcon: {
    width: 64,
    height: 64,
    borderRadius: 20,
    backgroundColor: c.tag,
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  emptyTitle: { fontFamily: fonts.display700, fontSize: 20, color: c.ink },
  footer: { gap: 14, padding: 18, marginTop: 4 },
}));
