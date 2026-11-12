export type Connector = {
  id: string;
  name: string;
  game: string;
  languages: string[];
};

export type CollectionRequest = {
  spider: string;
  languages: string[];
  card_ids: string[];
  limit: number;
  force: boolean;
};
export type Job = {
  id: string;
  status: "queued" | "running" | "succeeded" | "failed" | "interrupted";
  parameters: CollectionRequest;
  stats: Record<string, unknown>;
  error: string | null;
  created_at: string;
  finished_at: string | null;
};
