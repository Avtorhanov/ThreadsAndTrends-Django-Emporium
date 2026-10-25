import { useEffect, useState } from "react";
import { Linking, View } from "react-native";
import Animated, { FadeIn, FadeInDown, FadeOut, useReducedMotion } from "react-native-reanimated";

import { Button, Message } from "../components/ui";
import { API_URL } from "../config";
import { type Contact, contentService } from "../content/contentService";
import { ease, REDUCED_FADE_MS } from "../theme/motion";
import { makeStyles } from "../theme/ThemeProvider";

const ASK_KINDS: readonly string[] = ["telegram", "whatsapp"];
const order = (kind: string) => ASK_KINDS.indexOf(kind);

/** Ссылка на чат: в WhatsApp текст вопроса подставляется сам, в Telegram — только чат. */
function chatUrl(contact: Contact, message: string): string {
  return contact.kind === "whatsapp" ? `${contact.url}?text=${encodeURIComponent(message)}` : contact.url;
}

/**
 * Цена по запросу: «Узнать» раскрывает над кнопкой мессенджеры магазина (каналы — из
 * «Контактов»). Корзины у такого товара нет.
 */
export function AskPanel({ name, slug }: { name: string; slug: string }) {
  const s = useStyles();
  const reduced = useReducedMotion();
  const [open, setOpen] = useState(false);
  const [links, setLinks] = useState<Contact[] | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!open || links) return;
    contentService
      .contacts()
      .then((all) => setLinks(all.filter((c) => order(c.kind) >= 0).sort((a, b) => order(a.kind) - order(b.kind))))
      .catch(() => setError("Не удалось загрузить контакты магазина."));
  }, [open, links]);

  const message = `Здравствуйте! Подскажите цену: ${name} — ${API_URL}/product/${slug}/`;
  const entering = reduced
    ? FadeIn.duration(REDUCED_FADE_MS)
    : FadeInDown.duration(280)
        .withInitialValues({ opacity: 0, transform: [{ translateY: 8 }] })
        .easing(ease.out);

  return (
    <View style={s.wrap}>
      {open ? (
        <Animated.View entering={entering} exiting={FadeOut.duration(150)} style={s.links}>
          <Message text={error ?? (links && links.length === 0 ? "Контакты магазина пока не указаны." : null)} />
          {(links ?? []).map((contact) => (
            <View key={contact.kind} style={s.link}>
              <Button
                title={contact.title}
                icon={contact.kind === "telegram" ? "send" : "chat"}
                variant="secondary"
                onPress={() => void Linking.openURL(chatUrl(contact, message))}
              />
            </View>
          ))}
        </Animated.View>
      ) : null}
      <Button title={open ? "Скрыть" : "Узнать"} onPress={() => setOpen((v) => !v)} />
    </View>
  );
}

const useStyles = makeStyles(() => ({
  wrap: { gap: 10 },
  links: { flexDirection: "row", flexWrap: "wrap", gap: 10 },
  link: { flexGrow: 1, flexBasis: 140 },
}));
