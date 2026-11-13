import { useEffect, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { Button } from "@/components/ui/button";
import { useI18n } from "@/shared/i18n";
import { getCollectionOptions } from "./api";
import type { CollectionScope } from "./types";

export function useCollectionScope(languages: string[], enabled: boolean) {
  const { locale } = useI18n();
  const [blockId, setBlockId] = useState("");
  const [setId, setSetId] = useState<string | null>("");
  const languageKey = [...languages].sort().join(",");
  const blocks = useQuery({
    queryKey: ["collection-options", "blocks", languageKey, locale],
    queryFn: () => getCollectionOptions("blocks", languages, locale),
    enabled,
    staleTime: 300_000,
    retry: false,
  });
  const block = blocks.data?.find((choice) => choice.id === blockId);
  const sets = useQuery({
    queryKey: ["collection-options", "sets", languageKey, locale, blockId],
    queryFn: () => getCollectionOptions("sets", languages, locale, blockId),
    enabled: enabled && (!blockId || !!block),
    staleTime: 300_000,
    retry: false,
  });
  const set = sets.data?.find((choice) => choice.id === setId);
  useEffect(() => {
    if (blocks.isSuccess && !blocks.isFetching && blockId && !block) {
      setBlockId("");
      setSetId(null);
    }
  }, [blocks.isSuccess, blocks.isFetching, blockId, block]);
  useEffect(() => {
    if (sets.isSuccess && !sets.isFetching && setId && !set) setSetId(null);
  }, [sets.isSuccess, sets.isFetching, setId, set]);
  const ready =
    enabled &&
    blocks.isSuccess &&
    sets.isSuccess &&
    !blocks.isFetching &&
    !sets.isFetching;
  const scope: CollectionScope | null =
    !ready || setId === null || (blockId && !block) || (setId && !set)
      ? null
      : set
        ? { kind: "set", id: set.id }
        : block
          ? { kind: "block", id: block.id }
          : null;
  return {
    blocks,
    sets,
    blockId,
    setId,
    scope,
    selected: setId === null ? undefined : setId ? set : block,
    selectBlock: (value: string) => {
      setBlockId(value);
      setSetId("");
    },
    selectSet: setSetId,
  };
}

export function CollectionScopePicker({
  selection,
  languages,
  enabled,
}: {
  selection: ReturnType<typeof useCollectionScope>;
  languages: string[];
  enabled: boolean;
}) {
  const { t, languageName } = useI18n();
  const { blocks, sets, blockId, setId, selected } = selection;
  const failed = blocks.isError || sets.isError;
  const loading =
    enabled &&
    (blocks.isPending ||
      sets.isPending ||
      blocks.isFetching ||
      sets.isFetching);
  const unavailable = selected
    ? languages.filter((language) => !selected.languages.includes(language))
    : [];
  return (
    <>
      <label>
        {t("Bloc")}
        <select
          value={blockId}
          onChange={(event) => selection.selectBlock(event.target.value)}
          disabled={!enabled || !blocks.isSuccess}
        >
          <option value="">{t("Tous les blocs")}</option>
          {blocks.data?.map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.name} · {choice.id}
            </option>
          ))}
        </select>
      </label>
      <label>
        {t("Extension")}
        <select
          value={setId ?? "__choose__"}
          onChange={(event) => selection.selectSet(event.target.value)}
          disabled={!enabled || !sets.isSuccess || loading || failed}
        >
          {setId === null && (
            <option value="__choose__" disabled>
              {t("Choisir une extension")}
            </option>
          )}
          <option value="">
            {blockId ? t("Tout le bloc") : t("Choisir une extension")}
          </option>
          {sets.data?.map((choice) => (
            <option key={choice.id} value={choice.id}>
              {choice.name} · {choice.id}
            </option>
          ))}
        </select>
      </label>
      {failed ? (
        <div>
          <p role="alert" className="error">
            {t("Impossible de charger les blocs et extensions.")}
          </p>
          <Button
            type="button"
            variant="outline"
            disabled={blocks.isFetching || sets.isFetching}
            onClick={() => {
              void blocks.refetch();
              void sets.refetch();
            }}
          >
            {t("Réessayer")}
          </Button>
        </div>
      ) : loading ? (
        <p role="status">{t("Chargement des blocs et extensions…")}</p>
      ) : enabled && !sets.data?.length ? (
        <p role="status">
          {t("Aucune extension disponible pour cette sélection.")}
        </p>
      ) : null}
      {unavailable.length > 0 && (
        <p className="info-note">
          {t("Indisponible pour : {languages}", {
            languages: unavailable.map(languageName).join(", "),
          })}
        </p>
      )}
      <small>
        {t(
          "Toutes les cartes du périmètre choisi seront parcourues. Les cartes déjà présentes sont ignorées sauf actualisation.",
        )}
      </small>
    </>
  );
}
