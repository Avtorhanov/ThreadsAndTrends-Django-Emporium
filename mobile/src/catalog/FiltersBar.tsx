import { Pressable, StyleSheet, Text, TextInput, View } from "react-native";

import { colors, radius, spacing } from "../components/theme";
import type { ProductSort } from "./catalogService";

/** Состояние полей фильтра как ввёл пользователь; в запрос переводит products.tsx. */
export type FiltersDraft = {
  q: string;
  priceFrom: string; // рубли, как введено
  priceTo: string;
  inStock: boolean;
  sort: ProductSort | "";
};

export const EMPTY_FILTERS: FiltersDraft = { q: "", priceFrom: "", priceTo: "", inStock: false, sort: "" };

function Chip({ label, active, onPress }: { label: string; active: boolean; onPress: () => void }) {
  return (
    <Pressable
      accessibilityRole="button"
      accessibilityState={{ selected: active }}
      onPress={onPress}
      style={({ pressed }) => [styles.chip, active && styles.chipActive, pressed && styles.pressed]}
    >
      <Text style={[styles.chipText, active && styles.chipTextActive]}>{label}</Text>
    </Pressable>
  );
}

type Props = {
  value: FiltersDraft;
  onChange: (next: FiltersDraft) => void;
  priceError: string | null;
};

export function FiltersBar({ value, onChange, priceError }: Props) {
  const set = (patch: Partial<FiltersDraft>) => onChange({ ...value, ...patch });
  const searching = value.q.trim().length > 0;
  const sorts: { sort: FiltersDraft["sort"]; label: string }[] = [
    { sort: "", label: searching ? "Подходящие" : "Новинки" },
    { sort: "price_asc", label: "Дешевле" },
    { sort: "price_desc", label: "Дороже" },
  ];
  const changed =
    value.q !== "" || value.priceFrom !== "" || value.priceTo !== "" || value.inStock || value.sort !== "";

  return (
    <View style={styles.box}>
      <TextInput
        value={value.q}
        onChangeText={(q) => set({ q })}
        placeholder="Поиск товаров"
        placeholderTextColor={colors.muted}
        accessibilityLabel="Поиск товаров"
        returnKeyType="search"
        autoCorrect={false}
        maxLength={100}
        style={styles.search}
      />
      <View style={styles.row}>
        {sorts.map((item) => (
          <Chip
            key={item.sort || "default"}
            label={item.label}
            active={value.sort === item.sort}
            onPress={() => set({ sort: item.sort })}
          />
        ))}
        <Chip label="В наличии" active={value.inStock || searching} onPress={() => set({ inStock: !value.inStock })} />
      </View>
      <View style={styles.row}>
        <TextInput
          value={value.priceFrom}
          onChangeText={(priceFrom) => set({ priceFrom })}
          placeholder="Цена от, ₽"
          placeholderTextColor={colors.muted}
          accessibilityLabel="Цена от, рублей"
          keyboardType="numeric"
          style={[styles.price, priceError ? styles.priceError : null]}
        />
        <TextInput
          value={value.priceTo}
          onChangeText={(priceTo) => set({ priceTo })}
          placeholder="до, ₽"
          placeholderTextColor={colors.muted}
          accessibilityLabel="Цена до, рублей"
          keyboardType="numeric"
          style={[styles.price, priceError ? styles.priceError : null]}
        />
        {changed ? (
          <Pressable accessibilityRole="button" onPress={() => onChange(EMPTY_FILTERS)} hitSlop={8}>
            <Text style={styles.reset}>Сбросить</Text>
          </Pressable>
        ) : null}
      </View>
      {priceError ? <Text style={styles.error}>{priceError}</Text> : null}
      {searching ? <Text style={styles.hint}>Поиск показывает только товары в наличии.</Text> : null}
    </View>
  );
}

const styles = StyleSheet.create({
  box: { gap: spacing.sm, marginBottom: spacing.sm },
  search: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    paddingHorizontal: spacing.md,
    paddingVertical: 10,
    fontSize: 16,
    color: colors.text,
  },
  row: { flexDirection: "row", flexWrap: "wrap", alignItems: "center", gap: spacing.sm },
  chip: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: 999,
    paddingHorizontal: spacing.md,
    paddingVertical: 6,
  },
  chipActive: { backgroundColor: colors.primary, borderColor: colors.primary },
  chipText: { color: colors.text, fontSize: 14 },
  chipTextActive: { color: colors.primaryText },
  pressed: { opacity: 0.7 },
  price: {
    flexGrow: 1,
    flexBasis: 110,
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    paddingHorizontal: spacing.md,
    paddingVertical: 8,
    fontSize: 15,
    color: colors.text,
  },
  priceError: { borderColor: colors.danger },
  reset: { color: colors.primary, fontSize: 15 },
  error: { color: colors.danger, fontSize: 13 },
  hint: { color: colors.muted, fontSize: 13 },
});
