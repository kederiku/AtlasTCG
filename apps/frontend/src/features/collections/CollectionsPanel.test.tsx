import {
  QueryClient,
  QueryClientProvider,
  useQuery,
} from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import { afterEach, expect, test } from "vitest";
import { CollectionsPanel } from "./CollectionsPanel";
import type { Job } from "./types";

afterEach(cleanup);

test("metadata-only scoped jobs show zero added cards", () => {
  const records: Job[] = [
    {
      id: "scope",
      status: "succeeded",
      parameters: {
        kind: "collect_scope",
        spider: "tcgdex",
        languages: ["fr"],
        scope: { kind: "set", id: "swsh3" },
        force: false,
      },
      stats: {
        item_scraped_count: 2,
        "sets/stored": 1,
        "blocks/stored": 1,
        "cards/skipped_existing": 1,
      },
      error: null,
      created_at: "2026-11-13T12:00:00Z",
      finished_at: "2026-11-13T12:01:00Z",
    },
  ];
  const client = new QueryClient();
  function History() {
    const jobs = useQuery({
      queryKey: ["jobs"],
      queryFn: async () => records,
      initialData: records,
      staleTime: Infinity,
    });
    return (
      <CollectionsPanel
        jobs={jobs}
        onSelect={() => {}}
        onRepair={() => {}}
        repairing={false}
        repairError={false}
      />
    );
  }
  render(
    <QueryClientProvider client={client}>
      <History />
    </QueryClientProvider>,
  );
  const cells = within(screen.getAllByRole("row")[1]).getAllByRole("cell");
  expect(cells[3]).toHaveTextContent(/^0$/);
  expect(cells[4]).toHaveTextContent(/^1$/);
  client.clear();
});
