import { router, Stack } from "expo-router";
import { Pressable, Text } from "react-native";

import { colors } from "../../src/components/theme";

function ProfileButton() {
  return (
    <Pressable accessibilityRole="button" onPress={() => router.push("/profile")} hitSlop={8}>
      <Text style={{ color: colors.primary, fontSize: 16 }}>Профиль</Text>
    </Pressable>
  );
}

export default function AppLayout() {
  return (
    <Stack screenOptions={{ headerBackTitle: "Назад" }}>
      <Stack.Screen name="index" options={{ title: "Каталог", headerRight: ProfileButton }} />
      <Stack.Screen name="products" options={{ title: "Товары" }} />
      <Stack.Screen name="product/[slug]" options={{ title: "" }} />
      <Stack.Screen name="profile" options={{ title: "Профиль" }} />
      <Stack.Screen name="change-password" options={{ title: "Смена пароля" }} />
      <Stack.Screen name="delete-account" options={{ title: "Удаление аккаунта" }} />
    </Stack>
  );
}
