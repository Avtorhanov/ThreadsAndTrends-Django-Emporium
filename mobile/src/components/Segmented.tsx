import { ScrollView, Text, View } from "react-native";

import { fonts } from "../theme/fonts";
import { makeStyles } from "../theme/ThemeProvider";
import { size } from "../theme/tokens";
import { PressScale } from "./ui";

export type Segment<T extends string> = { value: T; label: string };

type Props<T extends string> = {
  segments: Segment<T>[];
  value: T;
  onChange: (value: T) => void;
  label: string;
  /** Сегменты делят ширину поровну; если не помещаются — прокрутка вбок. */
  scrollable?: boolean;
};

/** Сегменты (категории, сортировка, тема): активный — segOnBg/segOnInk. */
export function Segmented<T extends string>({ segments, value, onChange, label, scrollable }: Props<T>) {
  const s = useStyles();
  const items = segments.map((segment) => {
    const on = segment.value === value;
    return (
      <PressScale
        key={segment.value}
        accessibilityRole="tab"
        accessibilityState={{ selected: on }}
        onPress={() => onChange(segment.value)}
        scale={0.95}
        style={[s.seg, scrollable ? s.segScroll : s.segFlex, on && s.segOn]}
      >
        <Text numberOfLines={1} style={[s.text, on && s.textOn]}>
          {segment.label}
        </Text>
      </PressScale>
    );
  });

  return (
    <View style={s.box} accessibilityRole="tablist" accessibilityLabel={label}>
      {scrollable ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={s.scroll}>
          {items}
        </ScrollView>
      ) : (
        <View style={s.row}>{items}</View>
      )}
    </View>
  );
}

const useStyles = makeStyles(({ c, shadow }) => ({
  box: { padding: 4, borderRadius: 17, backgroundColor: c.surface, boxShadow: shadow.control },
  row: { flexDirection: "row", gap: 4 },
  scroll: { gap: 4 },
  seg: {
    height: size.segHeight,
    borderRadius: 13,
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 14,
  },
  segFlex: { flex: 1 },
  segScroll: { minWidth: 72 },
  segOn: { backgroundColor: c.segOnBg, boxShadow: "0 10px 18px -8px rgba(19,38,28,.6)" },
  text: { fontFamily: fonts.text800, fontSize: 13, color: c.muted },
  textOn: { color: c.segOnInk },
}));
