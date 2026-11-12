import { useI18n } from "@/shared/i18n";
import { useQuery } from "@tanstack/react-query";
import { Badge } from "@/components/ui/badge";
import { date } from "@/shared/format";
import { statusLabels } from "./status";
import { getJobLogs } from "./api";
import type { Job } from "./types";
export function JobLogs({ job }: { job: Job }) {
  const { t, locale } = useI18n();
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
      {job.error && <p className="error">{job.error}</p>}
      <pre className="log-output">
        {logs.isError
          ? t("Impossible de charger le journal.")
          : logs.data || t("Chargement du journal…")}
      </pre>
    </>
  );
}
