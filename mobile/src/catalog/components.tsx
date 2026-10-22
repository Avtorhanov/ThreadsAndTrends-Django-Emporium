import { router } from "expo-router";
import { Image, Text, View } from "react-native";

import { CardGradient, PressScale } from "../components/ui";
import { formatKopecks } from "../lib/money";
import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius, space } from "../theme/tokens";
import { toneColor } from "../theme/tone";
import type { ProductCard as ProductCardData, ProductDetail } from "./catalogService";

/** Скидка в процентах от старой цены; null — если старой цены нет. */
export function discountPercent(price: number, compareAt: number | null): number | null {
  if (!compareAt || compareAt <= price) return null;
  return Math.round(((compareAt - price) * 100) / compareAt);
}

export function Price({
  price,
  compareAt,
  size = "card",
}: {
  price: number;
  compareAt: number | null;
  size?: "card" | "detail";
}) {
  const s = useStyles();
  return (
    <View style={s.priceRow}>
      <Text style={size === "detail" ? s.priceDetail : s.price}>{formatKopecks(price)}</Text>
      {compareAt ? (
        <Text
          style={size === "detail" ? s.oldPriceDetail : s.oldPrice}
          accessibilityLabel={`Старая цена ${formatKopecks(compareAt)}`}
        >
          {formatKopecks(compareAt)}
        </Text>
      ) : null}
    </View>
  );
}

export function DiscountBadge({ percent }: { percent: number | null }) {
  const s = useStyles();
  if (percent === null) return null;
  return (
    <View style={s.badge}>
      <Text style={s.badgeText}>−{percent}%</Text>
    </View>
  );
}

/** Плашка фото: тон товара — подложка, пока фото грузится (и вместо фото, если его нет). */
export function ProductImage({
  slug,
  uri,
  style,
  label,
}: {
  slug: string;
  uri: string | null | undefined;
  style: object;
  label?: string;
}) {
  const s = useStyles();
  const { dark } = useTheme();
  return (
    <View style={[s.image, style, { backgroundColor: toneColor(slug, dark) }]}>
      {uri ? (
        <Image
          source={{ uri }}
          style={s.imageFill}
          resizeMode="cover"
          accessibilityLabel={label}
          accessibilityIgnoresInvertColors
        />
      ) : (
        <Text style={s.noPhoto}>Нет фото</Text>
      )}
      <View pointerEvents="none" style={s.imageInset} />
    </View>
  );
}

/** Карточка ленты: радиус 26, фото 214 (на широкой сетке — пропорционально), цена Unbounded. */
export function ProductCard({ product }: { product: ProductCardData | ProductDetail }) {
  const s = useStyles();
  const percent = discountPercent(product.price_kopecks, product.compare_at_kopecks);
  const cover = "cover_url" in product ? product.cover_url : product.images[0]?.url;
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={`${product.name}, ${formatKopecks(product.price_kopecks)}${product.in_stock ? "" : ", нет в наличии"}`}
      onPress={() => router.push({ pathname: "/product/[slug]", params: { slug: product.slug } })}
      style={s.card}
    >
      <CardGradient />
      <View>
        <ProductImage slug={product.slug} uri={cover} style={s.cardImage} />
        <View style={s.badgePos}>
          <DiscountBadge percent={percent} />
        </View>
      </View>
      <View style={s.cardBody}>
        <Text style={s.name} numberOfLines={2}>
          {product.name}
        </Text>
        <Price price={product.price_kopecks} compareAt={product.compare_at_kopecks} />
        {product.in_stock ? null : <Text style={s.outOfStock}>Нет в наличии</Text>}
      </View>
    </PressScale>
  );
}

type SizeOption = { id: number; size: string; in_stock: boolean };

/** Размеры 56×48: выбранный — лаймовый с подсветкой, отсутствующий — зачёркнут. */
export function SizePicker({
  variants,
  selected,
  onSelect,
}: {
  variants: SizeOption[];
  selected: number | null;
  onSelect: (id: number) => void;
}) {
  const s = useStyles();
  return (
    <View style={s.sizes} accessibilityRole="radiogroup" accessibilityLabel="Размер">
      {variants.map((variant) => {
        const on = variant.id === selected;
        return (
          <PressScale
            key={variant.id}
            accessibilityRole="radio"
            accessibilityLabel={variant.in_stock ? variant.size : `${variant.size}, нет в наличии`}
            accessibilityState={{ selected: on, disabled: !variant.in_stock }}
            disabled={!variant.in_stock}
            onPress={() => onSelect(variant.id)}
            scale={0.94}
            style={[s.size, on && s.sizeOn, !variant.in_stock && s.sizeOff]}
          >
            <Text style={[s.sizeText, on && s.sizeTextOn, !variant.in_stock && s.sizeTextOff]}>
              {variant.size}
            </Text>
          </PressScale>
        );
      })}
    </View>
  );
}

const useStyles = makeStyles(({ c, shadow, dark }) => ({
  priceRow: { flexDirection: "row", alignItems: "baseline", flexWrap: "wrap", columnGap: 6 },
  price: { fontFamily: fonts.display700, fontSize: 17, color: c.ink },
  priceDetail: { fontFamily: fonts.display700, fontSize: 24, color: c.ink },
  oldPrice: {
    fontFamily: fonts.text600,
    fontSize: 12,
    color: c.strike,
    textDecorationLine: "line-through",
  },
  oldPriceDetail: {
    fontFamily: fonts.text600,
    fontSize: 15,
    color: c.strike,
    textDecorationLine: "line-through",
  },
  badge: {
    height: 24,
    paddingHorizontal: 9,
    borderRadius: radius.badge,
    backgroundColor: c.segOnBg,
    justifyContent: "center",
    boxShadow: "0 6px 12px -6px rgba(0,0,0,.5)",
  },
  badgeText: { fontFamily: fonts.text800, fontSize: 12, color: c.segOnInk },
  badgePos: { position: "absolute", left: 8, top: 8 },
  image: { overflow: "hidden", alignItems: "center", justifyContent: "center" },
  imageFill: { position: "absolute", top: 0, left: 0, right: 0, bottom: 0 },
  imageInset: {
    position: "absolute",
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    borderRadius: radius.image,
    boxShadow: shadow.imageInset,
  },
  noPhoto: { fontFamily: fonts.text700, fontSize: 13, color: dark ? c.muted : c.brand, opacity: 0.7 },
  card: {
    flex: 1,
    padding: space.cardPad,
    paddingBottom: 16,
    gap: 12,
    borderRadius: radius.card,
    backgroundColor: c.card,
    boxShadow: shadow.card,
  },
  cardImage: { width: "100%", aspectRatio: 0.82, borderRadius: radius.image },
  cardBody: { paddingHorizontal: space.cardTextPad, gap: 6 },
  name: { fontFamily: fonts.text700, fontSize: 15, lineHeight: 19, color: c.ink },
  outOfStock: { fontFamily: fonts.text700, fontSize: 12, color: c.muted },
  sizes: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  size: {
    minWidth: 56,
    height: 48,
    paddingHorizontal: 14,
    borderRadius: radius.control,
    backgroundColor: c.surface,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: shadow.control,
  },
  sizeOn: {
    backgroundColor: c.accent,
    boxShadow: "0 12px 22px -10px rgba(130,180,0,.85), inset 0 1px 0 rgba(255,255,255,.5)",
  },
  sizeOff: { opacity: 0.45 },
  sizeText: { fontFamily: fonts.text800, fontSize: 15, color: c.ink },
  sizeTextOn: { color: c.onAccent },
  sizeTextOff: { textDecorationLine: "line-through" },
}));
