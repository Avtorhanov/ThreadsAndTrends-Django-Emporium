import { useRef, useState } from "react";
import { type FlatList, RefreshControl, Text, View } from "react-native";
import Animated, {
  useAnimatedScrollHandler,
  useDerivedValue,
  useReducedMotion,
  useSharedValue,
  withTiming,
} from "react-native-reanimated";

import type { ProductCard as ProductCardData } from "../../../src/catalog/catalogService";
import { ProductCard } from "../../../src/catalog/components";
import { FeedFade, GlassHeader, useHeaderHeight } from "../../../src/catalog/GlassHeader";
import { useCategories, useProductFeed } from "../../../src/catalog/hooks";
import { InstallHint } from "../../../src/components/InstallHint";
import { useGridColumns } from "../../../src/components/layout";
import { Segmented } from "../../../src/components/Segmented";
import { Button, Loading, Message, ScreenTitle, TAB_BAR_SPACE } from "../../../src/components/ui";
import { fonts } from "../../../src/theme/fonts";
import { ease, motion } from "../../../src/theme/motion";
import { useTabPress } from "../../../src/navigation/useTabPress";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";
import { space } from "../../../src/theme/tokens";

const ALL = "";
const { collapseAt, expandBelow } = motion.headerCollapse;
// Сколько остаётся проехать плавно при возврате наверх из глубины ленты.
const SHORT_RETURN = 480;

export default function CatalogScreen() {
  const s = useStyles();
  const { c } = useTheme();
  const reduced = useReducedMotion();
  const headerHeight = useHeaderHeight();
  const columns = useGridColumns();
  const categories = useCategories();
  const [category, setCategory] = useState<string>(ALL);
  const [search, setSearch] = useState("");
  const feed = useProductFeed({ category: category || undefined });
  const list = useRef<FlatList<ProductCardData>>(null);

  // Шапка: свёрнута после 24 px прокрутки, разворачивается выше 8 px (гистерезис — не дёргается).
  const collapsed = useSharedValue(0);
  const progress = useDerivedValue(() =>
    reduced
      ? collapsed.value
      : withTiming(collapsed.value, { duration: motion.headerCollapse.ms, easing: ease.soft }),
  );
  const scrollY = useSharedValue(0);
  const onScroll = useAnimatedScrollHandler((event) => {
    const y = event.contentOffset.y;
    scrollY.value = y;
    if (collapsed.value === 0 && y > collapseAt) collapsed.value = 1;
    else if (collapsed.value === 1 && y < expandBelow) collapsed.value = 0;
  });

  /**
   * Наверх без «перемотки» через всю ленту: если прокручено далеко, лента мгновенно встаёт на
   * короткое расстояние от начала, а оставшийся путь проходит плавно — как после лёгкой прокрутки.
   */
  const scrollTop = () => {
    const target = list.current;
    if (!target) return;
    const y = scrollY.value;
    if (reduced || y <= SHORT_RETURN) {
      target.scrollToOffset({ offset: 0, animated: !reduced });
      return;
    }
    target.scrollToOffset({ offset: SHORT_RETURN, animated: false });
    requestAnimationFrame(() => target.scrollToOffset({ offset: 0, animated: true }));
  };

  // Нажатие на название в шапке и повторное нажатие на вкладку «Каталог» — наверх.
  useTabPress(scrollTop);

  const roots = categories.data ?? [];
  const segments = [{ value: ALL, label: "Все" }, ...roots.map((root) => ({ value: root.slug, label: root.name }))];
  const current = roots.find((root) => root.slug === category);

  return (
    <View style={s.screen}>
      <Animated.FlatList
        ref={list}
        // Число колонок нельзя менять у смонтированного списка — новый key пересоздаёт его.
        key={`grid-${columns}`}
        data={feed.items}
        keyExtractor={(item) => String(item.id)}
        numColumns={columns}
        columnWrapperStyle={s.row}
        contentContainerStyle={[s.content, { paddingTop: headerHeight + 4 }]}
        onScroll={onScroll}
        scrollEventThrottle={16}
        keyboardShouldPersistTaps="handled"
        refreshControl={
          <RefreshControl
            refreshing={feed.refreshing}
            onRefresh={() => {
              feed.refresh();
              categories.reload();
            }}
            progressViewOffset={headerHeight}
            tintColor={c.ink}
          />
        }
        ListHeaderComponent={
          <View style={s.head}>
            <InstallHint />
            <ScreenTitle overline="Каталог" title={current?.name ?? "Все товары"} />
            {feed.count !== null ? <Text style={s.count}>Товаров: {feed.count}</Text> : null}
            <Message text={categories.error} />
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
          feed.loading || feed.error ? null : <Text style={s.empty}>Здесь пока нет товаров.</Text>
        }
        ListFooterComponent={
          <View style={s.footer}>
            {feed.loading && !feed.refreshing ? <Loading /> : null}
            <Message text={feed.error} />
            {feed.error ? <Button title="Повторить" variant="secondary" onPress={feed.refresh} /> : null}
          </View>
        }
      />
      <FeedFade progress={progress} />
      <GlassHeader
        progress={progress}
        search={search}
        onSearchChange={setSearch}
        onTitlePress={scrollTop}
        categories={
          <Segmented
            label="Категории"
            segments={segments}
            value={category}
            onChange={(value) => {
              setCategory(value);
              scrollTop();
            }}
            scrollable={segments.length > 4}
          />
        }
      />
    </View>
  );
}

const useStyles = makeStyles(({ c }) => ({
  screen: { flex: 1, backgroundColor: c.bg },
  content: { paddingHorizontal: space.feedSide, paddingBottom: TAB_BAR_SPACE, gap: space.gridGap },
  head: { gap: 6, paddingHorizontal: 2, paddingBottom: 12 },
  row: { gap: space.gridGap },
  // Ячейка — доля ширины даже для последнего неполного ряда.
  cell: { flex: 1 },
  count: { fontFamily: fonts.text600, fontSize: 13, color: c.muted },
  footer: { gap: 16, paddingVertical: 16 },
  empty: { fontFamily: fonts.text600, color: c.muted, textAlign: "center", marginTop: 32 },
}));
