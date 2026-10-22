import { Stack, useLocalSearchParams } from "expo-router";
import { Text, View } from "react-native";
import Animated, { FadeInDown, useReducedMotion } from "react-native-reanimated";

import { ProductImage } from "../../../src/catalog/components";
import { Button, Centered, Loading, Message, Screen } from "../../../src/components/ui";
import { useArticle } from "../../../src/content/hooks";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles } from "../../../src/theme/ThemeProvider";
import { radius } from "../../../src/theme/tokens";

/** Статья: обложка, дата, заголовок, абзацы текста и остальные фото. */
export default function ArticleScreen() {
  const s = useStyles();
  const reduced = useReducedMotion();
  const { slug } = useLocalSearchParams<{ slug: string }>();
  const { data: article, loading, error, reload } = useArticle(slug);

  if (!article) {
    return (
      <Centered>
        <Stack.Screen options={{ title: "Статья" }} />
        {loading ? <Loading /> : null}
        <Message text={error} />
        {error ? <Button title="Повторить" variant="secondary" onPress={reload} /> : null}
      </Centered>
    );
  }

  const [cover, ...gallery] = article.images;
  const enter = (delay: number) => (reduced ? undefined : FadeInDown.duration(420).delay(delay));

  return (
    <Screen>
      <Stack.Screen options={{ title: "Статья" }} />
      {cover ? (
        <ProductImage slug={article.slug} uri={cover.url} style={s.hero} label={article.title} />
      ) : null}
      <Animated.View entering={enter(120)} style={s.head}>
        {article.published_at ? (
          <Text style={s.date}>
            {new Date(article.published_at).toLocaleDateString("ru-RU", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </Text>
        ) : null}
        <Text style={s.title} accessibilityRole="header">
          {article.title}
        </Text>
        {article.excerpt ? <Text style={s.lead}>{article.excerpt}</Text> : null}
      </Animated.View>
      <Animated.View entering={enter(180)} style={s.body}>
        {article.paragraphs.map((paragraph, index) => (
          // Абзацы — простой текст без разметки; порядок не меняется, индекс как ключ безопасен.
          <Text key={index} style={s.paragraph}>
            {paragraph}
          </Text>
        ))}
      </Animated.View>
      {gallery.length ? (
        <Animated.View entering={enter(240)} style={s.gallery}>
          {gallery.map((image) => (
            <View key={image.id} style={s.cell}>
              <ProductImage slug={article.slug} uri={image.url} style={s.photo} />
            </View>
          ))}
        </Animated.View>
      ) : null}
    </Screen>
  );
}

const useStyles = makeStyles(({ c }) => ({
  hero: { height: 240, borderRadius: radius.hero },
  head: { gap: 8, paddingHorizontal: 4 },
  date: {
    fontFamily: fonts.text800,
    fontSize: 12,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: c.muted,
  },
  title: { fontFamily: fonts.display700, fontSize: 26, lineHeight: 31, color: c.ink },
  lead: { fontFamily: fonts.text600, fontSize: 17, lineHeight: 25, color: c.muted },
  body: { gap: 14, paddingHorizontal: 4 },
  paragraph: { fontFamily: fonts.text500, fontSize: 16, lineHeight: 26, color: c.ink },
  gallery: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  cell: { width: "48%" },
  photo: { aspectRatio: 4 / 5, borderRadius: radius.image },
}));
