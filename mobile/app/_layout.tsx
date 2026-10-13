import { Stack } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { ActivityIndicator, StyleSheet, Text, View } from "react-native";
import { SafeAreaProvider } from "react-native-safe-area-context";

import { AuthProvider, useAuth } from "../src/auth/AuthProvider";
import { CartProvider } from "../src/cart/CartProvider";
import { colors, spacing } from "../src/components/theme";
import { Button } from "../src/components/ui";

function RootNavigator() {
  const { status, retry } = useAuth();

  if (status === "loading") {
    return (
      <View style={styles.center}>
        <ActivityIndicator size="large" color={colors.primary} />
      </View>
    );
  }

  if (status === "offline") {
    return (
      <View style={styles.center}>
        <Text style={styles.text}>Нет соединения с сервером.</Text>
        <Button title="Повторить" onPress={retry} />
      </View>
    );
  }

  // Каталог и корзина открыты всем; вход и регистрация — модальной группой поверх них.
  // После входа экраны (auth) закрываются, пользователь возвращается туда, откуда пришёл.
  return (
    <Stack screenOptions={{ headerShown: false }}>
      <Stack.Screen name="(app)" />
      <Stack.Protected guard={status !== "signedIn"}>
        <Stack.Screen name="(auth)" options={{ presentation: "modal" }} />
      </Stack.Protected>
    </Stack>
  );
}

export default function RootLayout() {
  return (
    <SafeAreaProvider>
      <AuthProvider>
        <CartProvider>
          <StatusBar style="dark" />
          <RootNavigator />
        </CartProvider>
      </AuthProvider>
    </SafeAreaProvider>
  );
}

const styles = StyleSheet.create({
  center: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: spacing.md,
    padding: spacing.lg,
    backgroundColor: colors.background,
  },
  text: { fontSize: 16, color: colors.text },
});
