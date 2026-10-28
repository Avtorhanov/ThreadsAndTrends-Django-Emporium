import { type FormEvent, useState } from "react";

import { ApiError, type FieldErrors } from "../api/errors";
import { type ShopSettings, sellerParts, shopSettingsService } from "../api/settings";
import { useShopSettings } from "../hooks/useContent";
import { formatKopecks, kopecksToInput, parseRublesToKopecks } from "../lib/money";

function FieldError({ errors, name }: { errors: FieldErrors; name: string }) {
  const message = errors[name]?.[0];
  return message ? <span className="field-error">{message}</span> : null;
}

function Switch({
  checked,
  disabled,
  label,
  hint,
  onChange,
}: {
  checked: boolean;
  disabled?: boolean;
  label: string;
  hint: string;
  onChange: (value: boolean) => void;
}) {
  return (
    <label className={disabled ? "switch setting-switch is-disabled" : "switch setting-switch"}>
      <span className="setting-text">
        <span>{label}</span>
        <span className="muted small">{hint}</span>
      </span>
      <input type="checkbox" checked={checked} disabled={disabled} onChange={(e) => onChange(e.target.checked)} />
      <span className="switch-track" aria-hidden="true" />
    </label>
  );
}

type Draft = {
  courier: string;
  freeFrom: string;
  pickupEnabled: boolean;
  pickupAddress: string;
  cashOnDelivery: boolean;
  timeout: string;
  name: string;
  inn: string;
  ogrn: string;
  address: string;
  phone: string;
  email: string;
};

function toDraft(settings: ShopSettings): Draft {
  return {
    courier: kopecksToInput(settings.delivery_courier_kopecks),
    freeFrom: kopecksToInput(settings.delivery_free_from_kopecks),
    pickupEnabled: settings.pickup_enabled,
    pickupAddress: settings.pickup_address,
    cashOnDelivery: settings.cash_on_delivery_enabled,
    timeout: settings.unpaid_timeout_minutes === null ? "" : String(settings.unpaid_timeout_minutes),
    name: settings.seller_name,
    inn: settings.seller_inn,
    ogrn: settings.seller_ogrn,
    address: settings.seller_address,
    phone: settings.seller_phone,
    email: settings.seller_email,
  };
}

