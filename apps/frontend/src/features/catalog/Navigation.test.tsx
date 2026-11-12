import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, useLocation } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { I18nProvider, useI18n } from "@/shared/i18n";
import { CatalogPanel } from "./CatalogPanel";
import { facetName, navigationName } from "./facets";

const names = {
  fr: "Destinées Futures",
  en: "Next Destinies",
  es: "Destinos Futuros",
};
const overview = {
  total: 2,
  games: ["pokemon"],
  languages: ["fr", "es"],
  blocks: [
    {
      game: "pokemon",
      source: "tcgdex",
      id: "bw",
      names: { fr: "Noir et Blanc", es: "Negro y Blanco" },
    },
  ],
  sets: [
    {
      game: "pokemon",
      source: "tcgdex",
      id: "bw4",
      names,
      block_ids: { fr: "bw", es: "bw" },
    },
  ],
};
const versions = ["fr", "es"].map((language) => ({
  game: "pokemon",
  source: "tcgdex",
  source_id: "bw4-1",
  language,
  name: language === "fr" ? "Carte française" : "Carta española",
  set_id: "bw4",
  number: "1",
  image_urls: [],
  source_url: "https://example.com",
  set_name: names[language === "fr" ? "fr" : "es"],
  block_id: "bw",
  block_name: "",
  rarity: null,
  illustrators: [],
  schema_version: 2,
  updated_at: "2026-11-12T12:00:00Z",
}));
afterEach(() => {
  vi.unstubAllGlobals();
  localStorage.clear();
});
function Controls() {
  const { setLocale } = useI18n();
  return (
    <>
      <button onClick={() => setLocale("en")}>Switch interface</button>
      <output aria-label="Address">{useLocation().search}</output>
    </>
  );
}
test("keeps one translated extension and one card while changing the card language", async () => {
  const fetcher = vi.fn(async (path: string) => {
    const language = new URL(path, "http://localhost").searchParams.get(
      "language",
    );
    return Response.json({
      items: [{ ...versions[language === "es" ? 1 : 0], versions }],
      total: 1,
      page: 1,
      page_size: 24,
    });
  });
  vi.stubGlobal("fetch", fetcher);
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <I18nProvider initialLocale="fr">
        <MemoryRouter
          initialEntries={[
            "/?game=pokemon&language=es&block=pokemon%2Ftcgdex%2Fbw&set=pokemon%2Ftcgdex%2Fbw4",
          ]}
        >
          <CatalogPanel overview={overview} onCollect={() => {}} />
          <Controls />
        </MemoryRouter>
      </I18nProvider>
    </QueryClientProvider>,
  );
  expect(
    screen.getByRole("option", { name: "Destinées Futures (bw4)" }),
  ).toBeVisible();
  expect(
    screen.getByRole("option", { name: "Noir et Blanc (bw)" }),
  ).toBeVisible();
  expect(
    await screen.findByRole("heading", { name: "Carta española" }),
  ).toBeVisible();
  expect(document.querySelectorAll(".card-tile")).toHaveLength(1);
  expect(screen.getByRole("link", { name: /^FR ·/ })).toHaveAttribute(
    "href",
    "/cards/pokemon/tcgdex/fr/bw4-1",
  );
  expect(screen.getByRole("link", { name: /^ES ·/ })).toHaveAttribute(
    "href",
    "/cards/pokemon/tcgdex/es/bw4-1",
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Langue des cartes" }),
    "fr",
  );
  expect(screen.getByRole("combobox", { name: "Filtrer par set" })).toHaveValue(
    "pokemon/tcgdex/bw4",
  );
  await waitFor(() =>
    expect(fetcher.mock.lastCall?.[0]).toContain("language=fr"),
  );
  expect(fetcher.mock.lastCall?.[0]).toContain("/api/card-groups?");
  await userEvent.click(
    screen.getByRole("button", { name: "Switch interface" }),
  );
  expect(
    screen.getByRole("option", { name: "Next Destinies (bw4)" }),
  ).toBeVisible();
  expect(screen.getByLabelText("Address").textContent).toContain("language=fr");
  await waitFor(() =>
    expect(fetcher.mock.lastCall?.[0]).toContain("display_language=en"),
  );
});
test("uses a stable French fallback when the interface translation is missing", () => {
  expect(
    facetName(
      {
        game: "pokemon",
        source: "tcgdex",
        id: "bw4",
        names: { fr: "Destinées Futures", en: "Next Destinies" },
      },
      "es",
    ),
  ).toBe("Destinées Futures");
});

test("keeps navigation names stable while facets are unavailable", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json({
        items: [{ ...versions[1], versions }],
        total: 1,
        page: 1,
        page_size: 24,
      }),
    ),
  );
  render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <CatalogPanel onCollect={() => {}} />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  expect(await screen.findByText("Destinées Futures")).toBeVisible();
  expect(screen.queryByText("Destinos Futuros")).not.toBeInTheDocument();
  expect(
    navigationName(
      undefined,
      { game: "pokemon", source: "tcgdex", id: "bw4" },
      "fr",
    ),
  ).toBe("bw4");
});
