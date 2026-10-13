import { Stack, useLocalSearchParams } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Image,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  useWindowDimensions,
  View,
} from "react-native";

import { Price } from "../../../src/catalog/components";
import { useProduct } from "../../../src/catalog/hooks";
import { colors, radius, spacing } from "../../../src/components/theme";
import { Button, Message } from "../../../src/components/ui";

export default function ProductScreen() {
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { data: product, loading, error, reload } = useProduct(slug);
  const { width } = useWindowDimensions();
  const [selected, setSelected] = useState<number | null>(null);

  if (loading && !product) {
    return (
      <View style={styles.center}>
        <ActivityIndicator color={colors.primary} />
      </View>
    );
  }
  if (!product) {
    return (
      <View style={styles.center}>
        <Message text={error ?? "Товар не найден."} />
        <Button title="Повторить" variant="secondary" onPress={reload} />
      </View>
    );
  }

  // Один вариант «Без размера» — выбор размера не показывается.
  const hasSizes = product.variants.some((variant) => variant.size !== "");

  return (
    <>
      <Stack.Screen options={{ title: product.name }} />
      <ScrollView contentContainerStyle={styles.content}>
        {product.images.length ? (
          <ScrollView horizontal pagingEnabled showsHorizontalScrollIndicator={false}>
            {product.images.map((image) => (
              <Image
                key={image.id}
                source={{ uri: image.url }}
                style={{ width, height: width }}
                resizeMode="cover"
                accessibilityLabel={product.name}
              />
            ))}
          </ScrollView>
        ) : (
          <View style={[styles.noPhoto, { height: width * 0.6 }]}>
            <Text style={styles.muted}>Нет фото</Text>
          </View>
        )}

        <View style={styles.body}>
          <Text style={styles.category}>{product.category.name}</Text>
          <Text style={styles.title}>{product.name}</Text>
          <Price price={product.price_kopecks} compareAt={product.compare_at_kopecks} large />
          <Text style={product.in_stock ? styles.inStock : styles.outOfStock}>
            {product.in_stock ? "В наличии" : "Нет в наличии"}
          </Text>

          {hasSizes ? (
            <View style={styles.sizes}>
              <Text style={styles.muted}>Размер</Text>
              <View style={styles.chips}>
                {product.variants.map((variant) => (
                  <Pressable
                    key={variant.id}
                    accessibilityRole="button"
                    accessibilityState={{ selected: selected === variant.id, disabled: !variant.in_stock }}
                    disabled={!variant.in_stock}
                    onPress={() => setSelected(variant.id)}
                    style={[
                      styles.chip,
                      selected === variant.id && styles.chipSelected,
                      !variant.in_stock && styles.chipDisabled,
                    ]}
                  >
                    <Text
                      style={[
                        styles.chipText,
                        selected === variant.id && styles.chipTextSelected,
                        !variant.in_stock && styles.chipTextDisabled,
                      ]}
                    >
                      {variant.size}
                    </Text>
                  </Pressable>
                ))}
              </View>
            </View>
          ) : null}

          {product.description ? <Text style={styles.description}>{product.description}</Text> : null}
        </View>
      </ScrollView>
    </>
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
  content: { backgroundColor: colors.background, flexGrow: 1 },
  noPhoto: { alignItems: "center", justifyContent: "center", backgroundColor: colors.surface },
  body: { padding: spacing.lg, gap: spacing.sm },
  category: { color: colors.muted, fontSize: 14 },
  title: { fontSize: 22, fontWeight: "700", color: colors.text },
  muted: { color: colors.muted, fontSize: 14 },
  inStock: { color: colors.success, fontSize: 14 },
  outOfStock: { color: colors.danger, fontSize: 14 },
  sizes: { gap: spacing.sm, marginTop: spacing.sm },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    minWidth: 48,
    alignItems: "center",
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
    borderRadius: radius,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipSelected: { borderColor: colors.primary, backgroundColor: colors.primary },
  chipDisabled: { opacity: 0.45 },
  chipText: { fontSize: 15, color: colors.text },
  chipTextSelected: { color: colors.primaryText },
  chipTextDisabled: { textDecorationLine: "line-through" },
  description: { fontSize: 15, lineHeight: 22, color: colors.text, marginTop: spacing.md },
});
