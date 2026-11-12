import { useI18n, type Translate } from "@/shared/i18n";
import type { MessageKey } from "@/shared/i18n/messages";
import type { CardDetail, ResourceCost } from "./types";
const labels: Record<string, MessageKey> = {
  hp: "PV",
  power: "Puissance",
  toughness: "Endurance",
  attack: "Attaque",
  defense: "Défense",
  level: "Niveau",
  life: "Vie",
  retreat: "Retraite",
  play: "Jouer",
  rules: "Texte de règles",
  flavor: "Texte d’ambiance",
  reminder: "Rappel",
  ability: "Capacité",
  attack_cost: "Coût d’attaque",
  weaknesses: "Faiblesses",
  resistances: "Résistances",
  evolveFrom: "Évolution de",
  dexId: "Numéro Pokédex",
  regulationMark: "Marque de régulation",
  variants: "Variantes",
  variants_detailed: "Détail des variantes",
  thirdParty: "Identifiants externes",
  updated: "Mise à jour source",
};
const label = (key: string, t: Translate) =>
  labels[key] ? t(labels[key]) : key.replaceAll("_", " ");
function costText(cost: ResourceCost, t: Translate) {
  return (
    cost.text ??
    (cost.symbols !== null && cost.symbols !== undefined
      ? cost.symbols.length
        ? cost.symbols.join(" · ")
        : "0"
      : String(cost.value ?? t("Non renseigné")))
  );
}
function SourceValue({ value }: { value: unknown }) {
  const { t } = useI18n();
  if (value === null || value === undefined)
    return <span>{t("Non renseigné")}</span>;
  if (Array.isArray(value))
    return (
      <ul>
        {value.map((v, i) => (
          <li key={i}>
            <SourceValue value={v} />
          </li>
        ))}
      </ul>
    );
  if (typeof value === "object")
    return (
      <dl className="property-list">
        {Object.entries(value).map(([k, v]) => (
          <div key={k}>
            <dt>{label(k, t)}</dt>
            <dd>
              <SourceValue value={v} />
            </dd>
          </div>
        ))}
      </dl>
    );
  return (
    <span>
      {typeof value === "boolean"
        ? value
          ? t("Oui")
          : t("Non")
        : String(value)}
    </span>
  );
}
export function CardRules({
  card,
}: {
  card: Pick<
    CardDetail,
    "faces" | "illustrators" | "rarity" | "legalities" | "game_data"
  >;
}) {
  const { t } = useI18n();
  return (
    <section className="card-rules">
      <div className="printing-meta">
        <div>
          <small>{t("Illustrateur(s)")}</small>
          <p>{card.illustrators.join(", ") || t("Non renseigné")}</p>
        </div>
        <div>
          <small>{t("Rareté")}</small>
          <p>{card.rarity || t("Non renseignée")}</p>
        </div>
      </div>
      {card.faces.length === 0 && (
        <p className="muted">
          {t(
            "Cette observation n’a pas encore de caractéristiques normalisées.",
          )}
        </p>
      )}
      {card.faces.map((face, index) => (
        <article className="face-rules" key={index}>
          <h3>
            {card.faces.length > 1
              ? t("Face {number} · {name}", {
                  number: index + 1,
                  name: face.name,
                })
              : t("Caractéristiques")}
          </h3>
          <div className="trait-list">
            {[...face.types, ...Object.values(face.traits).flat()].map(
              (value, i) => (
                <span key={i}>{value}</span>
              ),
            )}
          </div>
          <dl className="stat-list">
            {Object.entries(face.statistics).map(([key, value]) => (
              <div key={key}>
                <dt>{label(key, t)}</dt>
                <dd>{value}</dd>
              </div>
            ))}
            {Object.entries(face.costs).map(([key, cost]) => (
              <div key={key}>
                <dt>{label(key, t)}</dt>
                <dd>{costText(cost, t)}</dd>
              </div>
            ))}
          </dl>
          {face.abilities.map((ability, i) => (
            <section className="ability" key={i}>
              <div className="ability-heading">
                <div>
                  <small>{label(ability.kind, t)}</small>
                  <h4>{ability.name || label(ability.kind, t)}</h4>
                </div>
                {ability.damage !== null && ability.damage !== undefined && (
                  <strong>{ability.damage}</strong>
                )}
              </div>
              {ability.cost && (
                <p className="ability-cost">{costText(ability.cost, t)}</p>
              )}
              {ability.text && <p className="rules-text">{ability.text}</p>}
              {Object.keys(ability.attributes).length > 0 && (
                <details>
                  <summary>{t("Précisions")}</summary>
                  <SourceValue value={ability.attributes} />
                </details>
              )}
            </section>
          ))}
          {face.texts.map((text, i) => (
            <div className={`text-block ${text.kind}`} key={i}>
              <small>{label(text.kind, t)}</small>
              <p className="rules-text">{text.text}</p>
            </div>
          ))}
        </article>
      ))}
      {Object.keys(card.legalities).length > 0 && (
        <section>
          <h3>{t("Légalité par format")}</h3>
          <dl className="property-list">
            {Object.entries(card.legalities).map(([format, status]) => (
              <div key={format}>
                <dt>{format}</dt>
                <dd>
                  {status === "legal"
                    ? t("Autorisé")
                    : status === "not_legal"
                      ? t("Non autorisé")
                      : status}
                </dd>
              </div>
            ))}
          </dl>
        </section>
      )}
      {Object.entries(card.game_data).map(([game, data]) => (
        <details className="game-specific" key={game}>
          <summary>{t("Informations spécifiques · {game}", { game })}</summary>
          <SourceValue value={data} />
        </details>
      ))}
    </section>
  );
}
