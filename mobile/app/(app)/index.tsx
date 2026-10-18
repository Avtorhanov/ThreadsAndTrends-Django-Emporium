import { router } from "expo-router";
import { useState } from "react";
import {
  ActivityIndicator,
  Pressable,
  RefreshControl,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  View,
} from "react-native";

import { useCategories } from "../../src/catalog/hooks";
import { InstallHint } from "../../src/components/InstallHint";
import { colors, radius, spacing } from "../../src/components/theme";
import { Button, Message } from "../../src/components/ui";

function openProducts(category?: { slug: string; name: string }) {
  router.push({
    pathname: "/products",
    params: category ? { category: category.slug, title: category.name } : {},
  });
}

export default function CatalogScreen() {
  const { data, loading, error, reload } = useCategories();
  const [search, setSearch] = useState("");

  const submitSearch = () => {
    const q = search.trim();
    if (q) router.push({ pathname: "/products", params: { q } });
  };

  return (
    <ScrollView
      contentContainerStyle={styles.content}
      refreshControl={<RefreshControl refreshing={loading && data !== null} onRefresh={reload} />}
      keyboardShouldPersistTaps="handled"
    >
      <InstallHint />
      <TextInput
        value={search}
        onChangeText={setSearch}
        onSubmitEditing={submitSearch}
        placeholder="Поиск товаров"
        placeholderTextColor={colors.muted}
        accessibilityLabel="Поиск товаров"
        returnKeyType="search"
        autoCorrect={false}
        maxLength={100}
        style={styles.search}
      />
      <Pressable style={styles.all} onPress={() => openProducts()} accessibilityRole="button">
        <Text style={styles.allText}>Все товары</Text>
        <Text style={styles.chevron}>›</Text>
      </Pressable>

      {loading && data === null ? <ActivityIndicator color={colors.primary} /> : null}
      <Message text={error} />
      {error && data === null ? <Button title="Повторить" variant="secondary" onPress={reload} /> : null}

      {data?.map((root) => (
        <View key={root.id} style={styles.section}>
          <Pressable onPress={() => openProducts(root)} accessibilityRole="button">
            <Text style={styles.sectionTitle}>{root.name}</Text>
          </Pressable>
          <View style={styles.chips}>
            {root.children.map((child) => (
              <Pressable
                key={child.id}
                accessibilityRole="button"
                style={({ pressed }) => [styles.chip, pressed && styles.pressed]}
                onPress={() => openProducts(child)}
              >
                <Text style={styles.chipText}>{child.name}</Text>
              </Pressable>
            ))}
          </View>
        </View>
      ))}
      {data && data.length === 0 ? <Text style={styles.empty}>Каталог пока пуст.</Text> : null}
    </ScrollView>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background, flexGrow: 1 },
  search: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
  },
  all: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    backgroundColor: colors.primary,
    borderRadius: radius,
    padding: spacing.md,
  },
  allText: { color: colors.primaryText, fontSize: 17, fontWeight: "600" },
  chevron: { color: colors.primaryText, fontSize: 22 },
  section: { gap: spacing.sm },
  sectionTitle: { fontSize: 20, fontWeight: "700", color: colors.text },
  chips: { flexDirection: "row", flexWrap: "wrap", gap: spacing.sm },
  chip: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    paddingVertical: spacing.sm,
  },
  chipText: { color: colors.text, fontSize: 15 },
  pressed: { opacity: 0.7 },
  empty: { color: colors.muted, textAlign: "center", marginTop: spacing.xl },
});
