import { router } from "expo-router";
import { Linking, Text, View } from "react-native";
import Animated, { FadeInDown, useReducedMotion } from "react-native-reanimated";

import { ProductImage } from "../../../src/catalog/components";
import { Icon, type IconName } from "../../../src/components/Icon";
import { Button, Card, CardGradient, Loading, Message, PressScale, Screen } from "../../../src/components/ui";
import type { Article, Contact, ContactKind } from "../../../src/content/contentService";
import { HelpCard } from "../../../src/content/HelpCard";
import { useContactsTab } from "../../../src/content/hooks";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";
import { radius } from "../../../src/theme/tokens";

// Простые значки в стиле «Лайм-тек» (не фирменные логотипы сервисов).
const ICONS: Record<ContactKind, IconName> = {
  whatsapp: "chat",
  telegram: "send",
  vk: "people",
  phone: "phone",
  email: "mail",
};

function ChannelCard({ contact, index }: { contact: Contact; index: number }) {
  const s = useStyles();
  const { c } = useTheme();
  const reduced = useReducedMotion();
  return (
    <Animated.View entering={reduced ? undefined : FadeInDown.duration(420).delay(60 * index)}>
      <PressScale
        accessibilityRole="link"
        accessibilityLabel={`${contact.title}: ${contact.handle}. ${contact.note}`}
        onPress={() => void Linking.openURL(contact.url)}
        scale={0.98}
        style={s.channel}
      >
        <CardGradient />
        <View style={s.channelIcon}>
          <Icon name={ICONS[contact.kind]} size={24} color={c.onAccent} strokeWidth={2.1} />
        </View>
        <View style={s.channelBody}>
          <Text style={s.channelTitle}>{contact.title}</Text>
          <Text style={s.channelHandle}>{contact.handle}</Text>
          <Text style={s.channelNote}>{contact.note}</Text>
        </View>
        <Icon name="chevron" size={18} color={c.muted} />
      </PressScale>
    </Animated.View>
  );
}

function ArticleCard({ article }: { article: Article }) {
  const s = useStyles();
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={article.title}
      onPress={() => router.push({ pathname: "/articles/[slug]", params: { slug: article.slug } })}
      scale={0.98}
      style={s.article}
    >
      <CardGradient />
      <ProductImage slug={article.slug} uri={article.cover_url} style={s.articleImage} />
      <View style={s.articleBody}>
        {article.published_at ? (
          <Text style={s.articleDate}>
            {new Date(article.published_at).toLocaleDateString("ru-RU", {
              day: "numeric",
              month: "long",
              year: "numeric",
            })}
          </Text>
        ) : null}
        <Text style={s.articleTitle}>{article.title}</Text>
        {article.excerpt ? (
          <Text style={s.articleText} numberOfLines={3}>
            {article.excerpt}
          </Text>
        ) : null}
      </View>
    </PressScale>
  );
}

/** Вкладка «Контакты»: мессенджеры, телефон и почта магазина, статьи, «Помощь». */
export default function ContactsScreen() {
  const s = useStyles();
  const { data, loading, error, reload } = useContactsTab();

  return (
    <Screen tabs title="Контакты" overline="Мы на связи">
      {loading && !data ? <Loading /> : null}
      <Message text={error} />
      {error ? <Button title="Повторить" variant="secondary" onPress={reload} /> : null}

      {data ? (
        <>
          {data.contacts.length ? (
            <View style={s.list}>
              {data.contacts.map((contact, index) => (
                <ChannelCard key={contact.kind} contact={contact} index={index} />
              ))}
            </View>
          ) : (
            <Card style={s.empty}>
              <Text style={s.emptyText}>Контакты скоро появятся.</Text>
            </Card>
          )}

          {data.articles.length ? (
            <View style={s.list}>
              <Text style={s.overline}>Журнал</Text>
              <Text style={s.sectionTitle} accessibilityRole="header">
                Статьи
              </Text>
              {data.articles.map((article) => (
                <ArticleCard key={article.id} article={article} />
              ))}
            </View>
          ) : null}
        </>
      ) : null}

      <HelpCard withContacts={false} />
    </Screen>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  list: { gap: 10 },
  channel: {
    minHeight: 84,
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingVertical: 12,
    paddingLeft: 12,
    paddingRight: 16,
    borderRadius: radius.card,
    backgroundColor: c.card,
    boxShadow: shadow.card,
  },
  channelIcon: {
    width: 56,
    height: 56,
    borderRadius: 18,
    backgroundColor: c.accent,
    alignItems: "center",
    justifyContent: "center",
    boxShadow: shadow.accentGlow,
  },
  channelBody: { flex: 1, gap: 2, minWidth: 0 },
  channelTitle: { fontFamily: fonts.display700, fontSize: 16, color: c.ink },
  channelHandle: { fontFamily: fonts.text800, fontSize: 14, color: c.brand },
  channelNote: { fontFamily: fonts.text500, fontSize: 13, lineHeight: 18, color: c.muted },
  overline: {
    marginTop: 18,
    fontFamily: fonts.text800,
    fontSize: 12,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: c.muted,
    paddingHorizontal: 6,
  },
  sectionTitle: { fontFamily: fonts.display700, fontSize: 24, color: c.ink, paddingHorizontal: 6 },
  article: {
    padding: 6,
    borderRadius: radius.card,
    backgroundColor: c.card,
    boxShadow: shadow.card,
    overflow: "hidden",
  },
  articleImage: { height: 200, borderRadius: radius.image },
  articleBody: { gap: 6, paddingHorizontal: 10, paddingTop: 12, paddingBottom: 10 },
  articleDate: {
    fontFamily: fonts.text800,
    fontSize: 11,
    letterSpacing: 1.2,
    textTransform: "uppercase",
    color: c.muted,
  },
  articleTitle: { fontFamily: fonts.display700, fontSize: 18, lineHeight: 23, color: c.ink },
  articleText: { fontFamily: fonts.text500, fontSize: 14, lineHeight: 20, color: c.muted },
  empty: { padding: 18 },
  emptyText: { fontFamily: fonts.text600, fontSize: 15, color: c.muted },
}));
