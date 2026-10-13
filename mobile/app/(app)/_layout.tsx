import { Stack } from "expo-router";

export default function AppLayout() {
  return (
    <Stack screenOptions={{ headerBackTitle: "Назад" }}>
      <Stack.Screen name="index" options={{ title: "Профиль" }} />
      <Stack.Screen name="change-password" options={{ title: "Смена пароля" }} />
      <Stack.Screen name="delete-account" options={{ title: "Удаление аккаунта" }} />
    </Stack>
  );
}
