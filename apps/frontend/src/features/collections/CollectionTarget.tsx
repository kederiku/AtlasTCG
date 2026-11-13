import { useI18n } from "@/shared/i18n";
import type { ScopedCollectionRequest } from "./types";

export function CollectionTarget({
  request,
}: {
  request: ScopedCollectionRequest;
}) {
  const { t } = useI18n();
  return (
    <>
      {t(request.scope.kind === "block" ? "Bloc" : "Extension")}:{" "}
      {request.scope.id}
      {" · "}
      {t(
        request.force
          ? "Actualiser aussi les cartes déjà en base"
          : "Sans actualisation",
      )}
    </>
  );
}
