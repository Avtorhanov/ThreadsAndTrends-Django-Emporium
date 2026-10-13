import { useLocalSearchParams } from "expo-router";
import { useState } from "react";

import { ApiError } from "../../src/api/errors";
import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, LinkButton, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function ResetPasswordScreen() {
  const params = useLocalSearchParams<{ email?: string }>();
  const { confirmPasswordReset, requestPasswordReset } = useAuth();
  const [form, setForm] = useState({
    email: params.email ?? "",
    code: "",
    password: "",
    confirm: "",
  });
  const [notice, setNotice] = useState<string | null>(null);
  const set = (field: keyof typeof form) => (value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const confirm = useSubmit(async () => {
    if (form.password !== form.confirm) {
      throw new ApiError(400, "Пароли не совпадают.", { confirm: ["Пароли не совпадают."] });
    }
    // После успеха пользователь входит автоматически — навигатор переключится сам.
    await confirmPasswordReset({
      email: form.email.trim(),
      code: form.code.trim(),
      new_password: form.password,
    });
  });

  const resend = useSubmit(async () => {
    await requestPasswordReset(form.email.trim());
    setNotice("Если аккаунт существует, новый код отправлен. Повторно — не чаще раза в минуту.");
  });

  return (
    <Screen title="Новый пароль">
      <Hint>Код действует 15 минут. Проверьте папку «Спам», если письма нет.</Hint>
      <Message text={confirm.error ?? resend.error} />
      <Message text={notice} kind="success" />
      <TextField
        label="Email"
        value={form.email}
        onChangeText={set("email")}
        autoCapitalize="none"
        keyboardType="email-address"
        errors={confirm.fieldErrors.email}
      />
      <TextField
        label="Код из письма"
        value={form.code}
        onChangeText={(value) => set("code")(value.replace(/\D/g, "").slice(0, 6))}
        keyboardType="number-pad"
        autoComplete="one-time-code"
        textContentType="oneTimeCode"
        maxLength={6}
        errors={confirm.fieldErrors.code}
      />
      <TextField
        label="Новый пароль"
        value={form.password}
        onChangeText={set("password")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={confirm.fieldErrors.new_password}
      />
      <TextField
        label="Повторите пароль"
        value={form.confirm}
        onChangeText={set("confirm")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={confirm.fieldErrors.confirm}
      />
      <Button
        title="Сохранить пароль"
        onPress={() => void confirm.submit()}
        loading={confirm.loading}
      />
      <LinkButton title="Отправить код ещё раз" onPress={() => void resend.submit()} />
    </Screen>
  );
}
