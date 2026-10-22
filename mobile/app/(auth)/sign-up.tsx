import { useState } from "react";

import { ApiError } from "../../src/api/errors";
import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function SignUpScreen() {
  const { register } = useAuth();
  const [form, setForm] = useState({
    email: "",
    firstName: "",
    lastName: "",
    password: "",
    confirm: "",
  });
  const set = (field: keyof typeof form) => (value: string) =>
    setForm((prev) => ({ ...prev, [field]: value }));

  const { submit, loading, error, fieldErrors } = useSubmit(async () => {
    if (form.password !== form.confirm) {
      throw new ApiError(400, "Пароли не совпадают.", { confirm: ["Пароли не совпадают."] });
    }
    await register({
      email: form.email.trim(),
      password: form.password,
      first_name: form.firstName.trim(),
      last_name: form.lastName.trim(),
    });
  });

  return (
    <Screen title="Регистрация" overline="Новый аккаунт">
      <Message text={error} />
      <TextField
        label="Email"
        value={form.email}
        onChangeText={set("email")}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        textContentType="emailAddress"
        errors={fieldErrors.email}
      />
      <TextField
        label="Имя"
        value={form.firstName}
        onChangeText={set("firstName")}
        autoComplete="given-name"
        errors={fieldErrors.first_name}
      />
      <TextField
        label="Фамилия"
        value={form.lastName}
        onChangeText={set("lastName")}
        autoComplete="family-name"
        errors={fieldErrors.last_name}
      />
      <TextField
        label="Пароль"
        value={form.password}
        onChangeText={set("password")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={fieldErrors.password}
      />
      <TextField
        label="Повторите пароль"
        value={form.confirm}
        onChangeText={set("confirm")}
        secureTextEntry
        autoComplete="new-password"
        textContentType="newPassword"
        errors={fieldErrors.confirm}
      />
      <Hint>Не короче 8 символов, не только цифры и не похож на email.</Hint>
      <Button title="Создать аккаунт" onPress={() => void submit()} loading={loading} />
    </Screen>
  );
}
