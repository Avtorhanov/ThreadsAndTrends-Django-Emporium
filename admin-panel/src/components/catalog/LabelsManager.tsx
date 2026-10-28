import { type FormEvent, useState } from "react";

import { LABEL_TONES, type LabelTone, type ProductLabel, labelsService } from "../../api/catalog";
import { ApiError } from "../../api/errors";

function message(error: unknown): string {
  if (!(error instanceof ApiError)) return "Действие не выполнено.";
  return Object.values(error.fieldErrors)[0]?.[0] ?? error.message;
}

export function LabelBadge({ label }: { label: Pick<ProductLabel, "name" | "tone"> }) {
  return <span className={`badge label-${label.tone}`}>{label.name}</span>;
}

function LabelRow({ label, onChanged }: { label: ProductLabel; onChanged: () => void }) {
  const [name, setName] = useState(label.name);
  const [hint, setHint] = useState(label.hint ?? "");
  const [tone, setTone] = useState<LabelTone>((label.tone ?? "neutral") as LabelTone);
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const dirty = name !== label.name || hint !== (label.hint ?? "") || tone !== label.tone;

  async function run(action: () => Promise<unknown>) {
    setBusy(true);
    setError(null);
    try {
      await action();
      onChanged();
    } catch (err) {
      setError(message(err));
    } finally {
      setBusy(false);
    }
  }

  return (
    <li className="label-row">
      <div className="label-fields">
        <input value={name} maxLength={40} aria-label="Название статуса" onChange={(e) => setName(e.target.value)} />
        <input
          value={hint}
          maxLength={120}
          placeholder="Подсказка покупателю"
          aria-label="Подсказка покупателю"
          onChange={(e) => setHint(e.target.value)}
        />
        <select value={tone} aria-label="Цвет" onChange={(e) => setTone(e.target.value as LabelTone)}>
          {Object.entries(LABEL_TONES).map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
      </div>
      <div className="label-actions">
        <LabelBadge label={{ name: name || label.name, tone }} />
        <span className="muted small">товаров: {label.products_count}</span>
        {dirty ? (
          <button
            type="button"
            className="button"
            disabled={busy}
            onClick={() => void run(() => labelsService.update(label.id, { name, hint, tone }))}
          >
            Сохранить
          </button>
        ) : null}
        <button
          type="button"
          className="button button-danger"
          disabled={busy}
          onClick={() => {
            const note = label.products_count ? ` С ${label.products_count} товаров метка снимется.` : "";
            if (window.confirm(`Удалить статус «${label.name}»?${note}`)) {
              void run(() => labelsService.remove(label.id));
            }
          }}
        >
          Удалить
        </button>
      </div>
      {error ? <span className="field-error">{error}</span> : null}
    </li>
  );
}

/** Справочник статусов товаров: название, подсказка покупателю, цвет. */
export function LabelsManager({ labels, onChanged }: { labels: ProductLabel[]; onChanged: () => void }) {
  const [name, setName] = useState("");
  const [tone, setTone] = useState<LabelTone>("neutral");
  const [error, setError] = useState<string | null>(null);

  async function add(event: FormEvent) {
    event.preventDefault();
    setError(null);
    try {
      await labelsService.create({ name, tone });
      setName("");
      onChanged();
    } catch (err) {
      setError(message(err));
    }
  }

  return (
    <details className="card labels">
      <summary>
        <h2>Статусы товаров</h2>
        <span className="muted">Видны покупателю на карточке, странице товара и в корзине</span>
      </summary>
      <ul className="label-list">
        {labels.map((label) => (
          <LabelRow key={`${label.id}:${label.name}:${label.tone}`} label={label} onChanged={onChanged} />
        ))}
      </ul>
      <form className="inline-form" onSubmit={add}>
        <input
          value={name}
          maxLength={40}
          required
          placeholder="Новый статус, например «Предзаказ»"
          aria-label="Название нового статуса"
          onChange={(e) => setName(e.target.value)}
        />
        <select value={tone} aria-label="Цвет" onChange={(e) => setTone(e.target.value as LabelTone)}>
          {Object.entries(LABEL_TONES).map(([value, text]) => (
            <option key={value} value={value}>
              {text}
            </option>
          ))}
        </select>
        <button type="submit" className="button">
          Добавить
        </button>
      </form>
      {error ? <p className="field-error">{error}</p> : null}
    </details>
  );
}
