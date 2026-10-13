import { router } from "expo-router";
import { useState } from "react";

import { ApiError } from "../../src/api/errors";
import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function ChangePasswordScreen() {
  const { changePassword } = useAuth();
  const [form, setForm] = useState({ old: "", password: "", confirm: "" });
  const set = (field: keyof typeof form) => (value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const { submit, loading, error, fieldErrors } = useSubmit(async () => {
    if (form.password !== form.confirm) {
      throw new ApiError(400, "Пароли не совпадают.", { confirm: ["Пароли не совпадают."] });
    }
    await changePassword({ old_password: form.old, new_password: form.password });
    router.back();
  });

  return (
    <Screen>
      <Hint>После смены пароля вход на остальных устройствах будет завершён.</Hint>
      <Message text={error} />
      <TextField
        label="Текущий пароль"
        value={form.old}
        onChangeText={set("old")}
        secureTextEntry
        autoComplete="current-password"
        textContentType="password"
        errors={fieldErrors.old_password}
      />
      <TextField
        label="Новый пароль"
        value={form.password}
        onChangeText={set("password")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={fieldErrors.new_password}
      />
      <TextField
        label="Повторите новый пароль"
        value={form.confirm}
        onChangeText={set("confirm")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={fieldErrors.confirm}
      />
      <Button title="Сменить пароль" onPress={() => void submit()} loading={loading} />
    </Screen>
  );
}
