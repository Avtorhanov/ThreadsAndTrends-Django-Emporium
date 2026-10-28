import type { Category } from "../../api/catalog";
import { type HomeBlock, inkFor } from "../../api/home";
import { formatKopecks } from "../../lib/money";

type Props = {
  blocks: HomeBlock[];
  categories: Category[];
  selectedId: number | null;
  onSelect: (id: number) => void;
  onBack: () => void;
};

/** Телефон с главной, как её увидит покупатель после публикации. Нажатие на блок — его настройки. */
export function HomePreview({ blocks, categories, selectedId, onSelect, onBack }: Props) {
  const visible = blocks.filter((block) => block.is_visible);
  const roots = categories.filter((item) => item.parent === null && item.is_active);

  return (
    <div className="he-preview-wrap">
      <div className="he-preview-head">
        <button type="button" className="button button-ghost he-phone-only" onClick={onBack}>
          ← Все блоки
        </button>
        <span className="muted small">Так увидит покупатель · нажмите на блок, чтобы настроить</span>
      </div>
      <div className="he-phone" aria-label="Предпросмотр главной">
        <div className="he-phone-bar">
          <strong>DiDi shop</strong>
          <span className="he-phone-dot" />
        </div>
        <div className="he-phone-screen">
          {visible.length === 0 ? (
            <p className="muted small he-phone-empty">Все блоки скрыты — покупатель увидит только каталог.</p>
          ) : null}
          {visible.map((block) => (
            <button
              key={block.id}
              type="button"
              className={block.id === selectedId ? "he-pv is-selected" : "he-pv"}
              onClick={() => onSelect(block.id)}
              aria-label={`Настроить блок «${block.title || block.kind}»`}
            >
              <PreviewBlock block={block} roots={roots} />
            </button>
          ))}
          <span className="he-pv-title">Все товары</span>
          <span className="he-pv-grid" aria-hidden="true">
            <span />
            <span />
          </span>
        </div>
      </div>
    </div>
  );
}

function PreviewBlock({ block, roots }: { block: HomeBlock; roots: Category[] }) {
  if (block.kind === "banner") {
    const ink = inkFor(block.color);
    return (
      <span className="he-pv-banner" style={{ background: block.color, color: ink }}>
        <span className="he-pv-banner-body">
          {block.title ? <strong>{block.title}</strong> : null}
          {block.text ? <span>{block.text}</span> : null}
        </span>
        {block.image_url ? <img src={block.image_url} alt="" /> : null}
      </span>
    );
  }
  if (block.kind === "collection") {
    return (
      <>
        <span className="he-pv-row">
          <span className="he-pv-title">{block.title}</span>
          {block.source !== "manual" ? <span className="muted small">Все ›</span> : null}
        </span>
        {block.preview_products.length ? (
          <span className="he-pv-rail">
            {block.preview_products.slice(0, 4).map((product) => (
              <span key={product.id} className="he-pv-card">
                {product.cover_url ? <img src={product.cover_url} alt="" /> : <span className="he-pv-photo" />}
                <span className="he-pv-name">{product.name}</span>
                <span className="he-pv-price">
                  {product.price_kopecks === null ? "по запросу" : formatKopecks(product.price_kopecks)}
                </span>
              </span>
            ))}
          </span>
        ) : (
          <span className="muted small he-pv-note">Нет товаров — покупатель не увидит этот блок.</span>
        )}
      </>
    );
  }
  if (block.kind === "categories") {
    return (
      <>
        {block.title ? <span className="he-pv-title">{block.title}</span> : null}
        <span className="he-pv-chips">
          {roots.map((item) => (
            <span key={item.id}>{item.name}</span>
          ))}
        </span>
      </>
    );
  }
  return (
    <span className="he-pv-text">
      {block.title ? <span className="he-pv-title">{block.title}</span> : null}
      {block.text
        .split("\n\n")
        .filter((part) => part.trim())
        .map((part, index) => (
          <span key={index} className="he-pv-par">
            {part}
          </span>
        ))}
    </span>
  );
}
