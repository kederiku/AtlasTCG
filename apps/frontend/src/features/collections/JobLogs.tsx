import { useI18n } from "@/shared/i18n";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { date, count } from "@/shared/format";
import { statusLabels } from "./status";
import { getJobLogs } from "./api";
import type { Job } from "./types";
import { isImageRepair, isScopedCollection } from "./types";
import { CollectionTarget } from "./CollectionTarget";
import type { MessageKey } from "@/shared/i18n/messages";

const repairCounters: [string, MessageKey][] = [
  ["images/examined", "Impressions examinées"],
  ["images/downloaded", "Images téléchargées"],
  ["images/present", "Images déjà présentes"],
  ["images/unavailable", "Images indisponibles"],
  ["images/errors", "Erreurs"],
];
export function JobLogs({ job }: { job: Job }) {
  const { t, locale, languageName } = useI18n();
  const logs = useQuery({
    queryKey: ["logs", job.id],
    queryFn: () => getJobLogs(job.id),
    refetchInterval:
      job.status === "running" || job.status === "queued" ? 2000 : false,
  });
  return (
    <>
      <div className="log-meta">
        <Badge>{t(statusLabels[job.status])}</Badge>
        <span>{date(job.created_at, locale)}</span>
      </div>
      {isScopedCollection(job.parameters) && (
        <>
          <p>
            <CollectionTarget request={job.parameters} />
          </p>
          <p>
            {t("Langues")}:{" "}
            {job.parameters.languages.map(languageName).join(", ")}
          </p>
          {job.stats["scope/languages_unavailable"] !== undefined && (
            <p>
              {t("Langues indisponibles")}:{" "}
              {count(job.stats["scope/languages_unavailable"], locale)}
            </p>
          )}
        </>
      )}
      {isImageRepair(job.parameters) &&
        (job.status === "queued" || job.status === "running" ? (
          <p className="muted">
            {t("Le bilan sera disponible à la fin de la réparation.")}
          </p>
        ) : (
          <dl className="repair-summary">
            {repairCounters.map(([key, label]) => (
              <div key={key}>
                <dt>{t(label)}</dt>
                <dd>{count(job.stats[key] ?? 0, locale)}</dd>
              </div>
            ))}
          </dl>
        ))}
      {job.error && <p className="error">{job.error}</p>}
      <pre className="log-output">
        {logs.isError
          ? t("Impossible de charger le journal.")
          : logs.data || t("Chargement du journal…")}
      </pre>
    </>
  );
}
