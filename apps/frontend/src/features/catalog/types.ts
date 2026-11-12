export type Card = {
  game: string;
  source: string;
  source_id: string;
  name: string;
  language: string;
  set_id: string;
  number: string;
  source_url: string;
  image_urls: string[];
  set_name: string | null;
  block_id: string | null;
  block_name: string | null;
  rarity: string | null;
  illustrators: string[];
  schema_version: number;
  updated_at: string;
};
export type Overview = {
  total: number;
  games: string[];
  languages: string[];
  sets: SetFacet[];
  blocks: BlockFacet[];
};
export type CardPage = {
  items: (Card & { versions: Card[] })[];
  total: number;
  page: number;
  page_size: number;
};
export type BlockFacet = {
  game: string;
  source: string;
  id: string;
  names: Record<string, string>;
};
type SetFacet = BlockFacet & { block_ids: Record<string, string> };
export type ResourceCost = {
  symbols?: string[] | null;
  value?: number | string | null;
  text?: string | null;
};
type CardFace = {
  name: string;
  types: string[];
  traits: Record<string, string[]>;
  texts: { kind: string; text: string }[];
  statistics: Record<string, number | string>;
  costs: Record<string, ResourceCost>;
  illustrators: string[];
  image_index?: number | null;
  abilities: {
    kind: string;
    name?: string | null;
    text?: string | null;
    damage?: string | null;
    cost?: ResourceCost | null;
    attributes: Record<string, unknown>;
  }[];
};
export type CardDetail = Card & {
  versions: Card[];
  set_info: {
    name: string | null;
    block: { id: string; name: string | null } | null;
    release_date: string | null;
    official_count: number | null;
    total_count: number | null;
  };
  faces: CardFace[];
  legalities: Record<string, string>;
  game_data: Record<string, unknown>;
  raw: Record<string, unknown>;
};
