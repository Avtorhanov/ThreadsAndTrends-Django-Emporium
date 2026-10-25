import { Alert } from "react-native";

export type ConfirmOptions = {
  title: string;
  message: string;
  confirmText: string;
  cancelText?: string;
};

/** Подтверждение необратимого действия. */
export function confirmAction({
  title,
  message,
  confirmText,
  cancelText = "Отмена",
}: ConfirmOptions): Promise<boolean> {
  return new Promise((resolve) => {
    Alert.alert(
      title,
      message,
      [
        { text: cancelText, style: "cancel", onPress: () => resolve(false) },
        { text: confirmText, style: "destructive", onPress: () => resolve(true) },
      ],
      { cancelable: true, onDismiss: () => resolve(false) },
    );
  });
}
