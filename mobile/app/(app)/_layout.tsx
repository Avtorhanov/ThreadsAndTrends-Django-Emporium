import { Stack } from "expo-router";

import { useAuth } from "../../src/auth/AuthProvider";
import { SheetDepthProvider } from "../../src/navigation/SheetDepth";
import { fonts } from "../../src/theme/fonts";
import { useTheme } from "../../src/theme/ThemeProvider";

export default function AppLayout() {
  const { status } = useAuth();
  const { c } = useTheme();
  return (
    <SheetDepthProvider>
      <Stack
        screenOptions={{
          headerBackTitle: "Назад",
          headerShadowVisible: false,
          headerStyle: { backgroundColor: c.bg },
          headerTintColor: c.ink,
          headerTitleStyle: { fontFamily: fonts.text800, fontSize: 17, color: c.ink },
          contentStyle: { backgroundColor: c.bg },
        }}
      >
        {/* Каталог, поиск, корзина и профиль (гостю — приглашение войти) — вкладки. */}
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        {/* Товар — лист снизу поверх вкладок; анимацию и затемнение рисует сам экран. */}
        <Stack.Screen
          name="product/[slug]"
          options={{
            headerShown: false,
            presentation: "transparentModal",
            animation: "none",
            contentStyle: { backgroundColor: "transparent" },
          }}
        />
        <Stack.Protected guard={status === "signedIn"}>
          <Stack.Screen name="checkout" options={{ title: "Оформление" }} />
          <Stack.Screen name="orders/index" options={{ title: "Мои заказы" }} />
          <Stack.Screen name="orders/[number]" options={{ title: "Заказ" }} />
          <Stack.Screen name="change-password" options={{ title: "Смена пароля" }} />
          <Stack.Screen name="delete-account" options={{ title: "Удаление аккаунта" }} />
        </Stack.Protected>
      </Stack>
    </SheetDepthProvider>
  );
}
