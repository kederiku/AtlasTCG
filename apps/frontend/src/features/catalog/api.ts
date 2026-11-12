import { api } from "@/shared/http/client";
import type { CardDetail, CardPage, Overview } from "./types";

export const getOverview = () => api<Overview>("/overview");
export const getCards = (parameters: URLSearchParams) =>
  api<CardPage>("/card-groups?" + parameters);
export const getCard = (identity: {
  game: string;
  source: string;
  language: string;
  source_id: string;
}) => api<CardDetail>("/cards/detail?" + new URLSearchParams(identity));
