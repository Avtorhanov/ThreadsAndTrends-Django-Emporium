import { router } from "expo-router";
import { useState } from "react";

import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function ForgotPasswordScreen() {
  const { requestPasswordReset } = useAuth();
  const [email, setEmail] = useState("");
  const { submit, loading, error, fieldErrors } = useSubmit(async () => {
    const normalized = email.trim();
    await requestPasswordReset(normalized);
    router.push({ pathname: "/reset-password", params: { email: normalized } });
  });

  return (
    <Screen title="Восстановление пароля">
      <Hint>Укажите email аккаунта — пришлём 6-значный код для сброса пароля.</Hint>
      <Message text={error} />
      <TextField
        label="Email"
        value={email}
        onChangeText={setEmail}
        autoCapitalize="none"
        autoComplete="email"
        keyboardType="email-address"
        textContentType="emailAddress"
        errors={fieldErrors.email}
      />
      <Button title="Получить код" onPress={() => void submit()} loading={loading} />
    </Screen>
  );
}
