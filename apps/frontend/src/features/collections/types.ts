export type Connector = {
  id: string;
  name: string;
  game: string;
  languages: string[];
};

export type LegacyCollectionRequest = {
  spider: string;
  languages: string[];
  card_ids: string[];
  limit: number;
  force: boolean;
};
export type CollectionScope = { kind: "block" | "set"; id: string };
export type ScopedCollectionRequest = {
  kind: "collect_scope";
  spider: "tcgdex";
  languages: string[];
  scope: CollectionScope;
  force: boolean;
};
export type CollectionRequest =
  LegacyCollectionRequest | ScopedCollectionRequest;
export type CollectionChoice = {
  id: string;
  name: string;
  languages: string[];
};
export type ImageRepairRequest = { kind: "repair_images" };
export type JobRequest = CollectionRequest | ImageRepairRequest;
export const isImageRepair = (
  request: JobRequest,
): request is ImageRepairRequest =>
  "kind" in request && request.kind === "repair_images";
export const isScopedCollection = (
  request: JobRequest,
): request is ScopedCollectionRequest =>
  "kind" in request && request.kind === "collect_scope";
export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "interrupted";
  parameters: JobRequest;
  stats: Record<string, unknown>;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};
