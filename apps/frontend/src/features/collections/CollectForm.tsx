import { useI18n } from "@/shared/i18n";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CollectionRequest } from "./types";
import { getConnectors } from "./api";
import {
  CollectionScopePicker,
  useCollectionScope,
} from "./CollectionScopePicker";
export function CollectForm({
  onSubmit,
  pending,
  error,
}: {
  onSubmit: (request: CollectionRequest) => void;
  pending: boolean;
  error?: string;
}) {
  const { t, languageName } = useI18n();
  const [languages, setLanguages] = useState(["fr", "en"]);
  const [ids, setIds] = useState("");
  const [preciseCards, setPreciseCards] = useState(false);
  const [force, setForce] = useState(false);
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
  });
  const connector = connectors.data?.find((item) => item.id === "tcgdex");
  const selectedLanguages = languages.filter((code) =>
    connector?.languages.includes(code),
  );
  const sourceReady =
    !pending &&
    !connectors.isPending &&
    !connectors.isError &&
    selectedLanguages.length > 0;
  const selection = useCollectionScope(
    selectedLanguages,
    sourceReady && !preciseCards,
  );
  const cardIds = [
    ...new Set(
      ids
        .split(",")
        .map((id) => id.trim())
        .filter(Boolean),
    ),
  ];
  const validIds =
    cardIds.length > 0 &&
    cardIds.length <= 100 &&
    cardIds.every((id) => /^[A-Za-z0-9_-]{1,100}$/.test(id));
  const canSubmit =
    sourceReady && (preciseCards ? validIds : !!selection.scope);
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSubmit) return;
        if (preciseCards) {
          onSubmit({
            spider: "tcgdex",
            languages: selectedLanguages,
            card_ids: cardIds,
            limit: cardIds.length,
            force,
          });
        } else if (selection.scope) {
          onSubmit({
            kind: "collect_scope",
            spider: "tcgdex",
            languages: selectedLanguages,
            scope: selection.scope,
            force,
          });
        }
      }}
      className="collect-form"
    >
      <label>
        {t("Source")}
        <select disabled value="tcgdex">
          <option value="tcgdex">TCGdex · Pokémon</option>
        </select>
      </label>
      <fieldset>
        <legend>{t("Langues")}</legend>
        {connectors.isPending ? (
          <p role="status">{t("Chargement des langues…")}</p>
        ) : connectors.isError || !connector ? (
          <div>
            <p role="alert" className="error">
              {connectors.isError
                ? t("Impossible de charger les langues.")
                : t("Source TCGdex indisponible.")}
            </p>
            <Button
              type="button"
              variant="outline"
              onClick={() => void connectors.refetch()}
              disabled={connectors.isFetching}
            >
              {t("Réessayer")}
            </Button>
          </div>
        ) : (
          <div className="language-choices">
            {connector.languages.map((code) => (
              <label
                key={code}
                className={languages.includes(code) ? "selected" : ""}
              >
                <input
                  type="checkbox"
                  checked={languages.includes(code)}
                  onChange={(e) =>
                    setLanguages(
                      e.target.checked
                        ? [...languages, code]
                        : languages.filter((l) => l !== code),
                    )
                  }
                />
                {languageName(code)}
              </label>
            ))}
          </div>
        )}
      </fieldset>
      <label className="check-row">
        <input
          type="checkbox"
          checked={preciseCards}
          onChange={(event) => setPreciseCards(event.target.checked)}
        />
        {t("Cartes précises (avancé)")}
      </label>
      {preciseCards ? (
        <label>
          {t("Identifiants de cartes")}
          <Input
            value={ids}
            onChange={(e) => setIds(e.target.value)}
            placeholder="base1-4, base1-1"
            pattern="[A-Za-z0-9_, \-]*"
            required
          />
          <small>
            {t("Sépare les identifiants par des virgules (100 maximum).")}
          </small>
        </label>
      ) : (
        <CollectionScopePicker
          selection={selection}
          languages={selectedLanguages}
          enabled={sourceReady}
        />
      )}
      <label className="check-row">
        <input
          type="checkbox"
          checked={force}
          onChange={(e) => setForce(e.target.checked)}
        />
        {t("Actualiser aussi les cartes déjà en base")}
      </label>
      <div className="info-note">
        <ShieldCheck size={18} />
        <span>
          {t(
            "Collecte progressive, débit limité. Les images sont enregistrées au format WebP.",
          )}
        </span>
      </div>
      {error && (
        <p role="alert" className="error">
          {t(
            "La demande de collecte a échoué. Vérifie les paramètres et réessaie.",
          )}
        </p>
      )}
      <Button className="w-full" size="lg" disabled={!canSubmit}>
        {pending ? t("Envoi en cours…") : t("Lancer la collecte")}
        <ArrowRight size={16} />
      </Button>
    </form>
  );
}
