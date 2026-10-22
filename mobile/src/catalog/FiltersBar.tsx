import { Text, TextInput, View } from "react-native";

import { Segmented } from "../components/Segmented";
import { LinkButton, PressScale } from "../components/ui";
import { Icon } from "../components/Icon";
import { fonts } from "../theme/fonts";
import { makeStyles, useTheme } from "../theme/ThemeProvider";
import { radius } from "../theme/tokens";
import type { ProductSort } from "./catalogService";

/** Состояние полей фильтра как ввёл пользователь; в запрос переводит экран поиска. */
export type FiltersDraft = {
  q: string;
  priceFrom: string; // рубли, как введено
  priceTo: string;
  inStock: boolean;
  sort: ProductSort | "";
};

export const EMPTY_FILTERS: FiltersDraft = { q: "", priceFrom: "", priceTo: "", inStock: false, sort: "" };

export function filtersChanged(value: FiltersDraft): boolean {
  return value.priceFrom !== "" || value.priceTo !== "" || value.inStock || value.sort !== "";
}

type Props = {
  value: FiltersDraft;
  onChange: (next: FiltersDraft) => void;
  priceError: string | null;
};

/** Сортировка, цена «от/до» в рублях и «В наличии» (поиск — отдельным полем на экране). */
export function FiltersBar({ value, onChange, priceError }: Props) {
  const s = useStyles();
  const { c } = useTheme();
  const set = (patch: Partial<FiltersDraft>) => onChange({ ...value, ...patch });
  const searching = value.q.trim().length > 0;
  // С поиском API показывает только товары в наличии — переключатель включён и не снимается.
  const inStock = value.inStock || searching;

  return (
    <View style={s.box}>
      <Segmented
        label="Сортировка"
        segments={[
          { value: "", label: searching ? "Подходящие" : "Новинки" },
          { value: "price_asc", label: "Дешевле" },
          { value: "price_desc", label: "Дороже" },
        ]}
        value={value.sort}
        onChange={(sort) => set({ sort })}
      />
      <View style={s.priceRow}>
        <TextInput
          value={value.priceFrom}
          onChangeText={(priceFrom) => set({ priceFrom })}
          placeholder="Цена от, ₽"
          placeholderTextColor={c.muted}
          selectionColor={c.brand}
          accessibilityLabel="Цена от, рублей"
          keyboardType="numeric"
          style={[s.price, priceError ? s.priceError : null]}
        />
        <TextInput
          value={value.priceTo}
          onChangeText={(priceTo) => set({ priceTo })}
          placeholder="до, ₽"
          placeholderTextColor={c.muted}
          selectionColor={c.brand}
          accessibilityLabel="Цена до, рублей"
          keyboardType="numeric"
          style={[s.price, priceError ? s.priceError : null]}
        />
      </View>
      {priceError ? <Text style={s.error}>{priceError}</Text> : null}
      <View style={s.row}>
        <PressScale
          accessibilityRole="checkbox"
          accessibilityState={{ checked: inStock, disabled: searching }}
          disabled={searching}
          onPress={() => set({ inStock: !value.inStock })}
          scale={0.95}
          style={[s.chip, inStock && s.chipOn]}
        >
          {inStock ? <Icon name="check" size={16} color={c.segOnInk} strokeWidth={2.4} /> : null}
          <Text style={[s.chipText, inStock && s.chipTextOn]}>В наличии</Text>
        </PressScale>
        {filtersChanged(value) ? (
          <LinkButton title="Сбросить" onPress={() => onChange({ ...EMPTY_FILTERS, q: value.q })} />
        ) : null}
      </View>
      {searching ? <Text style={s.hint}>Поиск показывает только товары в наличии.</Text> : null}
    </View>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  box: { gap: 12 },
  row: { flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 },
  priceRow: { flexDirection: "row", gap: 10 },
  price: {
    flex: 1,
    minWidth: 0,
    height: 48,
    paddingHorizontal: 16,
    borderRadius: radius.control,
    borderWidth: 1.5,
    borderColor: "transparent",
    backgroundColor: c.surface,
    boxShadow: shadow.control,
    fontFamily: fonts.text600,
    fontSize: 15,
    color: c.ink,
  },
  priceError: { borderColor: c.danger },
  chip: {
    height: 44,
    paddingHorizontal: 16,
    borderRadius: radius.control,
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
    backgroundColor: c.surface,
    boxShadow: shadow.control,
  },
  chipOn: { backgroundColor: c.segOnBg },
  chipText: { fontFamily: fonts.text800, fontSize: 14, color: c.ink },
  chipTextOn: { color: c.segOnInk },
  error: { fontFamily: fonts.text600, color: c.danger, fontSize: 13 },
  hint: { fontFamily: fonts.text500, color: c.muted, fontSize: 13 },
}));
