import { useI18n } from "@/shared/i18n";
import type { UseQueryResult } from "@tanstack/react-query";
import { Workflow, Check, Circle, Terminal } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { statusLabels } from "./status";
import { date, count } from "@/shared/format";
import type { Job } from "./types";
export function CollectionsPanel({
  jobs,
  onSelect,
}: {
  jobs: UseQueryResult<Job[]>;
  onSelect: (job: Job) => void;
}) {
  const { t, locale } = useI18n();
  return (
    <section>
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
                <th>{t("Importées")}</th>
                <th>{t("Ignorées")}</th>
                <th>
                  <span className="sr-only">{t("Journal")}</span>
                </th>
              </tr>
            </thead>
            <tbody>
              {jobs.data.map((job) => (
                <tr key={job.id}>
                  <td>
                    <strong>{job.parameters.spider}</strong>
                    <small>{date(job.created_at, locale)}</small>
                  </td>
                  <td>
                    {job.parameters.languages.map((l) => (
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
                      job.stats["cards/stored"] ??
                        job.stats["item_scraped_count"] ??
                        0,
                      locale,
                    )}
                  </td>
                  <td>
                    {count(job.stats["cards/skipped_existing"] ?? 0, locale)}
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
