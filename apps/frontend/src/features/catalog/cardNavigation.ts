import type { Card } from "./types";
export function cardPath(
  card: Pick<Card, "game" | "source" | "language" | "source_id">,
) {
  return (
    "/cards/" +
    [card.game, card.source, card.language, card.source_id]
      .map(encodeURIComponent)
      .join("/")
  );
}
