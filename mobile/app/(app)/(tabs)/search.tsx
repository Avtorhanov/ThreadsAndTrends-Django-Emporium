import { useLocalSearchParams } from "expo-router";
import { useEffect, useMemo, useRef, useState } from "react";
import { FlatList, Text, TextInput, View } from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import type { ProductQuery } from "../../../src/catalog/catalogService";
import { ProductCard } from "../../../src/catalog/components";
import {
  EMPTY_FILTERS,
  FiltersBar,
  type FiltersDraft,
  filtersChanged,
} from "../../../src/catalog/FiltersBar";
import { useCategories, useProductFeed } from "../../../src/catalog/hooks";
import { Icon } from "../../../src/components/Icon";
import { useGridColumns } from "../../../src/components/layout";
import { Segmented } from "../../../src/components/Segmented";
import { Button, Loading, Message, PressScale, ScreenTitle, TAB_BAR_SPACE } from "../../../src/components/ui";
import { useDebouncedValue } from "../../../src/hooks/useDebouncedValue";
import { parseRubles } from "../../../src/lib/money";
import { useTabPress } from "../../../src/navigation/useTabPress";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";
import { radius, size, space } from "../../../src/theme/tokens";

/** Поля фильтра → параметры API (цены — копейки). Неверная цена не уходит в запрос. */
function toQuery(category: string, draft: FiltersDraft): { query: ProductQuery; priceError: string | null } {
  const priceMin = parseRubles(draft.priceFrom);
  const priceMax = parseRubles(draft.priceTo);
  let priceError: string | null = null;
  if (priceMin === undefined || priceMax === undefined) priceError = "Цена — число рублей, например 1500.";
  else if (priceMin !== null && priceMax !== null && priceMin > priceMax) priceError = "«До» меньше, чем «от».";
  const valid = priceError === null;
  return {
    priceError,
    query: {
      category: category || undefined,
      q: draft.q.trim() || undefined,
      priceMin: valid ? (priceMin ?? undefined) : undefined,
      priceMax: valid ? (priceMax ?? undefined) : undefined,
      inStock: draft.inStock || undefined,
      sort: draft.sort || undefined,
    },
  };
}

