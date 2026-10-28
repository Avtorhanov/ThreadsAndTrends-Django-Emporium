import { router, useLocalSearchParams, useNavigation } from "expo-router";
import { useCallback, useEffect, useRef, useState } from "react";
import {
  type NativeScrollEvent,
  type NativeSyntheticEvent,
  ScrollView,
  Text,
  useWindowDimensions,
  View,
} from "react-native";
import Animated, {
  FadeIn,
  FadeInDown,
  useAnimatedStyle,
  useReducedMotion,
  useSharedValue,
  withDelay,
  withTiming,
} from "react-native-reanimated";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { useAuth } from "../../../src/auth/AuthProvider";
import { useCart } from "../../../src/cart/CartProvider";
import { AskPanel } from "../../../src/catalog/AskPanel";
import { InCartBadge, Price, ProductImage, SizePicker, StatusPill } from "../../../src/catalog/components";
import { useProduct } from "../../../src/catalog/hooks";
import { FillButton } from "../../../src/components/FillButton";
import { useContentWidth } from "../../../src/components/layout";
import { Button, IconButton, LinkButton, Loading, Message } from "../../../src/components/ui";
import { useSubmit } from "../../../src/hooks/useSubmit";
import { formatKopecks } from "../../../src/lib/money";
import { useSheetDepth } from "../../../src/navigation/SheetDepth";
import { fonts } from "../../../src/theme/fonts";
import { ease, motion, REDUCED_FADE_MS } from "../../../src/theme/motion";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";
import { radius, size } from "../../../src/theme/tokens";
import { toneColor } from "../../../src/theme/tone";

const { stagger } = motion.detailOpen;

/** Блоки под фото появляются по очереди (120/180/240/300 мс); при «Уменьшить движение» — сразу. */
function rise(index: number, reduced: boolean) {
  if (reduced) return FadeIn.duration(REDUCED_FADE_MS);
  return FadeInDown.delay(stagger[index] ?? 0)
    .duration(450)
    .withInitialValues({ opacity: 0, transform: [{ translateY: 16 }] })
    .easing(ease.out);
}

/**
 * Карточка товара — лист снизу: сдвиг 102 % → 0 за 420 мс, скругление 36 → 0, каталог позади
 * уменьшается и бледнеет (SheetDepth). Закрытие — та же анимация в обратную сторону.
 */
