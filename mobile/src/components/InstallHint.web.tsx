import { useEffect, useState } from "react";
import { Linking, Pressable, Text, View } from "react-native";

import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { Card } from "./ui";
import { Icon } from "./Icon";

// Ссылка на APK задаётся при сборке веб-версии (deploy/edge.Dockerfile, ANDROID_APK_URL в .env).
const APK_URL = process.env.EXPO_PUBLIC_ANDROID_APK_URL ?? "";
const DISMISSED_KEY = "didi:install-hint-dismissed";

type Kind = "ios" | "android" | null;

function detect(): Kind {
  if (typeof window === "undefined") return null;
  const standalone =
    window.matchMedia?.("(display-mode: standalone)").matches ||
    (navigator as Navigator & { standalone?: boolean }).standalone === true;
  if (standalone) return null;
  try {
    if (window.localStorage.getItem(DISMISSED_KEY)) return null;
  } catch {
    // Хранилище недоступно (приватный режим) — подсказка просто показывается.
  }
  const ua = navigator.userAgent;
  // iPadOS представляется как Mac, но с сенсорным экраном.
  if (/iPhone|iPad|iPod/.test(ua) || (/Macintosh/.test(ua) && navigator.maxTouchPoints > 1)) return "ios";
  if (/Android/.test(ua) && APK_URL) return "android";
  return null;
}

/** Веб-версия: как установить магазин на телефон (iPhone — «На экран Домой», Android — APK). */
export function InstallHint() {
  const s = useStyles();
  const { c } = useTheme();
  const [kind, setKind] = useState<Kind>(null);
  useEffect(() => setKind(detect()), []);
  if (!kind) return null;

  const dismiss = () => {
    try {
      window.localStorage.setItem(DISMISSED_KEY, "1");
    } catch {
      // не критично
    }
    setKind(null);
  };

  return (
    <Card style={s.box} radius={20}>
      <View style={s.text}>
        <Text style={s.title}>Установите магазин на телефон</Text>
        {kind === "ios" ? (
          <Text style={s.body}>
            В Safari нажмите «Поделиться» (квадрат со стрелкой) → «На экран „Домой“». Магазин откроется
            как приложение.
          </Text>
        ) : (
          <Pressable accessibilityRole="link" onPress={() => void Linking.openURL(APK_URL)}>
            <Text style={s.link}>Скачать приложение для Android (APK)</Text>
          </Pressable>
        )}
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel="Скрыть подсказку" onPress={dismiss} hitSlop={13}>
        <Icon name="close" size={18} color={c.muted} />
      </Pressable>
    </Card>
  );
}

const useStyles = makeStyles(({ c }) => ({
  box: { flexDirection: "row", alignItems: "flex-start", gap: 8, padding: 16, marginBottom: 8 },
  text: { flex: 1, gap: 4 },
  title: { fontFamily: fonts.text800, fontSize: 15, color: c.ink },
  body: { fontFamily: fonts.text500, fontSize: 14, lineHeight: 20, color: c.muted },
  link: { fontFamily: fonts.text700, fontSize: 15, color: c.brand },
}));
