import { Stack } from "expo-router";

import { fonts } from "../../src/theme/fonts";
import { useTheme } from "../../src/theme/ThemeProvider";

export default function AuthLayout() {
  const { c } = useTheme();
  return (
    <Stack
      initialRouteName="sign-in"
      screenOptions={{
        headerBackTitle: "Назад",
        title: "",
        headerShadowVisible: false,
        headerStyle: { backgroundColor: c.bg },
        headerTintColor: c.ink,
        headerTitleStyle: { fontFamily: fonts.text800, color: c.ink },
        contentStyle: { backgroundColor: c.bg },
      }}
    >
      <Stack.Screen name="sign-in" options={{ headerShown: false }} />
      <Stack.Screen name="sign-up" />
      <Stack.Screen name="forgot-password" />
      <Stack.Screen name="reset-password" />
    </Stack>
  );
}
