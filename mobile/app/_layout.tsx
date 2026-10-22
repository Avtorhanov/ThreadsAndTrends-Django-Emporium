import { useFonts } from "expo-font";
import { Stack } from "expo-router";
import * as SplashScreen from "expo-splash-screen";
import { StatusBar } from "expo-status-bar";
import * as SystemUI from "expo-system-ui";
import { useEffect } from "react";
import { Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider, useAuth } from "../src/auth/AuthProvider";
import { CartProvider } from "../src/cart/CartProvider";
import { MAX_CONTENT_WIDTH } from "../src/components/layout";
import { Button } from "../src/components/ui";
import { fontAssets, fonts } from "../src/theme/fonts";
import { makeStyles, ThemeProvider, useTheme } from "../src/theme/ThemeProvider";

// Заставка держится, пока не загружены шрифты и не проверена сессия — без мигания системного шрифта.
SplashScreen.preventAutoHideAsync().catch(() => undefined);

function RootNavigator({ fontsReady }: { fontsReady: boolean }) {
  const { status, retry } = useAuth();
  const s = useStyles();
  const ready = fontsReady && status !== "loading";

  useEffect(() => {
    if (ready) SplashScreen.hideAsync().catch(() => undefined);
  }, [ready]);

  if (!ready) return <View style={s.center} />;

  if (status === "offline") {
    return (
      <View style={s.center}>
        <Text style={s.text}>Нет соединения с сервером.</Text>
        <Button title="Повторить" onPress={retry} />
      </View>
    );
  }

  // Каталог и корзина открыты всем; вход и регистрация — модальной группой поверх них.
  // После входа экраны (auth) закрываются, пользователь возвращается туда, откуда пришёл.
  return (
    <Stack screenOptions={{ headerShown: false, contentStyle: s.scene }}>
      <Stack.Screen name="(app)" />
      <Stack.Protected guard={status !== "signedIn"}>
        <Stack.Screen name="(auth)" options={{ presentation: "modal" }} />
      </Stack.Protected>
    </Stack>
  );
}

function ThemedRoot({ fontsReady }: { fontsReady: boolean }) {
  const { c, dark } = useTheme();
  const s = useStyles();

  useEffect(() => {
    // Фон корневого окна виден при переходах и под клавиатурой — в цвет темы.
    SystemUI.setBackgroundColorAsync(c.bg).catch(() => undefined);
  }, [c.bg]);

  return (
    <>
      <StatusBar style={dark ? "light" : "dark"} />
      {/* В браузере на широком экране приложение — колонка по центру. */}
      <View style={s.page}>
        <View style={s.column}>
          <RootNavigator fontsReady={fontsReady} />
        </View>
      </View>
    </>
  );
}

export default function RootLayout() {
  const [loaded, error] = useFonts(fontAssets);
  // Шрифт не загрузился (нет сети в вебе) — работаем на системном, а не висим на заставке.
  const fontsReady = loaded || Boolean(error);

  return (
    <SafeAreaProvider>
      <ThemeProvider>
        <AuthProvider>
          <CartProvider>
            <ThemedRoot fontsReady={fontsReady} />
          </CartProvider>
        </AuthProvider>
      </ThemeProvider>
    </SafeAreaProvider>
  );
}

const useStyles = makeStyles(({ c }) => ({
  page: { flex: 1, backgroundColor: c.bg },
  column: { flex: 1, width: "100%", maxWidth: MAX_CONTENT_WIDTH, alignSelf: "center", backgroundColor: c.bg },
  scene: { backgroundColor: c.bg },
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
    padding: 24,
    backgroundColor: c.bg,
  },
  text: { fontFamily: fonts.text600, fontSize: 16, color: c.ink },
}));
