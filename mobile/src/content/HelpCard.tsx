import { router } from "expo-router";
import * as WebBrowser from "expo-web-browser";
import { Text, View } from "react-native";

import { Icon, type IconName } from "../components/Icon";
import { Card, PressScale } from "../components/ui";
import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import { SITE_PAGES } from "./contentService";

function Row({ icon, title, onPress }: { icon: IconName; title: string; onPress: () => void }) {
  const s = useStyles();
  const { c } = useTheme();
  return (
    <PressScale accessibilityRole="link" onPress={onPress} scale={0.98} style={s.row}>
      <View style={s.icon}>
        <Icon name={icon} size={20} color={c.tagInk} />
      </View>
      <Text style={s.text}>{title}</Text>
      <Icon name="chevron" size={18} color={c.muted} />
    </PressScale>
  );
}

/** «Помощь»: доставка и возврат, оферта, политика (страницы сайта) и вкладка «Контакты». */
export function HelpCard({ withContacts = true }: { withContacts?: boolean }) {
  const s = useStyles();
  const open = (url: string) => void WebBrowser.openBrowserAsync(url);
  return (
    <View style={s.wrap}>
      <Text style={s.overline}>Помощь</Text>
      <Card style={s.card}>
        <Row icon="box" title="Доставка, оплата и возврат" onPress={() => open(SITE_PAGES.delivery)} />
        <View style={s.divider} />
        {withContacts ? (
          <>
            <Row icon="chat" title="Контакты и статьи" onPress={() => router.navigate("/contacts")} />
            <View style={s.divider} />
          </>
        ) : null}
        <Row icon="help" title="Публичная оферта" onPress={() => open(SITE_PAGES.offer)} />
        <View style={s.divider} />
        <Row icon="help" title="Политика обработки данных" onPress={() => open(SITE_PAGES.privacy)} />
      </Card>
    </View>
  );
}

const useStyles = makeStyles(({ c }) => ({
  wrap: { gap: 8 },
  overline: {
    fontFamily: fonts.text800,
    fontSize: 12,
    letterSpacing: 1.4,
    textTransform: "uppercase",
    color: c.muted,
    paddingHorizontal: 6,
  },
  card: { paddingVertical: 6, paddingHorizontal: 8 },
  row: { minHeight: 56, flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 8 },
  icon: {
    width: 38,
    height: 38,
    borderRadius: radius.control - 3,
    backgroundColor: c.tag,
    alignItems: "center",
    justifyContent: "center",
  },
  text: { flex: 1, fontFamily: fonts.text700, fontSize: 16, color: c.ink },
  divider: { height: 1, marginHorizontal: 8, backgroundColor: c.border },
}));
