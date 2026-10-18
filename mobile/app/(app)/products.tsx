import { Stack, useLocalSearchParams } from "expo-router";
import { useMemo, useState } from "react";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import type { ProductQuery } from "../../src/catalog/catalogService";
import { EMPTY_FILTERS, FiltersBar, type FiltersDraft } from "../../src/catalog/FiltersBar";
import { ProductTile } from "../../src/catalog/components";
import { useProductFeed } from "../../src/catalog/hooks";
import { useGridColumns } from "../../src/components/layout";
import { colors, spacing } from "../../src/components/theme";
import { Button, Message } from "../../src/components/ui";
import { useDebouncedValue } from "../../src/hooks/useDebouncedValue";
import { parseRubles } from "../../src/lib/money";

/** Поля фильтра → параметры API (цены — копейки). Неверная цена не уходит в запрос. */
function toQuery(category: string | undefined, draft: FiltersDraft): { query: ProductQuery; priceError: string | null } {
  const priceMin = parseRubles(draft.priceFrom);
  const priceMax = parseRubles(draft.priceTo);
  let priceError: string | null = null;
  if (priceMin === undefined || priceMax === undefined) priceError = "Цена — число рублей, например 1500.";
  else if (priceMin !== null && priceMax !== null && priceMin > priceMax) priceError = "«До» меньше, чем «от».";
  const valid = priceError === null;
  return {
    priceError,
    query: {
      category,
      q: draft.q.trim() || undefined,
      priceMin: valid ? (priceMin ?? undefined) : undefined,
      priceMax: valid ? (priceMax ?? undefined) : undefined,
      inStock: draft.inStock || undefined,
      sort: draft.sort || undefined,
    },
  };
}

export default function ProductsScreen() {
  const params = useLocalSearchParams<{ category?: string; title?: string; q?: string }>();
  const [draft, setDraft] = useState<FiltersDraft>({ ...EMPTY_FILTERS, q: params.q ?? "" });
  // Запрос уходит после паузы во вводе, а не на каждую букву.
  const debounced = useDebouncedValue(draft, 400);
  const { query, priceError } = useMemo(
    () => toQuery(params.category || undefined, debounced),
    [params.category, debounced],
  );
  const feed = useProductFeed(query);
  const columns = useGridColumns();
  const filtered = Boolean(query.q || query.priceMin || query.priceMax || query.inStock);

  return (
    <>
      <Stack.Screen options={{ title: params.title || (params.q ? "Поиск" : "Все товары") }} />
      <FlatList
        // Число колонок нельзя менять у смонтированного списка — новый key пересоздаёт его.
        key={`grid-${columns}`}
        data={feed.items}
        keyExtractor={(item) => String(item.id)}
        numColumns={columns}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.content}
        keyboardShouldPersistTaps="handled"
        ListHeaderComponent={
          <View>
            <FiltersBar value={draft} onChange={setDraft} priceError={priceError} />
            {feed.count !== null ? (
              <Text style={styles.count}>Найдено товаров: {feed.count}</Text>
            ) : null}
          </View>
        }
        renderItem={({ item }) => (
          <View style={[styles.cell, { maxWidth: `${100 / columns}%` as `${number}%` }]}>
            <ProductTile product={item} />
          </View>
        )}
        onEndReached={feed.loadMore}
        onEndReachedThreshold={0.5}
        refreshing={feed.refreshing}
        onRefresh={feed.refresh}
        ListEmptyComponent={
          feed.loading || feed.error ? null : (
            <Text style={styles.empty}>
              {filtered ? "Ничего не нашлось. Измените запрос или фильтры." : "Здесь пока нет товаров."}
            </Text>
          )
        }
        ListFooterComponent={
          <View style={styles.footer}>
            {feed.loading && !feed.refreshing ? <ActivityIndicator color={colors.primary} /> : null}
            <Message text={feed.error} />
            {feed.error ? <Button title="Повторить" variant="secondary" onPress={feed.refresh} /> : null}
          </View>
        }
      />
    </>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background, flexGrow: 1 },
  row: { gap: spacing.md },
  // Ячейка — доля ширины даже для последнего неполного ряда.
  cell: { flex: 1 },
  count: { color: colors.muted, fontSize: 13 },
  footer: { gap: spacing.md, paddingVertical: spacing.md },
  empty: { color: colors.muted, textAlign: "center", marginTop: spacing.xl },
});
