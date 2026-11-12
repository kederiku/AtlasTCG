import type { BlockFacet, Card } from "./types";

export function facetKey(facet: Pick<BlockFacet, "game" | "source" | "id">) {
  return `${facet.game}/${facet.source}/${facet.id}`;
}

export function parseFacetKey(value: string) {
  const [game, source, ...parts] = value.split("/");
  const id = parts.join("/");
  return game && source && id ? { game, source, id } : undefined;
}

export function facetName(facet: BlockFacet, language: string) {
  return (
    facet.names[language || "fr"] ??
    facet.names.fr ??
    facet.names.en ??
    Object.entries(facet.names).sort(([a], [b]) =>
      a.localeCompare(b),
    )[0]?.[1] ??
    facet.id
  );
}

export function navigationName(
  facets: BlockFacet[] | undefined,
  identity: { game: string; source: string; id: string },
  locale: string,
  names: Record<string, string> = {},
) {
  const facet = facets?.find((item) => facetKey(item) === facetKey(identity));
  return facetName(facet ?? { ...identity, names }, locale);
}

export function printingNames(
  versions: Card[],
  kind: "set" | "block",
  id: string,
) {
  const names: Record<string, string> = {};
  for (const version of versions) {
    const matches = (kind === "set" ? version.set_id : version.block_id) === id;
    const name = kind === "set" ? version.set_name : version.block_name;
    if (matches && name) names[version.language] = name;
  }
  return names;
}
