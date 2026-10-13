import { Stack, useLocalSearchParams } from "expo-router";
import { ActivityIndicator, FlatList, StyleSheet, Text, View } from "react-native";

import { ProductTile } from "../../src/catalog/components";
import { useProductFeed } from "../../src/catalog/hooks";
import { colors, spacing } from "../../src/components/theme";
import { Button, Message } from "../../src/components/ui";

export default function ProductsScreen() {
  const params = useLocalSearchParams<{ category?: string; title?: string }>();
  const feed = useProductFeed(params.category || undefined);

  return (
    <>
      <Stack.Screen options={{ title: params.title || "Все товары" }} />
      <FlatList
        data={feed.items}
        keyExtractor={(item) => String(item.id)}
        numColumns={2}
        columnWrapperStyle={styles.row}
        contentContainerStyle={styles.content}
        renderItem={({ item }) => (
          <View style={styles.cell}>
            <ProductTile product={item} />
          </View>
        )}
        onEndReached={feed.loadMore}
        onEndReachedThreshold={0.5}
        refreshing={feed.refreshing}
        onRefresh={feed.refresh}
        ListEmptyComponent={
          feed.loading ? null : <Text style={styles.empty}>{feed.error ? "" : "Здесь пока нет товаров."}</Text>
        }
        ListFooterComponent={
          <View style={styles.footer}>
            {feed.loading && !feed.refreshing ? <ActivityIndicator color={colors.primary} /> : null}
            <Message text={feed.error} />
            {feed.error ? <Button title="Повторить" variant="secondary" onPress={feed.refresh} /> : null}
          </View>
        }
      />
    </>
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background, flexGrow: 1 },
  row: { gap: spacing.md },
  // Ячейка — половина ширины даже для последнего нечётного товара.
  cell: { flex: 1, maxWidth: "50%" },
  footer: { gap: spacing.md, paddingVertical: spacing.md },
  empty: { color: colors.muted, textAlign: "center", marginTop: spacing.xl },
});
