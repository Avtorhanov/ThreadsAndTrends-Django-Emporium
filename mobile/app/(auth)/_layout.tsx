import { Stack } from "expo-router";

export default function AuthLayout() {
  return (
    <Stack initialRouteName="sign-in" screenOptions={{ headerBackTitle: "Назад", title: "" }}>
      <Stack.Screen name="sign-in" options={{ headerShown: false }} />
      <Stack.Screen name="sign-up" />
      <Stack.Screen name="forgot-password" />
      <Stack.Screen name="reset-password" />
    </Stack>
  );
}
