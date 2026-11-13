import { useI18n } from "@/shared/i18n";
import type { UseQueryResult } from "@tanstack/react-query";
import { Workflow, Check, Circle, Terminal, ImageDown } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { statusLabels } from "./status";
import { date, count } from "@/shared/format";
import type { Job } from "./types";
import { isImageRepair, isScopedCollection } from "./types";
import { CollectionTarget } from "./CollectionTarget";
export function CollectionsPanel({
  jobs,
  onSelect,
  onRepair,
  repairing,
  repairError,
}: {
  jobs: UseQueryResult<Job[]>;
  onSelect: (job: Job) => void;
  onRepair: () => void;
  repairing: boolean;
  repairError: boolean;
}) {
  const { t, locale } = useI18n();
  return (
    <section>
      <div className="repair-action">
        <div>
          <h3>{t("Images du catalogue")}</h3>
          <p>
            {t(
              "Complétez les images de toutes les cartes déjà enregistrées, dans toutes leurs langues. Les fichiers présents sont conservés.",
            )}
          </p>
        </div>
        <Button variant="outline" onClick={onRepair} disabled={repairing}>
          <ImageDown size={16} />
          {repairing
            ? t("Envoi en cours…")
            : t("Réparer les images manquantes")}
        </Button>
      </div>
      {repairError && (
        <p role="alert" className="error">
          {t("La demande de réparation a échoué. Réessayez.")}
        </p>
      )}
      <div className="section-heading">
        <h2>
          {t("Historique des collectes")}{" "}
          <Badge variant="secondary">{jobs.data?.length ?? 0}</Badge>
        </h2>
        <span className="muted">{t("Actualisé automatiquement")}</span>
      </div>
      {jobs.isError ? (
        <div className="empty" role="alert">
          {t("Impossible de charger les collectes.")}
        </div>
      ) : jobs.isPending ? (
        <div className="empty">{t("Chargement…")}</div>
      ) : jobs.data.length === 0 ? (
        <div className="empty">
          <Workflow />
          <h3>{t("Prêt pour la première collecte")}</h3>
          <p>
            {t(
              "Choisissez une source et des langues. Le worker s’occupe de la suite.",
            )}
          </p>
        </div>
      ) : (
        <div className="jobs-table">
          <table>
            <thead>
              <tr>
                <th>{t("Source / lancement")}</th>
                <th>{t("Langues")}</th>
                <th>{t("État")}</th>
                <th>{t("Ajoutées")}</th>
                <th>{t("Déjà présentes")}</th>
                <th>
                  <span className="sr-only">{t("Journal")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.data.map((job) => (
                <tr key={job.id}>
                  <td>
                    <strong>
                      {isImageRepair(job.parameters)
                        ? t("Réparation des images")
                        : job.parameters.spider}
                    </strong>
                    {isScopedCollection(job.parameters) && (
                      <small>
                        <CollectionTarget request={job.parameters} />
                      </small>
                    )}
                    <small>{date(job.created_at, locale)}</small>
                  </td>
                  <td>
                    {isImageRepair(job.parameters)
                      ? t("Toutes les langues")
                      : job.parameters.languages.map((l) => (
                          <span className="table-lang" key={l}>
                            {l.toUpperCase()}
                          </span>
                        ))}
                  </td>
                  <td>
                    <span className={`job-status ${job.status}`}>
                      {job.status === "succeeded" ? (
                        <Check size={13} />
                      ) : (
                        <Circle size={10} />
                      )}{" "}
                      {t(statusLabels[job.status])}
                    </span>
                  </td>
                  <td>
                    {count(
                      isImageRepair(job.parameters)
                        ? (job.stats["images/downloaded"] ?? 0)
                        : (job.stats["cards/stored"] ??
                            (isScopedCollection(job.parameters)
                              ? 0
                              : job.stats["item_scraped_count"]) ??
                            0),
                      locale,
                    )}
                  </td>
                  <td>
                    {count(
                      isImageRepair(job.parameters)
                        ? (job.stats["images/present"] ?? 0)
                        : (job.stats["cards/skipped_existing"] ?? 0),
                      locale,
                    )}
                  </td>
                  <td>
                    <Button
                      variant="ghost"
                      size="sm"
                      onClick={() => onSelect(job)}
                    >
                      <Terminal size={14} />
                      {t("Journal")}
                    </Button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}
      <p className="footnote">
        {t(
          "Une collecte à la fois · 50 dernières collectes · Les demandes restent en attente si le worker est arrêté.",
        )}
      </p>
    </section>
  );
}
