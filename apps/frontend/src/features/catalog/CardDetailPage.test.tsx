import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter, Route, Routes } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import { CardDetailPage } from "./CardDetailPage";

const card = {
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
  set_info: {
    official_count: 102,
    block: { id: "base", name: "Base" },
    release_date: "1999-01-09",
  },
  faces: [],
  legalities: {},
  game_data: {},
  raw: { name: "Dracaufeu" },
};
afterEach(() => vi.unstubAllGlobals());
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
