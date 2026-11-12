import { render, screen } from "@testing-library/react";
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
