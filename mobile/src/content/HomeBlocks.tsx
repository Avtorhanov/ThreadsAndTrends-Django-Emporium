import { Image, Pressable, ScrollView, Text, View } from "react-native";

import { ProductCard } from "../catalog/components";
import { Icon } from "../components/Icon";
import { useContentWidth } from "../components/layout";
import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius, space } from "../theme/tokens";
import type { HomeBlock } from "./contentService";

type Props = {
  blocks: HomeBlock[];
  /** Переход в категорию — фильтр ленты на этом же экране. */
  onCategory: (slug: string) => void;
};

/** Главная из блоков (панель → «Главная»): баннер, подборка, лента категорий, текст. */
export function HomeBlocks({ blocks, onCategory }: Props) {
  const s = useStyles();
  const { c } = useTheme();
  const width = useContentWidth();
  // Подборка — ряд с прокруткой: видно 2 карточки и край третьей (подсказка, что ряд листается).
  const cardWidth = Math.min(240, (width - space.feedSide * 2 - space.gridGap) / 2.15);

  if (blocks.length === 0) return null;
  return (
    <View style={s.blocks}>
      {blocks.map((block) => {
        if (block.kind === "banner") {
          const category = block.category;
          const body = (
            <View style={[s.banner, { backgroundColor: block.color }]}>
              <View style={s.bannerBody}>
                {block.title ? <Text style={[s.bannerTitle, { color: block.ink }]}>{block.title}</Text> : null}
                {block.text ? <Text style={[s.bannerText, { color: block.ink }]}>{block.text}</Text> : null}
                {category ? (
                  <View style={s.bannerMore}>
                    <Text style={[s.bannerMoreText, { color: block.ink }]}>{category.name}</Text>
                    <Icon name="chevron" size={14} color={block.ink} />
                  </View>
                ) : null}
              </View>
              {block.image_url ? (
                <Image source={{ uri: block.image_url }} style={s.bannerImage} resizeMode="cover" />
              ) : null}
            </View>
          );
          return category ? (
            <Pressable
              key={block.id}
              accessibilityRole="button"
              accessibilityLabel={`${block.title || category.name}: открыть «${category.name}»`}
              onPress={() => onCategory(category.slug)}
            >
              {body}
            </Pressable>
          ) : (
            <View key={block.id}>{body}</View>
          );
        }

        if (block.kind === "collection") {
          const category = block.category;
          return (
            <View key={block.id}>
              <View style={s.head}>
                {block.title ? <Text style={s.title}>{block.title}</Text> : <View />}
                {category ? (
                  <Pressable
                    accessibilityRole="button"
                    accessibilityLabel={`Все товары: ${category.name}`}
                    onPress={() => onCategory(category.slug)}
                    style={s.all}
                  >
                    <Text style={s.allText}>Все</Text>
                    <Icon name="chevron" size={14} color={c.muted} />
                  </Pressable>
                ) : null}
              </View>
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                snapToInterval={cardWidth + space.gridGap}
                decelerationRate="fast"
                style={s.rail}
                contentContainerStyle={s.railContent}
              >
                {block.products.map((product) => (
                  <View key={product.id} style={{ width: cardWidth }}>
                    <ProductCard product={product} />
                  </View>
                ))}
              </ScrollView>
            </View>
          );
        }

        if (block.kind === "categories") {
          return (
            <View key={block.id}>
              {block.title ? <Text style={[s.title, s.titlePad]}>{block.title}</Text> : null}
              <ScrollView
                horizontal
                showsHorizontalScrollIndicator={false}
                style={s.rail}
                contentContainerStyle={s.chips}
              >
                {block.categories.map((item) => (
                  <Pressable
                    key={item.id}
                    accessibilityRole="button"
                    onPress={() => onCategory(item.slug)}
                    style={({ pressed }) => [s.chip, pressed && s.pressed]}
                  >
                    <Text style={s.chipText}>{item.name}</Text>
                  </Pressable>
                ))}
              </ScrollView>
            </View>
          );
        }

        const paragraphs = block.text.split("\n\n").filter((part) => part.trim());
        return (
          <View key={block.id} style={s.text}>
            {block.title ? <Text style={s.title}>{block.title}</Text> : null}
            {paragraphs.map((part, index) => (
              <Text key={index} style={s.paragraph}>
                {part}
              </Text>
            ))}
          </View>
        );
      })}
      <Text style={[s.title, s.titlePad]}>Все товары</Text>
    </View>
  );
}

const useStyles = makeStyles(({ c }) => ({
  blocks: { gap: 18, paddingBottom: 4 },
  banner: { flexDirection: "row", minHeight: 132, borderRadius: radius.card, overflow: "hidden" },
  bannerBody: { flex: 1, justifyContent: "center", gap: 6, paddingVertical: 18, paddingLeft: 20, paddingRight: 16 },
  bannerTitle: { fontFamily: fonts.display700, fontSize: 20, lineHeight: 24 },
  bannerText: { fontFamily: fonts.text600, fontSize: 14, lineHeight: 19, opacity: 0.86 },
  bannerMore: { flexDirection: "row", alignItems: "center", gap: 2, marginTop: 4 },
  bannerMoreText: { fontFamily: fonts.text700, fontSize: 13 },
  bannerImage: { width: "42%" },
  head: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    gap: 12,
    paddingHorizontal: 6,
    paddingBottom: 6,
  },
  title: { fontFamily: fonts.display700, fontSize: 18, lineHeight: 23, color: c.ink },
  titlePad: { paddingHorizontal: 6, paddingBottom: 6 },
  all: { flexDirection: "row", alignItems: "center", gap: 2, minHeight: 44, paddingLeft: 12 },
  allText: { fontFamily: fonts.text700, fontSize: 13, color: c.muted },
  // Ряд выходит за поля ленты — карточки уезжают под край экрана, а не обрезаются отступом.
  rail: { marginHorizontal: -space.feedSide },
  railContent: { gap: space.gridGap, paddingHorizontal: space.feedSide, paddingVertical: 4 },
  chips: { gap: 8, paddingHorizontal: space.feedSide, paddingVertical: 2 },
  chip: {
    justifyContent: "center",
    minHeight: 44,
    paddingHorizontal: 16,
    borderRadius: radius.seg,
    backgroundColor: c.surface,
  },
  chipText: { fontFamily: fonts.text700, fontSize: 14, color: c.ink },
  pressed: { opacity: 0.7 },
  text: { gap: 8, padding: 18, borderRadius: radius.card, backgroundColor: c.card },
  paragraph: { fontFamily: fonts.text600, fontSize: 15, lineHeight: 22, color: c.ink },
}));
