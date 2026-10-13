import type { ReactNode } from "react";
import {
  ActivityIndicator,
  KeyboardAvoidingView,
  Platform,
  Pressable,
  ScrollView,
  StyleSheet,
  Text,
  TextInput,
  type TextInputProps,
  View,
} from "react-native";
import { SafeAreaView } from "react-native-safe-area-context";

import { colors, radius, spacing } from "./theme";

export function Screen({ title, children }: { title?: string; children: ReactNode }) {
  return (
    <SafeAreaView style={styles.safe} edges={["top", "bottom"]}>
      <KeyboardAvoidingView
        style={styles.flex}
        behavior={Platform.OS === "ios" ? "padding" : undefined}
      >
        <ScrollView contentContainerStyle={styles.content} keyboardShouldPersistTaps="handled">
          {title ? <Text style={styles.title}>{title}</Text> : null}
          {children}
        </ScrollView>
      </KeyboardAvoidingView>
    </SafeAreaView>
  );
}

type TextFieldProps = TextInputProps & { label: string; errors?: string[] };

export function TextField({ label, errors, style, ...props }: TextFieldProps) {
  const hasError = Boolean(errors?.length);
  return (
    <View style={styles.field}>
      <Text style={styles.label}>{label}</Text>
      <TextInput
        placeholderTextColor={colors.muted}
        style={[styles.input, hasError && styles.inputError, style]}
        accessibilityLabel={label}
        {...props}
      />
      {errors?.map((message) => (
        <Text key={message} style={styles.fieldError}>
          {message}
        </Text>
      ))}
    </View>
  );
}

type ButtonProps = {
  title: string;
  onPress: () => void;
  loading?: boolean;
  variant?: "primary" | "secondary" | "danger";
  disabled?: boolean;
};

export function Button({ title, onPress, loading, variant = "primary", disabled }: ButtonProps) {
  const inactive = disabled || loading;
  return (
    <Pressable
      accessibilityRole="button"
      onPress={onPress}
      disabled={inactive}
      style={({ pressed }) => [
        styles.button,
        variant === "secondary" && styles.buttonSecondary,
        variant === "danger" && styles.buttonDanger,
        (pressed || inactive) && styles.buttonDimmed,
      ]}
    >
      {loading ? (
        <ActivityIndicator color={variant === "secondary" ? colors.primary : colors.primaryText} />
      ) : (
        <Text style={[styles.buttonText, variant === "secondary" && styles.buttonTextSecondary]}>
          {title}
        </Text>
      )}
    </Pressable>
  );
}

export function LinkButton({ title, onPress }: { title: string; onPress: () => void }) {
  return (
    <Pressable accessibilityRole="link" onPress={onPress} style={styles.link}>
      <Text style={styles.linkText}>{title}</Text>
    </Pressable>
  );
}

export function Message({ text, kind = "error" }: { text: string | null; kind?: "error" | "success" }) {
  if (!text) return null;
  return (
    <View style={[styles.message, kind === "success" ? styles.messageSuccess : styles.messageError]}>
      <Text style={{ color: kind === "success" ? colors.success : colors.danger }}>{text}</Text>
    </View>
  );
}

export function Hint({ children }: { children: ReactNode }) {
  return <Text style={styles.hint}>{children}</Text>;
}

const styles = StyleSheet.create({
  safe: { flex: 1, backgroundColor: colors.background },
  flex: { flex: 1 },
  content: { padding: spacing.lg, gap: spacing.md, flexGrow: 1 },
  title: { fontSize: 28, fontWeight: "700", color: colors.text, marginBottom: spacing.sm },
  field: { gap: spacing.xs },
  label: { fontSize: 14, color: colors.muted },
  input: {
    backgroundColor: colors.surface,
    borderWidth: 1,
    borderColor: colors.border,
    borderRadius: radius,
    paddingHorizontal: spacing.md,
    paddingVertical: 12,
    fontSize: 16,
    color: colors.text,
  },
  inputError: { borderColor: colors.danger },
  fieldError: { color: colors.danger, fontSize: 13 },
  button: {
    backgroundColor: colors.primary,
    borderRadius: radius,
    paddingVertical: 14,
    alignItems: "center",
    minHeight: 48,
    justifyContent: "center",
  },
  buttonSecondary: {
    backgroundColor: "transparent",
    borderWidth: 1,
    borderColor: colors.primary,
  },
  buttonDanger: { backgroundColor: colors.danger },
  buttonDimmed: { opacity: 0.6 },
  buttonText: { color: colors.primaryText, fontSize: 16, fontWeight: "600" },
  buttonTextSecondary: { color: colors.primary },
  link: { paddingVertical: spacing.sm, alignItems: "center" },
  linkText: { color: colors.primary, fontSize: 15 },
  message: { borderRadius: radius, padding: spacing.md },
  messageError: { backgroundColor: colors.dangerBg },
  messageSuccess: { backgroundColor: colors.successBg },
  hint: { color: colors.muted, fontSize: 14, lineHeight: 20 },
});
