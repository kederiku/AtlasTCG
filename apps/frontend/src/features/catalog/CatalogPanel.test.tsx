import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { CatalogPanel } from "./CatalogPanel";

const overview = {
  total: 3,
  games: ["pokemon", "magic"],
  languages: ["fr"],
  blocks: [
    { game: "pokemon", source: "tcgdex", id: "base", names: { fr: "Base" } },
    {
      game: "pokemon",
      source: "tcgdex",
      id: "swsh",
      names: { fr: "Épée et Bouclier" },
    },
    {
      game: "magic",
      source: "other",
      id: "base",
      names: { fr: "Un autre bloc" },
    },
  ],
  sets: [
    {
      game: "pokemon",
      source: "tcgdex",
      id: "base1",
      names: { fr: "Set de Base" },
      block_ids: { fr: "base" },
    },
    {
      game: "pokemon",
      source: "tcgdex",
      id: "swsh1",
      names: { fr: "Épée et Bouclier" },
      block_ids: { fr: "swsh" },
    },
  ],
};
afterEach(() => vi.unstubAllGlobals());
function Address() {
  return <output aria-label="Adresse">{useLocation().search}</output>;
}
function mount(url: string, withOverview = true) {
  const fetcher = vi
    .fn()
    .mockImplementation(() =>
      Promise.resolve(
        new Response(
          JSON.stringify({ items: [], total: 0, page: 1, page_size: 24 }),
        ),
      ),
    );
  vi.stubGlobal("fetch", fetcher);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter initialEntries={[url]}>
        <CatalogPanel
          overview={withOverview ? overview : undefined}
          onCollect={() => {}}
        />
        <Address />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return fetcher;
}
test("selecting a block clears the previous set and page and restricts the extensions", async () => {
  const fetcher = mount(
    "/?game=pokemon&language=fr&set=pokemon%2Ftcgdex%2Fbase1&page=3",
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Filtrer par bloc" }),
    "pokemon/tcgdex/swsh",
  );
  expect(screen.getByRole("combobox", { name: "Filtrer par set" })).toHaveValue(
    "",
  );
  expect(
    screen.queryByRole("option", { name: "Set de Base (base1)" }),
  ).not.toBeInTheDocument();
  expect(screen.getByLabelText("Adresse").textContent).not.toContain("page=");
  await waitFor(() =>
    expect(fetcher.mock.lastCall?.[0]).toContain("block_id=swsh"),
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Filtrer par TCG" }),
    "magic",
  );
  expect(
    screen.getByRole("combobox", { name: "Filtrer par bloc" }),
  ).toHaveValue("");
});
test("a shared block URL filters immediately even while facets are loading", async () => {
  const fetcher = mount("/?language=fr&block=pokemon%2Ftcgdex%2Fbase", false);
  await waitFor(() => expect(fetcher).toHaveBeenCalled());
  const url = String(fetcher.mock.calls[0][0]);
  expect(url).toContain("game=pokemon");
  expect(url).toContain("source=tcgdex");
  expect(url).toContain("block_id=base");
});
