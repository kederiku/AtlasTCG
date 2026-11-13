import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { act, cleanup, render, screen, within } from "@testing-library/react";
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
function optionResponse(path: string): Response {
  const url = new URL(path, "http://localhost");
  const selected = url.searchParams.get("languages")?.split(",") ?? [];
  const available = ["fr", "en"].filter((lang) => selected.includes(lang));
  if (url.pathname.endsWith("/blocks"))
    return Response.json(
      available.length
        ? [
            { id: "swsh", name: "Épée et Bouclier", languages: available },
            { id: "base", name: "Base", languages: available },
          ]
        : [],
    );
  const options =
    url.searchParams.get("block_id") === "base"
      ? [{ id: "base1", name: "Set de Base", languages: available }]
      : [
          { id: "swsh12.5", name: "Zénith Suprême", languages: available },
          {
            id: "orphan",
            name: "Sans bloc",
            languages: selected.includes("en") ? ["en"] : [],
          },
        ];
  return Response.json(options.filter((item) => item.languages.length));
}
async function chooseSet() {
  await screen.findByRole("option", { name: /Zénith Suprême/ });
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Extension" }),
    "swsh12.5",
  );
}

beforeEach(() => {
  client = new QueryClient({ defaultOptions: { queries: { retry: false } } });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => {
      if (path === "/api/spiders") return Response.json([connector]);
      if (path.startsWith("/api/collection-options/"))
        return optionResponse(path);
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

test("requests a complete extension without forcing existing cards or applying a limit", async () => {
  const submit = vi.fn();
  renderForm(submit);
  await screen.findByLabelText("Français");
  await chooseSet();
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith({
    spider: "tcgdex",
    languages: ["fr", "en"],
    kind: "collect_scope",
    scope: { kind: "set", id: "swsh12.5" },
    force: false,
  });
});

test("submits explicit card identifiers and an intentional refresh", async () => {
  const submit = vi.fn();
  renderForm(submit);
  await screen.findByLabelText("Français");
  await userEvent.click(screen.getByLabelText("Cartes précises (avancé)"));
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
    expect.objectContaining({
      card_ids: ["base1-4", "base1-1"],
      limit: 2,
      force: true,
    }),
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
  await chooseSet();
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
    vi.fn(async (path: string) =>
      path === "/api/spiders"
        ? Response.json([{ ...connector, languages: ["fr", "pt-br"] }])
        : optionResponse(path),
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
  await chooseSet();
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
      .mockImplementation(async (path: string) =>
        path === "/api/spiders"
          ? Response.json([connector])
          : optionResponse(path),
      ),
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
  await chooseSet();
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

test("requires a target and submits an entire block after resetting its extension", async () => {
  const submit = renderForm();
  await screen.findByRole("option", { name: /Épée et Bouclier/ });
  expect(screen.queryByRole("spinbutton")).not.toBeInTheDocument();
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
  await chooseSet();
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Bloc" }),
    "swsh",
  );
  expect(screen.getByRole("combobox", { name: "Extension" })).toHaveValue("");
  await screen.findByRole("option", { name: /Zénith Suprême/ });
  await userEvent.click(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  );
  expect(submit).toHaveBeenCalledWith(
    expect.objectContaining({ scope: { kind: "block", id: "swsh" } }),
  );
});

test("shows unavailable languages and clears a set no longer available after changing languages", async () => {
  renderForm();
  await screen.findByRole("option", { name: /Épée et Bouclier/ });
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Bloc" }),
    "swsh",
  );
  await screen.findByRole("option", { name: /Sans bloc/ });
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Extension" }),
    "orphan",
  );
  expect(screen.getByText(/Indisponible pour : Français/)).toBeVisible();
  await userEvent.click(screen.getByLabelText("Anglais"));
  await screen.findByRole("option", { name: /Zénith Suprême/ });
  expect(
    screen.getByRole("combobox", { name: "Extension" }),
  ).toHaveDisplayValue("Choisir une extension");
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
});

test("blocks submission on a source error and allows retrying", async () => {
  let fail = true;
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) =>
      path === "/api/spiders"
        ? Response.json([connector])
        : fail
          ? Response.json({}, { status: 503 })
          : optionResponse(path),
    ),
  );
  renderForm();
  expect(await screen.findByRole("alert")).toHaveTextContent(
    "Impossible de charger les blocs et extensions",
  );
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
  fail = false;
  await userEvent.click(screen.getByRole("button", { name: "Réessayer" }));
  await chooseSet();
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeEnabled();
});

test("late options for the previous block cannot replace the current selection", async () => {
  let finish: (response: Response) => void = () => {};
  const delayed = new Promise<Response>((resolve) => {
    finish = resolve;
  });
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) => {
      if (path === "/api/spiders") return Response.json([connector]);
      if (path.includes("block_id=swsh")) return delayed;
      return optionResponse(path);
    }),
  );
  renderForm();
  await screen.findByRole("option", { name: /Épée et Bouclier/ });
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Bloc" }),
    "swsh",
  );
  expect(
    screen.getByRole("button", { name: "Lancer la collecte" }),
  ).toBeDisabled();
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Bloc" }),
    "base",
  );
  await screen.findByRole("option", { name: /Set de Base/ });
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Extension" }),
    "base1",
  );
  await act(async () =>
    finish(Response.json([{ id: "swsh12.5", name: "Old", languages: ["fr"] }])),
  );
  expect(screen.getByRole("combobox", { name: "Bloc" })).toHaveValue("base");
  expect(screen.getByRole("combobox", { name: "Extension" })).toHaveValue(
    "base1",
  );
});
