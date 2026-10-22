import { Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";

import { IconButton } from "../components/ui";
import { fonts } from "../theme/fonts";
import { makeStyles } from "../theme/ThemeProvider";
import { size } from "../theme/tokens";

/** То, что нужно из props заголовка native-stack (expo-router передаёт больше). */
type Props = {
  options: { title?: string };
  back?: unknown;
  navigation: { goBack: () => void };
};

/** Заголовок экранов поверх вкладок в стиле «Лайм-тек»: стеклянная «Назад» + Unbounded. */
export function StackHeader({ options, back, navigation }: Props) {
  const s = useStyles();
  const insets = useSafeAreaInsets();
  return (
    <View style={[s.header, { paddingTop: insets.top + 8 }]}>
      {back ? (
        <IconButton icon="back" label="Назад" size={size.touchMin} onPress={navigation.goBack} />
      ) : null}
      <Text style={s.title} numberOfLines={1} accessibilityRole="header">
        {options.title ?? ""}
      </Text>
    </View>
  );
}

const useStyles = makeStyles(({ c }) => ({
  header: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    paddingHorizontal: 16,
    paddingBottom: 10,
    backgroundColor: c.bg,
  },
  title: {
    flex: 1,
    fontFamily: fonts.display700,
    fontSize: 20,
    letterSpacing: -0.4,
    color: c.ink,
  },
}));
