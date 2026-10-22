import { Pressable, Text, View } from "react-native";

import { fonts } from "../theme/fonts";
import { makeStyles, type Theme, useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import type { OrderStatus } from "./orderService";

function statusColors({ c }: Theme, status: OrderStatus): { fg: string; bg: string } {
  switch (status) {
    case "awaiting_payment":
      return { fg: c.warning, bg: c.warningBg };
    case "confirmed":
    case "paid":
    case "assembled":
      return { fg: c.tagInk, bg: c.tag };
    case "shipped":
    case "ready_for_pickup":
      return { fg: c.info, bg: c.infoBg };
    case "delivered":
      return { fg: c.success, bg: c.successBg };
    case "cancelled":
      return { fg: c.neutral, bg: c.neutralBg };
  }
}

export function StatusBadge({ status, label }: { status: OrderStatus; label: string }) {
  const s = useStyles();
  const palette = statusColors(useTheme(), status);
  return (
    <View style={[s.badge, { backgroundColor: palette.bg }]}>
      <Text style={[s.badgeText, { color: palette.fg }]}>{label}</Text>
    </View>
  );
}

/** Выбор одного варианта из списка (способ доставки, оплаты). */
export function ChoiceList<T extends string>({
  options,
  value,
  onChange,
}: {
  options: { value: T; title: string; caption?: string }[];
  value: T | null;
  onChange: (value: T) => void;
}) {
  const s = useStyles();
  return (
    <View style={s.choices} accessibilityRole="radiogroup">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Pressable
            key={option.value}
            accessibilityRole="radio"
            accessibilityLabel={option.caption ? `${option.title}, ${option.caption}` : option.title}
            accessibilityState={{ selected }}
            onPress={() => onChange(option.value)}
            style={({ pressed }) => [s.choice, selected && s.choiceSelected, pressed && s.pressed]}
          >
            <View style={[s.radio, selected && s.radioSelected]} />
            <View style={s.choiceBody}>
              <Text style={s.choiceTitle}>{option.title}</Text>
              {option.caption ? <Text style={s.choiceCaption}>{option.caption}</Text> : null}
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

export function formatDateTime(value: string): string {
  return new Date(value).toLocaleString("ru-RU", {
    day: "numeric",
    month: "long",
    hour: "2-digit",
    minute: "2-digit",
  });
}

const useStyles = makeStyles(({ c, shadow }) => ({
  badge: {
    alignSelf: "flex-start",
    height: 26,
    borderRadius: radius.tag,
    paddingHorizontal: 10,
    justifyContent: "center",
  },
  badgeText: { fontFamily: fonts.text800, fontSize: 12 },
  choices: { gap: 10 },
  choice: {
    flexDirection: "row",
    alignItems: "center",
    gap: 14,
    padding: 16,
    borderRadius: radius.control + 2,
    borderWidth: 1.5,
    borderColor: "transparent",
    backgroundColor: c.surface,
    boxShadow: shadow.control,
  },
  choiceSelected: { borderColor: c.brand },
  pressed: { opacity: 0.8 },
  radio: { width: 22, height: 22, borderRadius: 11, borderWidth: 2, borderColor: c.inputLine },
  radioSelected: { borderColor: c.brand, borderWidth: 7 },
  choiceBody: { flex: 1, gap: 2 },
  choiceTitle: { fontFamily: fonts.text700, fontSize: 16, color: c.ink },
  choiceCaption: { fontFamily: fonts.text500, fontSize: 13, color: c.muted },
}));
