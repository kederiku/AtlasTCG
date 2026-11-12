import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes, useLocation } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import App from "@/app/App";
import type { Card, CardDetail } from "./types";
import { CardDetailPage } from "./CardDetailPage";

const printing: Card = {
  game: "pokemon",
  source: "tcgdex",
  source_id: "base1-4",
  language: "fr",
  name: "Dracaufeu",
  set_id: "base1",
  set_name: "Set de Base",
  number: "4",
  source_url: "https://example.com",
  image_urls: [],
  rarity: "Rare",
  illustrators: ["Mitsuhiro Arita"],
  updated_at: "2026-11-12T12:00:00Z",
  block_id: "base",
  block_name: "Base",
  schema_version: 2,
};
const card: CardDetail = {
  ...printing,
  versions: [printing],
  set_info: {
    name: "Set de Base",
    total_count: 102,
    official_count: 102,
    block: { id: "base", name: "Base" },
    release_date: "1999-01-09",
  },
  faces: [],
  legalities: {},
  game_data: {},
  raw: { name: "Dracaufeu" },
};
afterEach(() => {
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
  localStorage.clear();
});
function mount(from?: string) {
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={client}>
      <MemoryRouter
        initialEntries={[
          { pathname: "/cards/pokemon/tcgdex/fr/base1-4", state: { from } },
        ]}
      >
        <Routes>
          <Route
            path="/cards/:game/:source/:language/:sourceId"
            element={<CardDetailPage />}
          />
          <Route path="/" element={<h1>Catalogue</h1>} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
test("opens a card from its direct URL as a page and returns to the catalog", async () => {
  const fetcher = vi
    .fn()
    .mockResolvedValue(new Response(JSON.stringify(card), { status: 200 }));
  vi.stubGlobal("fetch", fetcher);
  mount();
  expect(
    await screen.findByRole("heading", { name: "Dracaufeu", level: 1 }),
  ).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(document.title).toBe("Dracaufeu · Set de Base · atlasTCG");
  expect(screen.getByText("09 janvier 1999")).toBeVisible();
  expect(fetcher.mock.calls[0][0]).toContain("source_id=base1-4");
  await userEvent.click(
    screen.getByRole("link", { name: /Retour au catalogue/ }),
  );
  expect(screen.getByRole("heading", { name: "Catalogue" })).toBeVisible();
});
test("shows a missing-card page rather than an empty card", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockImplementation(() =>
      Promise.resolve(
        new Response(JSON.stringify({ detail: "Card not found" }), {
          status: 404,
        }),
      ),
    ),
  );
  mount();
  expect(
    await screen.findByRole("heading", { name: "Carte introuvable" }),
  ).toBeVisible();
});

test("returns to the catalog with the original filters and pagination", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn().mockResolvedValue(new Response(JSON.stringify(card))),
  );
  const from =
    "/?q=Dracaufeu&language=fr&game=pokemon&set=pokemon%2Ftcgdex%2Fbase1&page=2";
  mount(from);
  await screen.findByRole("heading", { name: "Dracaufeu", level: 1 });
  expect(
    screen.getByRole("link", { name: /Retour au catalogue/ }),
  ).toHaveAttribute("href", from);
});

function Address() {
  const location = useLocation();
  return (
    <output aria-label="Address">{location.pathname + location.search}</output>
  );
}

test("opens another localized printing and returns to the filtered catalog after switching the interface", async () => {
  const spanish: Card = {
    ...printing,
    language: "es-mx",
    name: "Charizard",
    set_name: "Conjunto Base",
    block_name: "Base ES",
  };
  const versions = [printing, spanish];
  const from =
    "/?q=Dracaufeu&language=fr&game=pokemon&block=pokemon%2Ftcgdex%2Fbase&set=pokemon%2Ftcgdex%2Fbase1&page=2";
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  const fetcher = vi.fn(async (path: string) => {
    const url = new URL(path, "http://localhost");
    if (url.pathname === "/api/overview")
      return Response.json({
        total: 50,
        games: ["pokemon"],
        languages: ["fr", "es-mx"],
        sets: [
          {
            game: "pokemon",
            source: "tcgdex",
            id: "base1",
            names: { fr: "Set de Base", en: "Base Set" },
            block_ids: { fr: "base", "es-mx": "base" },
          },
        ],
        blocks: [
          {
            game: "pokemon",
            source: "tcgdex",
            id: "base",
            names: { fr: "Base", en: "Base EN" },
          },
        ],
      });
    if (url.pathname === "/api/jobs") return Response.json([]);
    if (url.pathname === "/api/card-groups")
      return Response.json({
        items: [{ ...printing, versions }],
        total: 25,
        page: 2,
        page_size: 24,
      });
    if (url.pathname === "/api/cards/detail") {
      const localized =
        url.searchParams.get("language") === "es-mx" ? spanish : printing;
      return Response.json({
        ...card,
        ...localized,
        set_info: {
          ...card.set_info,
          name: localized.set_name,
          block: { id: "base", name: localized.block_name },
        },
        raw: { name: localized.name },
        versions,
      });
    }
    throw new Error(`Unexpected request: ${path}`);
  });
  vi.stubGlobal("fetch", fetcher);
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={[from]}>
        <App />
        <Address />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await userEvent.click(await screen.findByRole("link", { name: /Dracaufeu/ }));
  expect(
    await screen.findByRole("heading", { name: "Dracaufeu", level: 1 }),
  ).toBeVisible();
  expect(screen.getByLabelText("Address")).toHaveTextContent(
    "/cards/pokemon/tcgdex/fr/base1-4",
  );
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Langue de l’interface" }),
    "en",
  );
  expect(
    screen.getByRole("heading", { name: "Dracaufeu", level: 1 }),
  ).toBeVisible();
  expect(screen.getByLabelText("Address")).toHaveTextContent(
    "/cards/pokemon/tcgdex/fr/base1-4",
  );
  expect(document.title).toBe("Dracaufeu · Base Set · atlasTCG");
  await userEvent.click(
    screen.getByRole("link", { name: "ES-MX · Spanish (Mexico)" }),
  );
  expect(
    await screen.findByRole("heading", { name: "Charizard", level: 1 }),
  ).toBeVisible();
  expect(screen.getByLabelText("Address")).toHaveTextContent(
    "/cards/pokemon/tcgdex/es-mx/base1-4",
  );
  expect(
    screen.getByRole("link", { name: "ES-MX · Spanish (Mexico)" }),
  ).toHaveAttribute("aria-current", "page");
  const detailRequests = fetcher.mock.calls
    .map(([path]) => new URL(path, "http://localhost"))
    .filter((url) => url.pathname === "/api/cards/detail");
  expect(
    detailRequests.map((url) => Object.fromEntries(url.searchParams)),
  ).toEqual([
    { game: "pokemon", source: "tcgdex", language: "fr", source_id: "base1-4" },
    {
      game: "pokemon",
      source: "tcgdex",
      language: "es-mx",
      source_id: "base1-4",
    },
  ]);
  await userEvent.click(screen.getByRole("link", { name: "Back to catalog" }));
  expect(
    await screen.findByRole("heading", { name: "The catalog." }),
  ).toBeVisible();
  expect(screen.getByLabelText("Address").textContent).toBe(from);
  expect(screen.getByRole("combobox", { name: "Card language" })).toHaveValue(
    "fr",
  );
  expect(screen.getByRole("combobox", { name: "Filter by set" })).toHaveValue(
    "pokemon/tcgdex/base1",
  );
  expect(screen.getByText("25 cards · Page 2 of 2")).toBeVisible();
  client.clear();
});
