import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { cleanup, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, expect, test, vi } from "vitest";
import { CollectForm } from "./CollectForm";

const languages = [
  "en",
  "fr",
  "es",
  "es-mx",
  "it",
  "pt",
  "pt-br",
  "pt-pt",
  "de",
  "nl",
  "pl",
  "ru",
  "ja",
  "ko",
  "zh-tw",
  "id",
  "th",
  "zh-cn",
];
const connector = { id: "tcgdex", name: "TCGdex", game: "pokemon", languages };
let client: QueryClient;

beforeEach(() => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => {
      if (path === "/api/spiders") return Response.json([connector]);
      throw new Error(`Unexpected request: ${path}`);
    }),
  );
});

afterEach(() => {
  cleanup();
  client.clear();
  vi.unstubAllGlobals();
});

function renderForm(submit = vi.fn()) {
  render(
    <QueryClientProvider client={client}>
      <CollectForm onSubmit={submit} pending={false} />
    </QueryClientProvider>,
  );
  return submit;
}

test("requests a bounded collection without forcing already collected cards", async () => {
  const submit = vi.fn();
  renderForm(submit);
  await screen.findByLabelText("Français");
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith({
    spider: "tcgdex",
    languages: ["fr", "en"],
    card_ids: [],
    limit: 10,
    force: false,
  });
});

test("submits explicit card identifiers and an intentional refresh", async () => {
  const submit = vi.fn();
  renderForm(submit);
  await screen.findByLabelText("Français");
  await userEvent.type(
    screen.getByPlaceholderText("base1-4, base1-1"),
    "base1-4, base1-1",
  );
  await userEvent.click(
    screen.getByLabelText("Actualiser aussi les cartes déjà en base"),
  );
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({ card_ids: ["base1-4", "base1-1"], force: true }),
  );
});

test("offers all eighteen API languages and submits their exact codes", async () => {
  const submit = renderForm();
  await screen.findByLabelText("Français");
  const choices = within(
    screen.getByRole("group", { name: "Langues" }),
  ).getAllByRole("checkbox");
  expect(choices).toHaveLength(18);
  expect(screen.getByLabelText("Français")).toBeChecked();
  expect(screen.getByLabelText("Anglais")).toBeChecked();
  expect(choices.filter((choice) => choice.matches(":checked"))).toHaveLength(
    2,
  );
  for (const choice of choices) {
    if (!choice.matches(":checked")) await userEvent.click(choice);
  }
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({
      languages: [
        "fr",
        "en",
        "es",
        "es-mx",
        "it",
        "pt",
        "pt-br",
        "pt-pt",
        "de",
        "nl",
        "pl",
        "ru",
        "ja",
        "ko",
        "zh-tw",
        "id",
        "th",
        "zh-cn",
      ],
    }),
  );
});

test("only offers and submits languages declared by the API", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () =>
      Response.json([{ ...connector, languages: ["fr", "pt-br"] }]),
    ),
  );
  const submit = renderForm();
  await screen.findByLabelText("Portugais (Brésil)");
  expect(
    within(screen.getByRole("group", { name: "Langues" })).getAllByRole(
      "checkbox",
    ),
  ).toHaveLength(2);
  expect(screen.queryByLabelText("Anglais")).not.toBeInTheDocument();
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({ languages: ["fr"] }),
  );
});

test("prevents submission while the language registry is loading", () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(() => new Promise<Response>(() => {})),
  );
  renderForm();
  expect(screen.getByRole("status")).toHaveTextContent(
    "Chargement des langues",
  );
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
});

test("allows retrying the registry after a loading failure", async () => {
  vi.stubGlobal(
    "fetch",
    vi
      .fn()
      .mockResolvedValueOnce(Response.json({}, { status: 503 }))
      .mockImplementation(async () => Response.json([connector])),
  );
  renderForm();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Impossible de charger les langues",
  );
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
  await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
  await screen.findByLabelText("Français");
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeEnabled();
});

test("prevents submission when the connector is unavailable", async () => {
  vi.stubGlobal(
    "fetch",
    vi.fn(async () => Response.json([])),
  );
  renderForm();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Source TCGdex indisponible",
  );
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
});

test("prevents submission when no language is selected", async () => {
  renderForm();
  await userEvent.click(await screen.findByLabelText("Français"));
  await userEvent.click(screen.getByLabelText("Anglais"));
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
});
