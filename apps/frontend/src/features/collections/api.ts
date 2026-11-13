import { api } from "@/shared/http/client";
import type { JobRequest, Connector, Job, CollectionChoice } from "./types";

export const getConnectors = () => api<Connector[]>("/spiders");

export const getCollectionOptions = (
  kind: "blocks" | "sets",
  languages: string[],
  locale: string,
  blockId?: string,
) => {
  const query = new URLSearchParams({ languages: languages.join(","), locale });
  if (blockId) query.set("block_id", blockId);
  return api<CollectionChoice[]>(`/collection-options/tcgdex/${kind}?${query}`);
};

export const requestCollection = (body: JobRequest) =>
  api<Job>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-TCG-Admin": "1" },
    body: JSON.stringify(body),
  });

export const requestImageRepair = () =>
  requestCollection({ kind: "repair_images" });

export const getJobs = () => api<Job[]>("/jobs");
export async function getJobLogs(identifier: string): Promise<string> {
  const response = await fetch(`/api/jobs/${identifier}/logs`);
  if (!response.ok) throw new Error("Journal indisponible");
  return response.text();
}
