import { router, useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { ActivityIndicator, FlatList, Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../../../src/components/theme";
import { Button, Message } from "../../../src/components/ui";
import { formatKopecks } from "../../../src/lib/money";
import { formatDateTime, StatusBadge } from "../../../src/orders/components";
import { useOrderFeed } from "../../../src/orders/hooks";
import type { OrderSummary } from "../../../src/orders/orderService";

function OrderRow({ order }: { order: OrderSummary }) {
  return (
    <Pressable
      accessibilityRole="button"
      onPress={() => router.push({ pathname: "/orders/[number]", params: { number: order.number } })}
      style={({ pressed }) => [styles.row, pressed && styles.pressed]}
    >
      <View style={styles.rowTop}>
        <Text style={styles.number}>Заказ {order.number}</Text>
        <Text style={styles.total}>{formatKopecks(order.total_kopecks)}</Text>
      </View>
      <StatusBadge status={order.status} label={order.status_display} />
      <Text style={styles.muted}>
        {formatDateTime(order.created_at)} · {order.items_count} шт.
      </Text>
    </Pressable>
  );
}

export default function OrdersScreen() {
  const { items, loading, error, hasMore, refresh, loadMore } = useOrderFeed();

  // Статусы меняются на сервере — список обновляется при каждом открытии.
  useFocusEffect(
    useCallback(() => {
      void refresh();
    }, [refresh]),
  );

  return (
    <FlatList
      data={items}
      keyExtractor={(order) => order.number}
      contentContainerStyle={styles.content}
      renderItem={({ item }) => <OrderRow order={item} />}
      onEndReached={loadMore}
      onEndReachedThreshold={0.5}
      refreshing={loading && items.length > 0}
      onRefresh={() => void refresh()}
      ListHeaderComponent={<Message text={error} />}
      ListEmptyComponent={
        loading ? (
          <ActivityIndicator color={colors.primary} style={styles.loader} />
        ) : error ? null : (
          <View style={styles.empty}>
            <Text style={styles.emptyText}>Заказов пока нет</Text>
            <Button title="Перейти в каталог" variant="secondary" onPress={() => router.navigate("/")} />
          </View>
        )
      }
      ListFooterComponent={
        loading && items.length > 0 && hasMore ? (
          <ActivityIndicator color={colors.primary} style={styles.loader} />
        ) : null
      }
    />
  );
}

const styles = StyleSheet.create({
  content: { padding: spacing.md, gap: spacing.md, backgroundColor: colors.background, flexGrow: 1 },
  row: {
    gap: spacing.xs,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  pressed: { opacity: 0.7 },
  rowTop: { flexDirection: "row", justifyContent: "space-between", gap: spacing.md },
  number: { fontSize: 16, fontWeight: "600", color: colors.text },
  total: { fontSize: 16, fontWeight: "700", color: colors.text },
  muted: { fontSize: 13, color: colors.muted },
  loader: { marginTop: spacing.lg },
  empty: { alignItems: "center", gap: spacing.md, marginTop: spacing.xl },
  emptyText: { color: colors.muted, fontSize: 16 },
});
