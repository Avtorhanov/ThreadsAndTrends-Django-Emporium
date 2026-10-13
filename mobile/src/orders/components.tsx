import { Pressable, StyleSheet, Text, View } from "react-native";

import { colors, radius, spacing } from "../components/theme";
import type { OrderStatus } from "./orderService";

const STATUS_COLORS: Record<OrderStatus, { fg: string; bg: string }> = {
  awaiting_payment: { fg: "#B54708", bg: "#FFFAEB" },
  confirmed: { fg: colors.primary, bg: "#EAF2EE" },
  paid: { fg: colors.primary, bg: "#EAF2EE" },
  assembled: { fg: colors.primary, bg: "#EAF2EE" },
  shipped: { fg: "#175CD3", bg: "#EFF8FF" },
  ready_for_pickup: { fg: "#175CD3", bg: "#EFF8FF" },
  delivered: { fg: colors.success, bg: colors.successBg },
  cancelled: { fg: colors.muted, bg: "#F0EEEB" },
};

export function StatusBadge({ status, label }: { status: OrderStatus; label: string }) {
  const palette = STATUS_COLORS[status];
  return (
    <View style={[styles.badge, { backgroundColor: palette.bg }]}>
      <Text style={[styles.badgeText, { color: palette.fg }]}>{label}</Text>
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
  return (
    <View style={styles.choices} accessibilityRole="radiogroup">
      {options.map((option) => {
        const selected = option.value === value;
        return (
          <Pressable
            key={option.value}
            accessibilityRole="radio"
            accessibilityState={{ selected }}
            onPress={() => onChange(option.value)}
            style={[styles.choice, selected && styles.choiceSelected]}
          >
            <View style={[styles.radio, selected && styles.radioSelected]} />
            <View style={styles.choiceBody}>
              <Text style={styles.choiceTitle}>{option.title}</Text>
              {option.caption ? <Text style={styles.choiceCaption}>{option.caption}</Text> : null}
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

const styles = StyleSheet.create({
  badge: {
    alignSelf: "flex-start",
    borderRadius: 999,
    paddingHorizontal: spacing.sm,
    paddingVertical: 2,
  },
  badgeText: { fontSize: 13, fontWeight: "600" },
  choices: { gap: spacing.sm },
  choice: {
    flexDirection: "row",
    alignItems: "center",
    gap: spacing.md,
    padding: spacing.md,
    borderRadius: radius,
    borderWidth: 1,
    borderColor: colors.border,
    backgroundColor: colors.surface,
  },
  choiceSelected: { borderColor: colors.primary },
  radio: {
    width: 20,
    height: 20,
    borderRadius: 10,
    borderWidth: 2,
    borderColor: colors.border,
  },
  radioSelected: { borderColor: colors.primary, borderWidth: 6 },
  choiceBody: { flex: 1, gap: 2 },
  choiceTitle: { fontSize: 16, color: colors.text },
  choiceCaption: { fontSize: 13, color: colors.muted },
});
