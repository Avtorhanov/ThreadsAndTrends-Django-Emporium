import { Stack } from "expo-router";

import { useAuth } from "../../src/auth/AuthProvider";
import { SheetDepthProvider } from "../../src/navigation/SheetDepth";
import { StackHeader } from "../../src/navigation/StackHeader";
import { useTheme } from "../../src/theme/ThemeProvider";

export default function AppLayout() {
  const { status } = useAuth();
  const { c } = useTheme();
  return (
    <SheetDepthProvider>
      <Stack
        screenOptions={{
          header: (props) => <StackHeader {...props} />,
          contentStyle: { backgroundColor: c.bg },
        }}
      >
        {/* Каталог, контакты, корзина и профиль (гостю — приглашение войти) — вкладки. */}
        <Stack.Screen name="(tabs)" options={{ headerShown: false }} />
        {/* Поиск — из шапки каталога (лаймовая кнопка, поле, фильтры); статьи — из «Контактов». */}
        <Stack.Screen name="search" options={{ title: "Поиск" }} />
        <Stack.Screen name="articles/[slug]" options={{ title: "Статья" }} />
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