/** Вкладка «Поиск»: поле с фокусом, категории, сортировка и цена, сетка результатов. */
export default function SearchScreen() {
  const s = useStyles();
  const { c } = useTheme();
  const params = useLocalSearchParams<{ q?: string; category?: string; filters?: string }>();
  const [draft, setDraft] = useState<FiltersDraft>({ ...EMPTY_FILTERS, q: params.q ?? "" });
  const [category, setCategory] = useState(params.category ?? "");
  const [showFilters, setShowFilters] = useState(params.filters === "1");
  const input = useRef<TextInput>(null);
  const [focused, setFocused] = useState(false);
  const categories = useCategories();
  const columns = useGridColumns();

  // Переход из шапки каталога с запросом или кнопкой фильтров — подхватываем параметры.
  useEffect(() => {
    if (params.q !== undefined) setDraft((prev) => ({ ...prev, q: params.q ?? "" }));
  }, [params.q]);
  useEffect(() => {
    if (params.category !== undefined) setCategory(params.category);
  }, [params.category]);
  useEffect(() => {
    if (params.filters === "1") setShowFilters(true);
  }, [params.filters]);
  useTabPress(() => input.current?.focus());

  // Запрос уходит после паузы во вводе, а не на каждую букву.
  const debounced = useDebouncedValue(draft, 400);
  const { query, priceError } = useMemo(() => toQuery(category, debounced), [category, debounced]);
  const feed = useProductFeed(query);
  const filtered = Boolean(query.q || query.priceMin || query.priceMax || query.inStock);
  const changed = filtersChanged(draft);

  const segments = [
    { value: "", label: "Все" },
    ...(categories.data ?? []).map((root) => ({ value: root.slug, label: root.name })),
  ];

  return (
    <SafeAreaView style={s.screen} edges={["top"]}>
      <FlatList
        // Число колонок нельзя менять у смонтированного списка — новый key пересоздаёт его.
        key={`grid-${columns}`}
        data={feed.items}
        keyExtractor={(item) => String(item.id)}
        numColumns={columns}
        columnWrapperStyle={s.row}
        contentContainerStyle={s.content}
        keyboardShouldPersistTaps="handled"
        keyboardDismissMode="on-drag"
        refreshing={feed.refreshing}
        onRefresh={feed.refresh}
        ListHeaderComponent={
          <View style={s.head}>
            <ScreenTitle overline="Поиск" title="Найти товар" />
            <View style={s.searchRow}>
              <View style={[s.search, focused && s.searchFocused]}>
                <Icon name="search" size={20} color={c.muted} />
                <TextInput
                  ref={input}
                  onFocus={() => setFocused(true)}
                  onBlur={() => setFocused(false)}
                  value={draft.q}
                  onChangeText={(q) => setDraft((prev) => ({ ...prev, q }))}
                  placeholder="Футболка, кеды, панама…"
                  placeholderTextColor={c.muted}
                  selectionColor={c.brand}
                  accessibilityLabel="Поиск товаров"
                  returnKeyType="search"
                  autoCorrect={false}
                  autoFocus={!params.q && params.filters !== "1"}
                  maxLength={100}
                  style={s.searchInput}
                />
                {draft.q ? (
                  <PressScale
                    accessibilityRole="button"
                    accessibilityLabel="Очистить поиск"
                    onPress={() => setDraft((prev) => ({ ...prev, q: "" }))}
                    hitSlop={6}
                    style={s.clear}
                  >
                    <Icon name="close" size={18} color={c.muted} />
                  </PressScale>
                ) : null}
              </View>
              <PressScale
                accessibilityRole="button"
                accessibilityLabel={showFilters ? "Скрыть фильтры" : "Фильтры и сортировка"}
                accessibilityState={{ expanded: showFilters }}
                onPress={() => setShowFilters((value) => !value)}
                scale={0.92}
                style={[s.filterButton, (showFilters || changed) && s.filterButtonOn]}
              >
                <Icon name="filter" size={20} color={c.onAccent} strokeWidth={2.2} />
              </PressScale>
            </View>
            <Segmented
              label="Категории"
              segments={segments}
              value={category}
              onChange={setCategory}
              scrollable={segments.length > 4}
            />
            {showFilters ? <FiltersBar value={draft} onChange={setDraft} priceError={priceError} /> : null}
            {feed.count !== null ? <Text style={s.count}>Найдено товаров: {feed.count}</Text> : null}
          </View>
        }
        renderItem={({ item }) => (
          <View style={[s.cell, { maxWidth: `${100 / columns}%` as `${number}%` }]}>
            <ProductCard product={item} />
          </View>
        )}
        onEndReached={feed.loadMore}
        onEndReachedThreshold={0.5}
        ListEmptyComponent={
          feed.loading || feed.error ? null : (
            <Text style={s.empty}>
              {filtered ? "Ничего не нашлось. Измените запрос или фильтры." : "Здесь пока нет товаров."}
            </Text>
          )
        }
        ListFooterComponent={
          <View style={s.footer}>
            {feed.loading && !feed.refreshing ? <Loading /> : null}
            <Message text={feed.error} />
            {feed.error ? <Button title="Повторить" variant="secondary" onPress={feed.refresh} /> : null}
          </View>
        }
      />
    </SafeAreaView>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  screen: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: space.feedSide, paddingBottom: TAB_BAR_SPACE, gap: space.gridGap },
  head: { gap: 14, paddingHorizontal: 8, paddingTop: 8, paddingBottom: 6 },
  searchRow: { flexDirection: "row", alignItems: "center", gap: 10 },
  searchFocused: { borderColor: c.brand },
  search: {
    borderWidth: 1.5,
    borderColor: "transparent",
    flex: 1,
    height: size.searchHeight,
    flexDirection: "row",
    alignItems: "center",
    gap: 10,
    paddingLeft: 16,
    paddingRight: 8,
    borderRadius: radius.search,
    backgroundColor: c.surface,
    boxShadow: shadow.control,
  },
  searchInput: {
    outlineWidth: 0, // фокус в браузере — рамкой поля, а не системной обводкой
    flex: 1,
    minWidth: 0,
    height: size.searchHeight,
    fontFamily: fonts.text600,
    fontSize: 15,
    color: c.ink,
  },
  clear: { width: 36, height: 36, alignItems: "center", justifyContent: "center" },
  filterButton: {
    width: size.searchHeight,
    height: size.searchHeight,
    borderRadius: radius.search,
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
    opacity: 0.85,
  },
  filterButtonOn: { opacity: 1, boxShadow: shadow.accentGlow },
  row: { gap: space.gridGap },
  cell: { flex: 1 },
  count: { fontFamily: fonts.text600, fontSize: 13, color: c.muted },
  footer: { gap: 16, paddingVertical: 16 },
  empty: { fontFamily: fonts.text600, color: c.muted, textAlign: "center", marginTop: 32 },
}));
