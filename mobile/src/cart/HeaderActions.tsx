import { router } from "expo-router";
import { Pressable, StyleSheet, Text, View } from "react-native";

import { useAuth } from "../auth/AuthProvider";
import { colors, spacing } from "../components/theme";
import { useCart } from "./CartProvider";

export function CartHeaderButton() {
  const { count } = useCart();
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityLabel={count ? `Корзина, товаров: ${count}` : "Корзина"}
      onPress={() => router.push("/cart")}
      hitSlop={8}
      style={styles.cart}
    >
      <Text style={styles.link}>Корзина</Text>
      {count > 0 ? (
        <View style={styles.badge}>
          <Text style={styles.badgeText}>{count > 99 ? "99+" : count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

function AccountHeaderButton() {
  const { status } = useAuth();
  const signedIn = status === "signedIn";
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push(signedIn ? "/profile" : "/sign-in")}
      hitSlop={8}
    >
      <Text style={styles.link}>{signedIn ? "Профиль" : "Войти"}</Text>
    </Pressable>
  );
}

/** Шапка каталога: корзина и вход/профиль. */
export function CatalogHeaderActions() {
  return (
    <View style={styles.row}>
      <CartHeaderButton />
      <AccountHeaderButton />
    </View>
  );
}

const styles = StyleSheet.create({
  row: { flexDirection: "row", alignItems: "center", gap: spacing.md },
  cart: { flexDirection: "row", alignItems: "center", gap: spacing.xs },
  link: { color: colors.primary, fontSize: 16 },
  badge: {
    minWidth: 20,
    height: 20,
    paddingHorizontal: 5,
    borderRadius: 10,
    backgroundColor: colors.primary,
    alignItems: "center",
    justifyContent: "center",
  },
  badgeText: { color: colors.primaryText, fontSize: 12, fontWeight: "700" },
});
