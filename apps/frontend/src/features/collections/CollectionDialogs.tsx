import { useI18n } from "@/shared/i18n";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogDescription,
} from "@/components/ui/dialog";
import { CollectForm } from "./CollectForm";
import { JobLogs } from "./JobLogs";
import type { useCollections } from "./useCollections";
export function CollectionDialogs({
  collections,
}: {
  collections: ReturnType<typeof useCollections>;
}) {
  const { t } = useI18n();
  const { collect, setCollect, selectedJob, setSelectedJob, mutation, jobs } =
    collections;
  return (
    <>
      <Dialog open={collect} onOpenChange={setCollect}>
        <DialogContent className="max-h-[calc(100dvh-2rem)] overflow-y-auto sm:max-w-lg">
          <DialogHeader>
            <DialogTitle>{t("Nouvelle collecte")}</DialogTitle>
            <DialogDescription>
              {t("Importez des cartes et leurs images dans votre catalogue.")}
            </DialogDescription>
          </DialogHeader>
          <CollectForm
            onSubmit={(request) => mutation.mutate(request)}
            pending={mutation.isPending}
            error={mutation.error?.message}
          />
        </DialogContent>
      </Dialog>
      <Dialog
        open={!!selectedJob}
        onOpenChange={(open) => {
          if (!open) setSelectedJob(null);
        }}
      >
        <DialogContent className="sm:max-w-4xl">
          <DialogHeader>
            <DialogTitle>{t("Journal de collecte")}</DialogTitle>
            <DialogDescription>
              {selectedJob?.parameters.spider} · {selectedJob?.id}
            </DialogDescription>
          </DialogHeader>
          {selectedJob && (
            <JobLogs
              job={
                jobs.data?.find((job) => job.id === selectedJob.id) ??
                selectedJob
              }
            />
          )}
        </DialogContent>
      </Dialog>
    </>
  );
}
