import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { expect, test } from "vitest";
import { CardRules } from "./CardRules";

test("shows normalized stats, rules, costs and artists without interpreting printed symbols", () => {
  render(
    <CardRules
      card={{
        illustrators: ["Mitsuhiro Arita"],
        rarity: "Rare",
        legalities: {},
        game_data: {},
        faces: [
          {
            name: "Dracaufeu",
            types: ["Pokémon"],
            traits: { types: ["Feu"] },
            statistics: { hp: 120 },
            texts: [{ kind: "flavor", text: "Il peut fondre la roche." }],
            costs: { retreat: { value: 3 } },
            illustrators: [],
            abilities: [
              {
                kind: "attack",
                name: "Danseflamme",
                text: "Défaussez 2 cartes Énergie.",
                cost: { symbols: ["Feu", "Feu", "Feu", "Feu"] },
                damage: "100+",
                attributes: {},
              },
            ],
          },
        ],
      }}
    />,
  );
  expect(screen.getByText("Mitsuhiro Arita")).toBeVisible();
  expect(screen.getByText("PV")).toBeVisible();
  expect(screen.getByText("120")).toBeVisible();
  expect(screen.getByText("100+")).toBeVisible();
  expect(screen.getByText("Feu · Feu · Feu · Feu")).toBeVisible();
  expect(screen.getByText("Défaussez 2 cartes Énergie.")).toBeVisible();
});

test("keeps both faces and distinguishes zero costs from missing costs", () => {
  const face = {
    name: "Recto",
    types: [],
    traits: {},
    statistics: {},
    texts: [],
    costs: {},
    illustrators: [],
    abilities: [],
  };
  render(
    <CardRules
      card={{
        illustrators: [],
        rarity: null,
        legalities: {},
        game_data: {},
        faces: [
          {
            ...face,
            name: "Recto",
            statistics: { hp: 0 },
            costs: {
              retreat: { value: 0 },
              play: { symbols: [] },
              attack_cost: { value: null, symbols: null, text: null },
            },
          },
          {
            ...face,
            name: "Verso",
            abilities: [
              {
                kind: "attack",
                name: "Force variable",
                damage: "20×",
                text: "Texte source inchangé",
                attributes: {},
                cost: { text: "X" },
              },
            ],
          },
        ],
      }}
    />,
  );
  expect(screen.getByRole("heading", { name: "Face 1 · Recto" })).toBeVisible();
  expect(screen.getByRole("heading", { name: "Face 2 · Verso" })).toBeVisible();
  const [front, back] = screen.getAllByRole("article");
  expect(within(front).getAllByText("0", { selector: "dd" })).toHaveLength(3);
  expect(
    within(front).getByText("Non renseigné", { selector: "dd" }),
  ).toBeVisible();
  expect(within(back).getByText("20×")).toBeVisible();
  expect(within(back).getByText("X")).toBeVisible();
  expect(within(back).getByText("Texte source inchangé")).toBeVisible();
});

test("retains null, false and zero in source-specific data", async () => {
  render(
    <CardRules
      card={{
        illustrators: [],
        rarity: null,
        faces: [],
        legalities: {},
        game_data: {
          pokemon: {
            variants: { normal: false, reverse: true },
            dexId: [0, null],
          },
        },
      }}
    />,
  );
  await userEvent.click(screen.getByText("Informations spécifiques · pokemon"));
  expect(screen.getByText("Non")).toBeVisible();
  expect(screen.getByText("Oui")).toBeVisible();
  expect(screen.getByText("0")).toBeVisible();
  expect(screen.getByText("Non renseigné", { selector: "span" })).toBeVisible();
});
