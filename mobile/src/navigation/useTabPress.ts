import { useNavigation } from "expo-router";
import { useEffect, useRef } from "react";

type TabNavigation = {
  addListener: (event: "tabPress", callback: () => void) => () => void;
  isFocused: () => boolean;
};

/** Нажатие на вкладку, которая уже открыта (наверх, фокус в поиск). */
export function useTabPress(onRepeatPress: () => void) {
  const navigation = useNavigation() as unknown as TabNavigation;
  const callback = useRef(onRepeatPress);
  callback.current = onRepeatPress;
  useEffect(
    () =>
      navigation.addListener("tabPress", () => {
        if (navigation.isFocused()) callback.current();
      }),
    [navigation],
  );
}
