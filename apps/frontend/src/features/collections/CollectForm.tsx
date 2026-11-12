import { useI18n } from "@/shared/i18n";
import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { ArrowRight, ShieldCheck } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import type { CollectionRequest } from "./types";
import { getConnectors } from "./api";
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
  const [limit, setLimit] = useState(10);
  const [force, setForce] = useState(false);
  const connectors = useQuery({
    queryKey: ["connectors"],
    queryFn: getConnectors,
  });
  const connector = connectors.data?.find((item) => item.id === "tcgdex");
  const selectedLanguages = languages.filter((code) =>
    connector?.languages.includes(code),
  );
  const canSubmit =
    !pending &&
    !connectors.isPending &&
    !connectors.isError &&
    selectedLanguages.length > 0;
  return (
    <form
      onSubmit={(event) => {
        event.preventDefault();
        if (!canSubmit) return;
        onSubmit({
          spider: "tcgdex",
          languages: selectedLanguages,
          card_ids: ids
            .split(",")
            .map((id) => id.trim())
            .filter(Boolean),
          limit,
          force,
        });
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
      <label>
        {t("Nombre maximal par langue")}
        <Input
          type="number"
          min={1}
          max={10000}
          value={limit}
          required
          onChange={(e) => setLimit(Number(e.target.value))}
        />
        <small>
          {t(
            "Les cartes déjà présentes sont ignorées. Le total importé peut être inférieur.",
          )}
        </small>
      </label>
      <label>
        {t("Identifiants de cartes")}{" "}
        <span className="optional">{t("facultatif")}</span>
        <Input
          value={ids}
          onChange={(e) => setIds(e.target.value)}
          placeholder="base1-4, base1-1"
          pattern="[A-Za-z0-9_, \-]*"
        />
        <small>
          {t(
            "Sépare les identifiants par des virgules, ou laisse vide pour parcourir le catalogue.",
          )}
        </small>
      </label>
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
