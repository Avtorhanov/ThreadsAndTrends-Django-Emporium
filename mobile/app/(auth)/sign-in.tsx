import { router } from "expo-router";
import { useState } from "react";

import { useAuth } from "../../src/auth/AuthProvider";
import { Button, Hint, LinkButton, Message, Screen, TextField } from "../../src/components/ui";
import { useSubmit } from "../../src/hooks/useSubmit";

export default function SignInScreen() {
  const { login } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const { submit, loading, error, fieldErrors } = useSubmit(() =>
    login({ email: email.trim(), password }),
  );

  return (
    <Screen title="Вход">
      <Hint>Корзина сохранится: после входа товары из неё перенесутся в ваш аккаунт.</Hint>
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
      <TextField
        label="Пароль"
        value={password}
        onChangeText={setPassword}
        secureTextEntry
        autoComplete="current-password"
        textContentType="password"
        errors={fieldErrors.password}
        onSubmitEditing={() => void submit()}
      />
      <Button title="Войти" onPress={() => void submit()} loading={loading} />
      <LinkButton title="Забыли пароль?" onPress={() => router.push("/forgot-password")} />
      <LinkButton
        title="Нет аккаунта? Зарегистрироваться"
        onPress={() => router.push("/sign-up")}
      />
      <LinkButton
        title="Продолжить без входа"
        onPress={() => (router.canGoBack() ? router.back() : router.replace("/"))}
      />
    </Screen>
  );
}
