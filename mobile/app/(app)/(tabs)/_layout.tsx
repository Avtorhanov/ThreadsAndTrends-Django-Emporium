import { Tabs } from "expo-router";
import { StyleSheet } from "react-native";
import Animated from "react-native-reanimated";

import { TabBar } from "../../../src/components/TabBar";
import { useBehindStyle } from "../../../src/navigation/SheetDepth";
import { useTheme } from "../../../src/theme/ThemeProvider";

export default function TabsLayout() {
  const { c } = useTheme();
  const behind = useBehindStyle();
  return (
    // Под открытым листом товара вкладки уменьшаются и бледнеют (motion.listBehind).
    <Animated.View style={[styles.fill, { backgroundColor: c.bg }, behind]}>
      <Tabs
        tabBar={(props) => <TabBar {...props} />}
        screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: c.bg } }}
      >
        <Tabs.Screen name="index" options={{ title: "Каталог" }} />
        <Tabs.Screen name="contacts" options={{ title: "Контакты" }} />
        <Tabs.Screen name="cart" options={{ title: "Корзина" }} />
        <Tabs.Screen name="profile" options={{ title: "Профиль" }} />
      </Tabs>
    </Animated.View>
  );
}

const styles = StyleSheet.create({ fill: { flex: 1 } });
