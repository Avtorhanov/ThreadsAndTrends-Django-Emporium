import { router, useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { FlatList, Text, View } from "react-native";

import { Icon } from "../../../src/components/Icon";
import { Button, Card, Loading, Message, PressScale } from "../../../src/components/ui";
import { formatKopecks } from "../../../src/lib/money";
import { formatDateTime, StatusBadge } from "../../../src/orders/components";
import { useOrderFeed } from "../../../src/orders/hooks";
import type { OrderSummary } from "../../../src/orders/orderService";
import { fonts } from "../../../src/theme/fonts";
import { makeStyles, useTheme } from "../../../src/theme/ThemeProvider";

function OrderRow({ order }: { order: OrderSummary }) {
  const s = useStyles();
  const { c } = useTheme();
  return (
    <PressScale
      accessibilityRole="button"
      accessibilityLabel={`Заказ ${order.number}, ${order.status_display}, ${formatKopecks(order.total_kopecks)}`}
      onPress={() => router.push({ pathname: "/orders/[number]", params: { number: order.number } })}
      scale={0.98}
    >
      <Card style={s.row}>
        <View style={s.rowBody}>
          <View style={s.rowTop}>
            <Text style={s.number}>Заказ {order.number}</Text>
            <Text style={s.total}>{formatKopecks(order.total_kopecks)}</Text>
          </View>
          <StatusBadge status={order.status} label={order.status_display} />
          <Text style={s.muted}>
            {formatDateTime(order.created_at)} · {order.items_count} шт.
          </Text>
        </View>
        <Icon name="chevron" size={18} color={c.muted} />
      </Card>
    </PressScale>
  );
}

export default function OrdersScreen() {
  const s = useStyles();
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
      style={s.list}
      contentContainerStyle={s.content}
      renderItem={({ item }) => <OrderRow order={item} />}
      onEndReached={loadMore}
      onEndReachedThreshold={0.5}
      refreshing={loading && items.length > 0}
      onRefresh={() => void refresh()}
      ListHeaderComponent={<Message text={error} />}
      ListEmptyComponent={
        loading ? (
          <View style={s.loader}>
            <Loading />
          </View>
        ) : error ? null : (
          <Card style={s.empty}>
            <Text style={s.emptyTitle}>Заказов пока нет</Text>
            <Button title="Перейти в каталог" variant="accent" onPress={() => router.navigate("/")} />
          </Card>
        )
      }
      ListFooterComponent={
        loading && items.length > 0 && hasMore ? (
          <View style={s.loader}>
            <Loading />
          </View>
        ) : null
      }
    />
  );
}

const useStyles = makeStyles(({ c }) => ({
  list: { backgroundColor: c.bg },
  content: { padding: 16, gap: 12, flexGrow: 1 },
  row: { flexDirection: "row", alignItems: "center", gap: 12, padding: 18 },
  rowBody: { flex: 1, gap: 8 },
  rowTop: { flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 16 },
  number: { fontFamily: fonts.text800, fontSize: 16, color: c.ink },
  total: { fontFamily: fonts.display700, fontSize: 16, color: c.ink },
  muted: { fontFamily: fonts.text600, fontSize: 13, color: c.muted },
  loader: { marginTop: 24 },
  empty: { alignItems: "center", gap: 14, padding: 24, marginTop: 8 },
  emptyTitle: { fontFamily: fonts.display700, fontSize: 18, color: c.ink },
}));
