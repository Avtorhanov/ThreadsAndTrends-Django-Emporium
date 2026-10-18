import { useEffect, useState } from "react";
import { Linking, Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "./theme";

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
    <View style={styles.box} accessibilityRole="summary">
      <View style={styles.text}>
        <Text style={styles.title}>Установите магазин на телефон</Text>
        {kind === "ios" ? (
          <Text style={styles.body}>
            В Safari нажмите «Поделиться» (квадрат со стрелкой) → «На экран „Домой“». Магазин откроется
            как приложение.
          </Text>
        ) : (
          <Pressable accessibilityRole="link" onPress={() => void Linking.openURL(APK_URL)}>
            <Text style={styles.link}>Скачать приложение для Android (APK)</Text>
          </Pressable>
        )}
      </View>
      <Pressable accessibilityRole="button" accessibilityLabel="Скрыть подсказку" onPress={dismiss} hitSlop={8}>
        <Text style={styles.close}>✕</Text>
      </Pressable>
    </View>
  );
}

const styles = StyleSheet.create({
  box: {
    flexDirection: "row",
    alignItems: "flex-start",
    gap: spacing.sm,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    padding: spacing.md,
  },
  text: { flex: 1, gap: spacing.xs },
  title: { fontSize: 15, fontWeight: "600", color: colors.text },
  body: { fontSize: 14, lineHeight: 20, color: colors.muted },
  link: { fontSize: 15, color: colors.primary },
  close: { fontSize: 16, color: colors.muted },
});
