import { useI18n } from "@/shared/i18n";
import { useEffect, type ReactNode } from "react";
import type { UseQueryResult } from "@tanstack/react-query";
import { useLocation, useMatch, useNavigate } from "react-router-dom";
import {
  Layers3,
  LayoutGrid,
  Workflow,
  Plus,
  Database,
  Globe2,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import type { Overview } from "@/features/catalog/types";
export function WorkspaceLayout({
  overview,
  active,
  onCollect,
  children,
}: {
  overview: UseQueryResult<Overview>;
  active: number;
  onCollect: () => void;
  children: ReactNode;
}) {
  const { t, locale, setLocale } = useI18n();
  const navigate = useNavigate();
  const location = useLocation();
  const isCardPage = !!useMatch("/cards/:game/:source/:language/:sourceId");
  const tab = location.pathname === "/collections" ? "jobs" : "catalog";
  useEffect(() => {
    window.scrollTo(0, 0);
  }, [location.pathname]);
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <a className="brand" href="/" aria-label={t("atlasTCG accueil")}>
          <span className="brand-mark">
            <Layers3 size={23} />
          </span>
          <span>
            atlasTCG<span className="brand-dot">.</span>
          </span>
        </a>
        <div className="workspace-label">{t("ESPACE TCG")}</div>
        <nav aria-label={t("Navigation principale")}>
          <button
            className={tab === "catalog" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/")}
          >
            <LayoutGrid size={18} />
            {t("Catalogue")}
            <span>{overview.data?.total ?? "—"}</span>
          </button>
          <button
            className={tab === "jobs" ? "nav-item active" : "nav-item"}
            onClick={() => navigate("/collections")}
          >
            <Workflow size={18} />
            {t("Collectes")}
            {active > 0 && <span>{active}</span>}
          </button>
        </nav>
        <div className="sidebar-note">
          <div className="note-icon">
            <Database size={19} />
          </div>
          <strong>{t("Votre collection, réunie.")}</strong>
          <p>{t("Les cartes de vos TCG, toutes langues confondues.")}</p>
          <div className="local-status">
            <i />
            {t("Espace local")}
          </div>
        </div>
        <div className="sidebar-bottom">
          <span className="avatar">C</span>
          <div>
            {t("Administration")}
            <small>{t("Catalogue personnel")}</small>
          </div>
          <span className="version">v0.1</span>
        </div>
      </aside>
      <div className="main-shell">
        <header className="topbar">
          <span>
            {t("Espace")}
            <span className="slash">/</span>{" "}
            <strong>
              {isCardPage
                ? t("Fiche de carte")
                : tab === "catalog"
                  ? t("Catalogue")
                  : t("Collectes")}
            </strong>
          </span>
          <div className="topbar-actions">
            <label className="interface-language">
              <span className="sr-only">{t("Langue de l’interface")}</span>
              <select
                aria-label={t("Langue de l’interface")}
                value={locale}
                onChange={(event) => setLocale(event.target.value)}
              >
                <option value="fr">Français</option>
                <option value="en">English</option>
                <option value="es">Español</option>
              </select>
            </label>
            <span className="connection">
              <span className={overview.isError ? "dot red" : "dot"} />
              {overview.isError ? t("API inaccessible") : t("Stockage local")}
            </span>
          </div>
        </header>
        <main>
          {!isCardPage && (
            <>
              <div className="page-heading">
                <div>
                  <div className="eyebrow">
                    {t("VOTRE BIBLIOTHÈQUE DE CARTES")}
                  </div>
                  <h1>
                    {tab === "catalog"
                      ? t("Le catalogue.")
                      : t("Les collectes.")}
                  </h1>
                  <p>
                    {tab === "catalog"
                      ? t(
                          "Explorez les cartes importées, une édition à la fois.",
                        )
                      : t("Lancez vos spiders et suivez chaque importation.")}
                  </p>
                </div>
                <Button size="lg" onClick={onCollect}>
                  <Plus size={17} />
                  {t("Nouvelle collecte")}
                </Button>
              </div>
              <section className="metrics" aria-label={t("Statistiques")}>
                <div>
                  <span>
                    {t("Cartes en base")}
                    <Layers3 size={17} />
                  </span>
                  <strong>
                    {overview.data?.total.toLocaleString(locale) ?? "—"}
                  </strong>
                  <small>{t("Impressions localisées")}</small>
                </div>
                <div>
                  <span>
                    {t("Jeux de cartes")}
                    <LayoutGrid size={17} />
                  </span>
                  <strong>{overview.data?.games.length ?? "—"}</strong>
                  <small>{t("TCG dans le catalogue")}</small>
                </div>
                <div>
                  <span>
                    {t("Langues")}
                    <Globe2 size={17} />
                  </span>
                  <strong>{overview.data?.languages.length ?? "—"}</strong>
                  <small>{t("Versions disponibles")}</small>
                </div>
                <div>
                  <span>
                    {t("Extensions")}
                    <Database size={17} />
                  </span>
                  <strong>{overview.data?.sets.length ?? "—"}</strong>
                  <small>{t("Sets collectés")}</small>
                </div>
              </section>
            </>
          )}
          {children}
          <footer>
            <span>
              <Layers3 size={14} /> atlasTCG / TCG Catalog
            </span>
            <span>{t("Un catalogue qui grandit avec vous.")}</span>
          </footer>
        </main>
      </div>
    </div>
  );
}
