import { api } from "@/shared/http/client";
import type { CollectionRequest, Connector, Job } from "./types";

export const getConnectors = () => api<Connector[]>("/spiders");

export const requestCollection = (body: CollectionRequest) =>
  api<Job>("/jobs", {
    method: "POST",
    headers: { "Content-Type": "application/json", "X-TCG-Admin": "1" },
    body: JSON.stringify(body),
  });

export const getJobs = () => api<Job[]>("/jobs");
export async function getJobLogs(identifier: string): Promise<string> {
  const response = await fetch(`/api/jobs/${identifier}/logs`);
  if (!response.ok) throw new Error("Journal indisponible");
  return response.text();
}
