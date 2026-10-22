import { Stack } from "expo-router";

import { StackHeader } from "../../src/navigation/StackHeader";
import { useTheme } from "../../src/theme/ThemeProvider";

export default function AuthLayout() {
  const { c } = useTheme();
  return (
    <Stack
      initialRouteName="sign-in"
      screenOptions={{
        title: "",
        header: (props) => <StackHeader {...props} />,
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
