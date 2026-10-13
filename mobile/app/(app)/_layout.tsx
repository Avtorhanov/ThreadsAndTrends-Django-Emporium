import { Stack } from "expo-router";

import { useAuth } from "../../src/auth/AuthProvider";
import { CartHeaderButton, CatalogHeaderActions } from "../../src/cart/HeaderActions";

export default function AppLayout() {
  const { status } = useAuth();
  return (
    <Stack screenOptions={{ headerBackTitle: "Назад", headerRight: () => <CartHeaderButton /> }}>
      {/* Каталог и корзина доступны без входа. */}
      <Stack.Screen
        name="index"
        options={{ title: "Каталог", headerRight: () => <CatalogHeaderActions /> }}
      />
      <Stack.Screen name="products" options={{ title: "Товары" }} />
      <Stack.Screen name="product/[slug]" options={{ title: "" }} />
      <Stack.Screen name="cart" options={{ title: "Корзина", headerRight: undefined }} />
      <Stack.Protected guard={status === "signedIn"}>
        <Stack.Screen name="checkout" options={{ title: "Оформление", headerRight: undefined }} />
        <Stack.Screen name="orders/index" options={{ title: "Мои заказы" }} />
        <Stack.Screen name="orders/[number]" options={{ title: "Заказ" }} />
        <Stack.Screen name="profile" options={{ title: "Профиль", headerRight: undefined }} />
        <Stack.Screen
          name="change-password"
          options={{ title: "Смена пароля", headerRight: undefined }}
        />
        <Stack.Screen
          name="delete-account"
          options={{ title: "Удаление аккаунта", headerRight: undefined }}
        />
      </Stack.Protected>
    </Stack>
  );
}
