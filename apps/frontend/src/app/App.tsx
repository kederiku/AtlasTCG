import { I18nProvider, useI18n } from "@/shared/i18n";
import { useQuery } from "@tanstack/react-query";
import { Routes, Route, Link } from "react-router-dom";
import { getOverview } from "@/features/catalog/api";
import { CatalogPanel } from "@/features/catalog/CatalogPanel";
import { CardDetailPage } from "@/features/catalog/CardDetailPage";
import { CollectionsPanel } from "@/features/collections/CollectionsPanel";
import { CollectionDialogs } from "@/features/collections/CollectionDialogs";
import { useCollections } from "@/features/collections/useCollections";
import { WorkspaceLayout } from "./WorkspaceLayout";
export default function App() {
  return (
    <I18nProvider>
      <Application />
    </I18nProvider>
  );
}
function Application() {
  const { t } = useI18n();
  const overview = useQuery({
    queryKey: ["overview"],
    queryFn: getOverview,
    refetchInterval: 5000,
  });
  const collections = useCollections();
  return (
    <>
      <WorkspaceLayout
        overview={overview}
        active={collections.active}
        onCollect={collections.openForm}
      >
        <Routes>
          <Route
            path="/"
            element={
              <CatalogPanel
                overview={overview.data}
                onCollect={collections.openForm}
              />
            }
          />
          <Route
            path="/collections"
            element={
              <CollectionsPanel
                jobs={collections.jobs}
                onSelect={collections.setSelectedJob}
              />
            }
          />
          <Route
            path="/cards/:game/:source/:language/:sourceId"
            element={<CardDetailPage overview={overview.data} />}
          />
          <Route
            path="*"
            element={
              <section>
                <h1>{t("Page introuvable")}</h1>
                <Link to="/">{t("Retour au catalogue")}</Link>
              </section>
            }
          />
        </Routes>
      </WorkspaceLayout>
      <CollectionDialogs collections={collections} />
    </>
  );
}
