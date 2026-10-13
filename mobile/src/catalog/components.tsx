import { router } from "expo-router";
import { Image, Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../components/theme";
import { formatKopecks } from "../lib/money";
import type { ProductCard } from "./catalogService";

export function Price({ price, compareAt, large }: { price: number; compareAt: number | null; large?: boolean }) {
  return (
    <View style={styles.priceRow}>
      <Text style={[styles.price, large && styles.priceLarge]}>{formatKopecks(price)}</Text>
      {compareAt ? <Text style={styles.oldPrice}>{formatKopecks(compareAt)}</Text> : null}
    </View>
  );
}

export function ProductTile({ product }: { product: ProductCard }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={product.name}
      style={({ pressed }) => [styles.tile, pressed && styles.pressed]}
      onPress={() => router.push({ pathname: "/product/[slug]", params: { slug: product.slug } })}
    >
      {product.cover_url ? (
        <Image source={{ uri: product.cover_url }} style={styles.cover} resizeMode="cover" />
      ) : (
        <View style={[styles.cover, styles.coverEmpty]}>
          <Text style={styles.coverEmptyText}>Нет фото</Text>
        </View>
      )}
      <View style={styles.tileBody}>
        <Text style={styles.name} numberOfLines={2}>
          {product.name}
        </Text>
        <Price price={product.price_kopecks} compareAt={product.compare_at_kopecks} />
        {product.in_stock ? null : <Text style={styles.outOfStock}>Нет в наличии</Text>}
      </View>
    </Pressable>
  );
}

const styles = StyleSheet.create({
  priceRow: { flexDirection: "row", alignItems: "baseline", flexWrap: "wrap", gap: spacing.sm },
  price: { fontSize: 16, fontWeight: "700", color: colors.text },
  priceLarge: { fontSize: 24 },
  oldPrice: { fontSize: 14, color: colors.muted, textDecorationLine: "line-through" },
  tile: {
    flex: 1,
    backgroundColor: colors.surface,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    overflow: "hidden",
  },
  pressed: { opacity: 0.7 },
  cover: { width: "100%", aspectRatio: 1, backgroundColor: colors.background },
  coverEmpty: { alignItems: "center", justifyContent: "center" },
  coverEmptyText: { color: colors.muted, fontSize: 13 },
  tileBody: { padding: spacing.sm, gap: spacing.xs },
  name: { fontSize: 14, color: colors.text },
  outOfStock: { fontSize: 12, color: colors.danger },
});