export default function ProductScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const s = useStyles();
  const { dark } = useTheme();
  const insets = useSafeAreaInsets();
  const reduced = useReducedMotion();
  const { height } = useWindowDimensions();
  const navigation = useNavigation();
  const depth = useSheetDepth();

  const { data: product, loading, error, reload } = useProduct(slug);
  const contentWidth = useContentWidth();
  const wide = contentWidth >= 820;
  const heroWidth = (wide ? Math.floor(contentWidth / 2) : contentWidth) - 24;
  const heroHeight = wide ? heroWidth : size.detailHero;

  const [selected, setSelected] = useState<number | null>(null);
  const [added, setAdded] = useState(false);
  const [page, setPage] = useState(0);
  const cart = useCart();
  const { status } = useAuth();
  // Сколько единиц товара уже в корзине — метка «В корзине» под названием.
  const inCart = product
    ? (cart.cart?.items ?? []).filter((line) => line.product?.slug === product.slug).reduce((n, line) => n + line.quantity, 0)
    : 0;
  const addToCart = useSubmit(async (variantId: number, priceKopecks: number) => {
    setAdded(false);
    await cart.add(variantId, priceKopecks);
    setAdded(true);
  });

  // 0 — лист внизу, 1 — открыт.
  const open = useSharedValue(0);
  const closing = useRef(false);
  useEffect(() => {
    const duration = reduced ? REDUCED_FADE_MS : motion.detailOpen.ms;
    open.value = withTiming(1, { duration, easing: ease.out });
    depth.value = withTiming(1, { duration, easing: ease.out });
    // Экран могут убрать и без beforeRemove (переход на вкладку, сброс стека) — каталог возвращается.
    return () => {
      depth.value = withTiming(0, { duration: REDUCED_FADE_MS });
    };
  }, [open, depth, reduced]);

  // Любое закрытие (кнопка, жест, системная «Назад») сначала уводит лист вниз.
  useEffect(
    () =>
      navigation.addListener("beforeRemove", (event) => {
        if (closing.current) return;
        event.preventDefault();
        closing.current = true;
        const duration = reduced ? REDUCED_FADE_MS : motion.detailOpen.ms - 80;
        depth.value = withTiming(0, { duration, easing: ease.out });
        open.value = withTiming(0, { duration, easing: ease.out });
        setTimeout(() => navigation.dispatch(event.data.action), duration);
      }),
    [navigation, open, depth, reduced],
  );
  const close = useCallback(() => {
    if (router.canGoBack()) router.back();
    else router.replace("/");
  }, []);

  const sheet = useAnimatedStyle(() =>
    reduced
      ? { opacity: open.value }
      : {
          transform: [{ translateY: (1 - open.value) * height * 1.02 }],
          borderTopLeftRadius: (1 - open.value) * radius.sheet,
          borderTopRightRadius: (1 - open.value) * radius.sheet,
        },
  );
  const heroScale = useSharedValue(reduced ? 1 : motion.detailOpen.hero.fromScale);
  useEffect(() => {
    if (reduced) return;
    heroScale.value = withDelay(
      motion.detailOpen.hero.delay,
      withTiming(1, { duration: motion.detailOpen.hero.ms, easing: ease.out }),
    );
  }, [heroScale, reduced]);
  const hero = useAnimatedStyle(() => ({ transform: [{ scale: heroScale.value }] }));

  const onGalleryScroll = (event: NativeSyntheticEvent<NativeScrollEvent>) => {
    setPage(Math.round(event.nativeEvent.contentOffset.x / Math.max(1, heroWidth)));
  };

  // Один вариант «Без размера» — выбор размера не показывается.
  const hasSizes = product ? product.variants.some((variant) => variant.size !== "") : false;
  const variantId = product ? (hasSizes ? selected : (product.variants[0]?.id ?? null)) : null;
  const variant = product?.variants.find((item) => item.id === variantId);
  const ctaTitle = !product?.in_stock ? "Нет в наличии" : variantId === null ? "Выберите размер" : "В корзину";

  const images = product?.images ?? [];

  return (
    <Animated.View style={[s.sheet, sheet]}>
      <ScrollView
        contentContainerStyle={[s.scroll, wide && s.scrollWide, { paddingBottom: 140 + insets.bottom }]}
        showsVerticalScrollIndicator={false}
      >
        <Animated.View
          style={[s.hero, { width: heroWidth, height: heroHeight, backgroundColor: toneColor(slug, dark) }, hero]}
        >
          {images.length ? (
            <ScrollView
              horizontal
              pagingEnabled
              showsHorizontalScrollIndicator={false}
              onMomentumScrollEnd={onGalleryScroll}
              accessibilityLabel={`Фото товара, ${images.length}`}
            >
              {images.map((image) => (
                <ProductImage
                  key={image.id}
                  slug={slug}
                  uri={image.url}
                  label={product?.name}
                  style={{ width: heroWidth, height: heroHeight, borderRadius: radius.hero }}
                />
              ))}
            </ScrollView>
          ) : (
            <ProductImage
              slug={slug}
              uri={null}
              style={{ width: heroWidth, height: heroHeight, borderRadius: radius.hero }}
            />
          )}
          <IconButton
            icon="back"
            label="Назад"
            variant="glass"
            size={48}
            onPress={close}
            style={[s.back, { top: Math.max(insets.top, 12) + 18 }]}
          />
          {images.length > 1 ? (
            <View style={s.dots} accessibilityElementsHidden importantForAccessibility="no-hide-descendants">
              {images.map((image, index) => (
                <View key={image.id} style={[s.dot, index === page && s.dotOn]} />
              ))}
            </View>
          ) : null}
        </Animated.View>

        <View style={[s.body, wide && s.bodyWide]}>
          {!product ? (
            <View style={s.state}>
              {loading ? <Loading /> : null}
              <Message text={error ?? (loading ? null : "Товар не найден.")} />
              {error ? <Button title="Повторить" variant="secondary" onPress={reload} /> : null}
            </View>
          ) : (
            <>
              <Animated.View entering={rise(0, reduced)} style={s.block}>
                <View style={s.tag}>
                  <Text style={s.tagText}>{product.category.name}</Text>
                </View>
                <Text style={s.title} accessibilityRole="header">
                  {product.name}
                </Text>
                {product.status ? <StatusPill status={product.status} /> : null}
                <Price price={product.price_kopecks} compareAt={product.compare_at_kopecks} size="detail" />
                {inCart > 0 ? <InCartBadge label={`В корзине · ${inCart} шт.`} /> : null}
                {product.in_stock ? null : <Text style={s.outOfStock}>Нет в наличии</Text>}
              </Animated.View>

              {hasSizes ? (
                <Animated.View entering={rise(1, reduced)} style={s.block}>
                  <Text style={s.caps}>Размер</Text>
                  <SizePicker
                    variants={product.variants}
                    selected={selected}
                    onSelect={(id) => {
                      setSelected(id);
                      setAdded(false);
                    }}
                  />
                </Animated.View>
              ) : null}

              {product.description ? (
                <Animated.Text entering={rise(2, reduced)} style={s.description}>
                  {product.description}
                </Animated.Text>
              ) : null}
            </>
          )}
        </View>
      </ScrollView>

      {product ? (
        <Animated.View
          entering={rise(3, reduced)}
          style={[s.cta, wide && s.ctaWide, { paddingBottom: Math.max(insets.bottom, 12) + 18 }]}
        >
          {product.price_kopecks === null ? (
            <AskPanel name={product.name} slug={product.slug} />
          ) : (
            <>
              <Message text={addToCart.error} />
              <FillButton
                title={ctaTitle}
                doneTitle="Добавлено в корзину"
                done={added}
                trailing={formatKopecks(product.price_kopecks)}
                loading={addToCart.loading}
                disabled={!variant?.in_stock}
                onPress={() => {
                  if (added) router.navigate("/cart");
                  else if (variant && product.price_kopecks !== null) {
                    void addToCart.submit(variant.id, product.price_kopecks);
                  }
                }}
              />
              {added ? (
                <LinkButton title="Перейти в корзину" onPress={() => router.navigate("/cart")} />
              ) : (
                // «Купить сейчас»: оформление только этого размера, корзина не меняется.
                <Button
                  title="Купить сейчас"
                  variant="accent"
                  disabled={!variant?.in_stock}
                  onPress={() => {
                    if (!variant) return;
                    if (status !== "signedIn") router.push("/sign-in");
                    else router.push({ pathname: "/checkout", params: { variant: String(variant.id), qty: "1" } });
                  }}
                />
              )}
            </>
          )}
        </Animated.View>
      ) : null}
    </Animated.View>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  sheet: {
    flex: 1,
    backgroundColor: c.bg,
    overflow: "hidden",
    boxShadow: "0 -20px 40px -20px rgba(0,0,0,.45)",
  },
  scroll: { alignItems: "center" },
  scrollWide: { flexDirection: "row", alignItems: "flex-start", justifyContent: "center", gap: 12 },
  hero: {
    marginTop: 12,
    borderRadius: radius.hero,
    overflow: "hidden",
    boxShadow: shadow.card,
  },
  back: { position: "absolute", left: 14 },
  dots: {
    position: "absolute",
    bottom: 18,
    alignSelf: "center",
    flexDirection: "row",
    gap: 6,
  },
  dot: { width: 6, height: 6, borderRadius: 3, backgroundColor: c.ink, opacity: 0.3 },
  dotOn: { width: 22, opacity: 1 },
  body: { width: "100%", paddingHorizontal: 24, paddingTop: 20, gap: 18 },
  bodyWide: { flex: 1, maxWidth: 560, paddingTop: 24 },
  state: { alignItems: "center", gap: 16, paddingVertical: 24 },
  block: { gap: 10 },
  tag: {
    alignSelf: "flex-start",
    height: 26,
    paddingHorizontal: 10,
    borderRadius: radius.tag,
    backgroundColor: c.tag,
    justifyContent: "center",
  },
  tagText: { fontFamily: fonts.text800, fontSize: 12, color: c.tagInk },
  title: { fontFamily: fonts.display700, fontSize: 23, lineHeight: 27, letterSpacing: -0.4, color: c.ink },
  outOfStock: { fontFamily: fonts.text700, fontSize: 14, color: c.danger },
  caps: {
    fontFamily: fonts.text800,
    fontSize: 13,
    letterSpacing: 1.3,
    textTransform: "uppercase",
    color: c.muted,
  },
  description: { fontFamily: fonts.text500, fontSize: 15, lineHeight: 22, color: c.muted },
  cta: {
    position: "absolute",
    left: 0,
    right: 0,
    bottom: 0,
    paddingHorizontal: 20,
    paddingTop: 12,
    gap: 4,
    backgroundColor: c.bg,
  },
  ctaWide: { left: "50%", maxWidth: 600 },
}));