function SettingsForm({ settings, onSaved }: { settings: ShopSettings; onSaved: (value: ShopSettings) => void }) {
  const [draft, setDraft] = useState<Draft>(() => toDraft(settings));
  const [errors, setErrors] = useState<FieldErrors>({});
  const [formError, setFormError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  const [saved, setSaved] = useState(false);
  const defaults = settings.defaults;
  const set = (patch: Partial<Draft>) => {
    setDraft((prev) => ({ ...prev, ...patch }));
    setSaved(false);
  };

  // Предпросмотр строки подвала: пустое поле — значение из .env, как на сайте.
  const line = sellerParts({
    name: draft.name || defaults.seller_name,
    inn: draft.inn || defaults.seller_inn,
    ogrn: draft.ogrn || defaults.seller_ogrn,
    address: draft.address || defaults.seller_address,
    phone: draft.phone || defaults.seller_phone,
    email: draft.email || defaults.seller_email,
  });

  async function submit(event: FormEvent) {
    event.preventDefault();
    const fieldErrors: FieldErrors = {};
    const money = (value: string, field: string) => {
      if (!value.trim()) return null;
      const kopecks = parseRublesToKopecks(value);
      if (kopecks === null) fieldErrors[field] = ["Сумма в рублях, например 500."];
      return kopecks;
    };
    const courier = money(draft.courier, "delivery_courier_kopecks");
    const freeFrom = money(draft.freeFrom, "delivery_free_from_kopecks");
    const timeout = draft.timeout.trim() ? Number(draft.timeout) : null;
    if (timeout !== null && !Number.isInteger(timeout)) {
      fieldErrors.unpaid_timeout_minutes = ["Целое число минут."];
    }
    setErrors(fieldErrors);
    setFormError(null);
    if (Object.keys(fieldErrors).length) return;
    setSaving(true);
    try {
      const result = await shopSettingsService.save({
        delivery_courier_kopecks: courier,
        delivery_free_from_kopecks: freeFrom,
        pickup_enabled: draft.pickupEnabled,
        pickup_address: draft.pickupAddress,
        cash_on_delivery_enabled: draft.cashOnDelivery,
        unpaid_timeout_minutes: timeout,
        seller_name: draft.name,
        seller_inn: draft.inn,
        seller_ogrn: draft.ogrn,
        seller_address: draft.address,
        seller_phone: draft.phone,
        seller_email: draft.email,
      });
      setSaved(true);
      onSaved(result);
    } catch (err) {
      if (err instanceof ApiError) {
        setErrors(err.fieldErrors);
        setFormError(err.message);
      } else {
        setFormError("Не удалось сохранить настройки.");
      }
    } finally {
      setSaving(false);
    }
  }

  return (
    <form className="settings" onSubmit={submit} noValidate>
      <div className="page-header">
        <h1>Настройки магазина</h1>
        <div className="header-action pf-actions">
          {saved ? <span className="saved">Сохранено</span> : null}
          <button type="submit" className="button" disabled={saving}>
            {saving ? "Сохранение…" : "Сохранить"}
          </button>
        </div>
      </div>
      <p className="muted settings-lead">Меняются без деплоя. Пустое поле — значение из настроек сервера (.env), оно видно в подсказке.</p>
      {formError ? <p className="alert">{formError}</p> : null}

      <div className="settings-grid">
        <section className="card form-grid">
          <h2>Доставка</h2>
          <div className="pf-prices">
            <label className="field">
              Курьер
              <span className="money">
                <input
                  inputMode="decimal"
                  value={draft.courier}
                  placeholder={kopecksToInput(defaults.delivery_courier_kopecks)}
                  onChange={(e) => set({ courier: e.target.value })}
                />
                <span>₽</span>
              </span>
              <FieldError errors={errors} name="delivery_courier_kopecks" />
            </label>
            <label className="field">
              Бесплатно от
              <span className="money">
                <input
                  inputMode="decimal"
                  value={draft.freeFrom}
                  placeholder={kopecksToInput(defaults.delivery_free_from_kopecks)}
                  onChange={(e) => set({ freeFrom: e.target.value })}
                />
                <span>₽</span>
              </span>
              <FieldError errors={errors} name="delivery_free_from_kopecks" />
            </label>
          </div>
          <Switch
            checked={draft.pickupEnabled}
            label="Самовывоз"
            hint="Бесплатно, предлагается при оформлении"
            onChange={(pickupEnabled) => set({ pickupEnabled })}
          />
          {draft.pickupEnabled ? (
            <label className="field">
              Адрес пункта выдачи
              <input
                value={draft.pickupAddress}
                maxLength={300}
                placeholder={defaults.pickup_address || "Город, улица, дом, часы работы"}
                onChange={(e) => set({ pickupAddress: e.target.value })}
              />
              {!draft.pickupAddress.trim() && !defaults.pickup_address ? (
                <span className="muted small">Без адреса самовывоз покупателю не предлагается.</span>
              ) : null}
              <FieldError errors={errors} name="pickup_address" />
            </label>
          ) : null}
        </section>

        <section className="card form-grid">
          <h2>Оплата</h2>
          <Switch
            checked={settings.online_payment_available}
            disabled
            label="Онлайн-оплата (ЮKassa)"
            hint="Карта, СБП, чеки 54-ФЗ"
            onChange={() => undefined}
          />
          {!settings.online_payment_available ? (
            <p className="note note-warning">
              Включится, когда на сервере появятся ключи ЮKassa. Ключи вводятся только в .env — в панели их нет.
            </p>
          ) : null}
          <Switch
            checked={draft.cashOnDelivery}
            label="Оплата при получении"
            hint="Наличными или картой курьеру"
            onChange={(cashOnDelivery) => set({ cashOnDelivery })}
          />
          <FieldError errors={errors} name="cash_on_delivery_enabled" />
          <label className="field">
            Автоотмена неоплаченного онлайн-заказа
            <span className="money input-narrow">
              <input
                inputMode="numeric"
                value={draft.timeout}
                placeholder={String(defaults.unpaid_timeout_minutes)}
                onChange={(e) => set({ timeout: e.target.value })}
              />
              <span>мин</span>
            </span>
            <span className="muted small">Остатки возвращаются на склад. От 10 минут до суток.</span>
            <FieldError errors={errors} name="unpaid_timeout_minutes" />
          </label>
        </section>

        <section className="card form-grid settings-wide">
          <h2>Реквизиты продавца</h2>
          <p className="muted">Пустые поля на сайте не показываются. Заполненные собираются в одну строку подвала.</p>
          <div className="settings-fields">
            <label className="field">
              Продавец
              <input
                value={draft.name}
                maxLength={200}
                placeholder={defaults.seller_name || "ИП Фамилия И. О. или ООО «…»"}
                onChange={(e) => set({ name: e.target.value })}
              />
              <FieldError errors={errors} name="seller_name" />
            </label>
            <label className="field">
              ИНН
              <input
                inputMode="numeric"
                value={draft.inn}
                maxLength={20}
                placeholder={defaults.seller_inn || "10 или 12 цифр"}
                onChange={(e) => set({ inn: e.target.value })}
              />
              <FieldError errors={errors} name="seller_inn" />
            </label>
            <label className="field">
              ОГРН / ОГРНИП
              <input
                inputMode="numeric"
                value={draft.ogrn}
                maxLength={20}
                placeholder={defaults.seller_ogrn || "13 или 15 цифр"}
                onChange={(e) => set({ ogrn: e.target.value })}
              />
              <FieldError errors={errors} name="seller_ogrn" />
            </label>
            <label className="field">
              Адрес
              <input
                value={draft.address}
                maxLength={300}
                placeholder={defaults.seller_address || "Город, улица, дом"}
                onChange={(e) => set({ address: e.target.value })}
              />
              <FieldError errors={errors} name="seller_address" />
            </label>
            <label className="field">
              Телефон
              <input
                type="tel"
                value={draft.phone}
                maxLength={30}
                placeholder={defaults.seller_phone || "+7 ___ ___-__-__"}
                onChange={(e) => set({ phone: e.target.value })}
              />
              <FieldError errors={errors} name="seller_phone" />
            </label>
            <label className="field">
              Email
              <input
                type="email"
                value={draft.email}
                maxLength={254}
                placeholder={defaults.seller_email || "shop@домен.ru"}
                onChange={(e) => set({ email: e.target.value })}
              />
              <FieldError errors={errors} name="seller_email" />
            </label>
          </div>
          <div className="seller-preview">
            <span className="eyebrow">Так это будет в подвале сайта</span>
            {line.length ? (
              <p className="seller-line">
                {line.map((part, index) => (
                  <span key={part.text}>
                    <span className="seller-part">{part.text}</span>
                    {index < line.length - 1 ? " · " : ""}
                  </span>
                ))}
              </p>
            ) : (
              <p className="muted">Ничего не заполнено — строки в подвале не будет.</p>
            )}
          </div>
        </section>
      </div>
      <p className="muted small">
        Сейчас покупатель видит: доставка курьером{" "}
        {formatKopecks(parseRublesToKopecks(draft.courier) ?? defaults.delivery_courier_kopecks)}, бесплатно от{" "}
        {formatKopecks(parseRublesToKopecks(draft.freeFrom) ?? defaults.delivery_free_from_kopecks)}.
      </p>
    </form>
  );
}

/** Только демо на GitHub Pages: вернуть магазин и панель к исходным данным. */
function DemoReset() {
  const [busy, setBusy] = useState(false);
  const [confirming, setConfirming] = useState(false);

  async function reset() {
    setBusy(true);
    // Имитация сервера (preview/mock.ts → sim.js) уже загружена: панель работает через неё.
    await window.DidiSim?.reset();
    window.location.reload();
  }

  return (
    <section className="card form-card">
      <h2>Демо-данные</h2>
      <p className="muted small">
        Это демо: товары, заказы, клиенты и настройки хранятся в этом браузере — общие для панели и магазина.
      </p>
      {confirming ? (
        <div className="he-confirm">
          <span>Удалить все изменения и вернуть исходный каталог, заказы и настройки?</span>
          <div className="actions">
            <button type="button" className="button button-danger" disabled={busy} onClick={() => void reset()}>
              {busy ? "Сбрасываем…" : "Сбросить"}
            </button>
            <button type="button" className="button button-ghost" disabled={busy} onClick={() => setConfirming(false)}>
              Отмена
            </button>
          </div>
        </div>
      ) : (
        <div>
          <button type="button" className="button button-outline" onClick={() => setConfirming(true)}>
            Сбросить демо-данные
          </button>
        </div>
      )}
    </section>
  );
}

export function SettingsPage() {
  const settings = useShopSettings();
  return (
    <section className="stack">
      {settings.error ? <p className="alert">{settings.error}</p> : null}
      {settings.loading && !settings.data ? <p className="muted">Загрузка…</p> : null}
      {settings.data ? (
        <SettingsForm
          key={settings.data.updated_at ?? "new"}
          settings={settings.data}
          onSaved={settings.set}
        />
      ) : null}
      {import.meta.env.VITE_PREVIEW === "1" ? <DemoReset /> : null}
    </section>
  );
}
