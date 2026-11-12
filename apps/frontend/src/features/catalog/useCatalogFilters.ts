import { useSearchParams } from "react-router-dom";
import { parseFacetKey } from "./facets";

export function useCatalogFilters() {
  const [filters, setFilters] = useSearchParams();
  const q = filters.get("q") ?? "";
  const language = filters.get("language") ?? "";
  const game = filters.get("game") ?? "";
  const setId = filters.get("set") ?? "";
  const blockId = filters.get("block") ?? "";
  const requestedPage = Number(filters.get("page"));
  const page =
    Number.isSafeInteger(requestedPage) && requestedPage > 0
      ? requestedPage
      : 1;
  const updateFilter = (key: string, value: string) => {
    setFilters(
      (previous) => {
        const next = new URLSearchParams(previous);
        if (value) next.set(key, value);
        else next.delete(key);
        next.delete("page");
        if (key === "game") next.delete("block");
        if (key === "block") {
          const selected = parseFacetKey(value);
          if (selected) next.set("game", selected.game);
        }
        if (["game", "block"].includes(key)) next.delete("set");
        return next;
      },
      { replace: true },
    );
  };
  const setPage = (value: number) => {
    setFilters((previous) => {
      const next = new URLSearchParams(previous);
      next.set("page", String(value));
      return next;
    });
  };
  const selectedSet = parseFacetKey(setId);
  const selectedBlock = parseFacetKey(blockId);
  const reset = () => setFilters({});
  return {
    q,
    language,
    game,
    setId,
    blockId,
    page,
    updateFilter,
    setPage,
    selectedSet,
    selectedBlock,
    reset,
  };
}
