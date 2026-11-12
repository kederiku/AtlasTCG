import { render, screen, waitFor, cleanup } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { MemoryRouter } from "react-router-dom";
import { afterEach, test, expect, vi } from "vitest";
import App from "./App";

afterEach(() => {
  localStorage.clear();
  vi.unstubAllGlobals();
  vi.restoreAllMocks();
});
function mount() {
  vi.spyOn(window, "scrollTo").mockImplementation(() => {});
  vi.stubGlobal(
    "fetch",
    vi.fn(async (path: string) =>
      Response.json(
        path === "/api/overview"
          ? { total: 0, games: [], languages: [], sets: [], blocks: [] }
          : path === "/api/jobs"
            ? []
            : { items: [], total: 0, page: 1, page_size: 24 },
      ),
    ),
  );
  return render(
    <QueryClientProvider
      client={
        new QueryClient({ defaultOptions: { queries: { retry: false } } })
      }
    >
      <MemoryRouter>
        <App />
      </MemoryRouter>
    </QueryClientProvider>,
  );
}
test("switches the interface language and restores it after reload", async () => {
  mount();
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Langue de l’interface" }),
    "es",
  );
  expect(
    await screen.findByRole("heading", { name: "El catálogo." }),
  ).toBeVisible();
  await waitFor(() => expect(document.documentElement.lang).toBe("es"));
  cleanup();
  mount();
  expect(
    screen.getByRole("combobox", { name: "Idioma de la interfaz" }),
  ).toHaveValue("es");
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Idioma de la interfaz" }),
    "en",
  );
  expect(
    await screen.findByRole("heading", { name: "The catalog." }),
  ).toBeVisible();
});
test("an unknown or inaccessible preference falls back to French", async () => {
  localStorage.setItem("atlasTCG.locale", "xx");
  mount();
  expect(
    screen.getByRole("combobox", { name: "Langue de l’interface" }),
  ).toHaveValue("fr");
  cleanup();
  vi.spyOn(Storage.prototype, "getItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  vi.spyOn(Storage.prototype, "setItem").mockImplementation(() => {
    throw new Error("blocked");
  });
  mount();
  await userEvent.selectOptions(
    screen.getByRole("combobox", { name: "Langue de l’interface" }),
    "en",
  );
  expect(
    await screen.findByRole("heading", { name: "The catalog." }),
  ).toBeVisible();
});
