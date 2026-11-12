import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import App from "./App";

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

test.each([
  [
    "fr",
    "Nouvelle collecte",
    "Lancer la collecte",
    "Historique des collectes",
    "En attente",
    "Journal",
  ],
  [
    "en",
    "New collection",
    "Start collection",
    "Collection history",
    "Queued",
    "Log",
  ],
  [
    "es",
    "Nueva recopilación",
    "Iniciar recopilación",
    "Historial de recopilaciones",
    "En espera",
    "Registro",
  ],
])(
  "submits a collection and reads its log in %s",
  async (
    locale,
    createLabel,
    submitLabel,
    historyLabel,
    statusLabel,
    logLabel,
  ) => {
    localStorage.setItem("atlasTCG.locale", locale);
    vi.spyOn(window, "scrollTo").mockImplementation(() => {});
    const job = {
      id: "12345678-1234-1234-1234-123456789012",
      status: "queued",
      parameters: {
        spider: "tcgdex",
        languages: ["fr", "en"],
        card_ids: [],
        limit: 10,
        force: false,
      },
      stats: { "cards/stored": 10000 },
      error: null,
      created_at: "2026-11-12T12:00:00Z",
      started_at: null,
      finished_at: null,
    };
    let submitted = false;
    vi.stubGlobal(
      "fetch",
      vi.fn(async (path: string, options?: RequestInit) => {
        if (path === "/api/spiders")
          return Response.json([
            {
              id: "tcgdex",
              name: "TCGdex",
              game: "pokemon",
              languages: ["fr", "en"],
            },
          ]);
        if (path === "/api/jobs" && options?.method === "POST") {
          expect(JSON.parse(String(options.body))).toEqual(job.parameters);
          submitted = true;
          return Response.json(job, { status: 202 });
        }
        if (path === "/api/jobs") return Response.json(submitted ? [job] : []);
        if (path.endsWith("/logs"))
          return new Response("Collecte en attente de traitement");
        if (path === "/api/overview")
          return Response.json({
            total: 0,
            games: [],
            languages: [],
            sets: [],
            blocks: [],
          });
        if (path.startsWith("/api/card-groups"))
          return Response.json({ items: [], total: 0, page: 1, page_size: 24 });
        throw new Error(`Unexpected request: ${path}`);
      }),
    );
    const client = new QueryClient({
      defaultOptions: { queries: { retry: false } },
    });
    render(
      <QueryClientProvider client={client}>
        <MemoryRouter>
          <App />
        </MemoryRouter>
      </QueryClientProvider>,
    );
    await userEvent.click(screen.getByRole("button", { name: createLabel }));
    await screen.findByText("TCGdex · Pokémon");
    await userEvent.click(screen.getByRole("button", { name: submitLabel }));
    expect(
      await screen.findByRole("heading", { name: new RegExp(historyLabel) }),
    ).toBeInTheDocument();
    expect(
      await screen.findByText(statusLabel, { selector: ".job-status" }),
    ).toBeInTheDocument();
    expect(
      screen.getByRole("cell", {
        name: new Intl.NumberFormat(locale).format(10000),
      }),
    ).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: logLabel }));
    expect(
      await screen.findByText("Collecte en attente de traitement"),
    ).toBeInTheDocument();
    client.clear();
  },
);

test("preserves a failed collection request and prevents duplicate submission while it is pending", async () => {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  const parameters = {
    spider: "tcgdex",
    languages: ["fr", "en", "es-mx"],
    card_ids: ["base1-4", "base1-1"],
    limit: 37,
    force: true,
  };
  const job = {
    id: "12345678-1234-1234-1234-123456789012",
    status: "queued",
    parameters,
    stats: {},
    error: null,
    created_at: "2026-11-12T12:00:00Z",
    started_at: null,
    finished_at: null,
  };
  let finishFirstRequest: (response: Response) => void = () => {
    throw new Error("Request not started");
  };
  const firstResponse = new Promise<Response>((resolve) => {
    finishFirstRequest = resolve;
  });
  const submittedBodies: unknown[] = [];
  let accepted = false;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      if (path === "/api/spiders")
        return Response.json([
          {
            id: "tcgdex",
            name: "TCGdex",
            game: "pokemon",
            languages: ["fr", "en", "es-mx"],
          },
        ]);
      if (path === "/api/jobs" && options?.method === "POST") {
        submittedBodies.push(JSON.parse(String(options.body)));
        if (submittedBodies.length === 1) return firstResponse;
        accepted = true;
        return Response.json(job, { status: 202 });
      }
      if (path === "/api/jobs") return Response.json(accepted ? [job] : []);
      if (path === "/api/overview")
        return Response.json({
          total: 0,
          games: [],
          languages: [],
          sets: [],
          blocks: [],
        });
      if (path.startsWith("/api/card-groups"))
        return Response.json({ items: [], total: 0, page: 1, page_size: 24 });
      throw new Error(`Unexpected request: ${path}`);
    }),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Nouvelle collecte" }),
  );
  await userEvent.click(await screen.findByLabelText("Espagnol (Mexique)"));
  await userEvent.type(
    screen.getByPlaceholderText("base1-4, base1-1"),
    " base1-4 , base1-1 ",
  );
  await userEvent.clear(
    screen.getByRole("spinbutton", { name: /^Nombre maximal par langue/ }),
  );
  await userEvent.type(
    screen.getByRole("spinbutton", { name: /^Nombre maximal par langue/ }),
    "37",
  );
  await userEvent.click(
    screen.getByLabelText("Actualiser aussi les cartes déjà en base"),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  const pendingButton = await screen.findByRole("button", {
    name: "Envoi en cours…",
  });
  expect(pendingButton).toBeDisabled();
  await userEvent.click(pendingButton);
  expect(submittedBodies).toEqual([parameters]);
  finishFirstRequest(
    Response.json({ detail: "Service unavailable" }, { status: 503 }),
  );
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "La demande de collecte a échoué",
  );
  expect(screen.getByRole("dialog")).toBeVisible();
  expect(screen.getByPlaceholderText("base1-4, base1-1")).toHaveValue(
    " base1-4 , base1-1 ",
  );
  expect(
    screen.getByRole("spinbutton", { name: /^Nombre maximal par langue/ }),
  ).toHaveValue(37);
  for (const label of ["Français", "Anglais", "Espagnol (Mexique)"])
    expect(screen.getByLabelText(label)).toBeChecked();
  expect(
    screen.getByLabelText("Actualiser aussi les cartes déjà en base"),
  ).toBeChecked();
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(
    await screen.findByRole("heading", { name: /Historique des collectes/ }),
  ).toBeVisible();
  expect(
    await screen.findByText("En attente", { selector: ".job-status" }),
  ).toBeVisible();
  expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  expect(screen.getAllByRole("row")).toHaveLength(2);
  expect(submittedBodies).toEqual([parameters, parameters]);
  client.clear();
});
