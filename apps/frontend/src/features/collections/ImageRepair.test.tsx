import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { MemoryRouter } from "react-router-dom";
import { afterEach, expect, test, vi } from "vitest";
import App from "@/app/App";

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});

function setup(locale: string, submit: () => Promise<Response>) {
  localStorage.setItem("atlasTCG.locale", locale);
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  let accepted = false;
  const job = {
    id: "12345678-1234-1234-1234-123456789012",
    status: "succeeded",
    parameters: { kind: "repair_images" },
    stats: {
      "images/examined": 6,
      "images/downloaded": 2,
      "images/present": 3,
      "images/unavailable": 1,
      "images/errors": 0,
    },
    error: null,
    created_at: "2026-11-12T12:00:00Z",
    started_at: null,
    finished_at: null,
  };
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string, options?: RequestInit) => {
      if (path === "/api/jobs" && options?.method === "POST") {
        expect(JSON.parse(String(options.body))).toEqual({
          kind: "repair_images",
        });
        expect(options.headers).toMatchObject({ "X-TCG-Admin": "1" });
        const response = await submit();
        if (!response.ok) return response;
        accepted = true;
        return Response.json(job, { status: 202 });
      }
      if (path === "/api/jobs") return Response.json(accepted ? [job] : []);
      if (path.endsWith("/logs"))
        return new Response("Image unavailable: pokemon/tcgdex/de/base1-4");
      if (path === "/api/overview")
        return Response.json({
          total: 6,
          games: [],
          languages: [],
          sets: [],
          blocks: [],
        });
      throw new Error(`Unexpected request: ${path}`);
    }),
  );
  const client = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  render(
    <QueryClientProvider client={client}>
      <MemoryRouter initialEntries={["/collections"]}>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
  return client;
}

test.each([
  [
    "fr",
    "Réparer les images manquantes",
    "Réparation des images",
    "Toutes les langues",
    "Journal",
    "Images téléchargées",
  ],
  [
    "en",
    "Repair missing images",
    "Image repair",
    "All card languages",
    "Log",
    "Downloaded images",
  ],
  [
    "es",
    "Reparar las imágenes que faltan",
    "Reparación de imágenes",
    "Todos los idiomas de cartas",
    "Registro",
    "Imágenes descargadas",
  ],
])(
  "requests a global repair and displays its result in %s",
  async (locale, button, title, languages, log, downloaded) => {
    const client = setup(
      locale,
      async () => new Response(null, { status: 202 }),
    );
    await userEvent.click(screen.getByRole("button", { name: button }));
    expect(
      await screen.findByText(title, { selector: "strong" }),
    ).toBeVisible();
    expect(screen.getByRole("cell", { name: languages })).toBeVisible();
    await userEvent.click(screen.getByRole("button", { name: log }));
    expect(
      await screen.findByText("Image unavailable: pokemon/tcgdex/de/base1-4"),
    ).toBeVisible();
    expect(screen.getByText(downloaded).nextElementSibling).toHaveTextContent(
      "2",
    );
    client.clear();
  },
);

test("prevents duplicate repair submission and allows retry after an error", async () => {
  let resolve: (response: Response) => void = () => {
    throw new Error("not started");
  };
  const response = new Promise<Response>((finish) => {
    resolve = finish;
  });
  const client = setup("fr", () => response);
  await userEvent.click(
    screen.getByRole("button", { name: "Réparer les images manquantes" }),
  );
  expect(
    screen.getByRole("button", { name: "Envoi en cours…" }),
  ).toBeDisabled();
  resolve(new Response(null, { status: 503 }));
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "La demande de réparation a échoué",
  );
  expect(
    screen.getByRole("button", { name: "Réparer les images manquantes" }),
  ).toBeEnabled();
  client.clear();
});
