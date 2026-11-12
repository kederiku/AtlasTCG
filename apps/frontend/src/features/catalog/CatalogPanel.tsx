import { Link, useLocation } from "react-router-dom";
import { useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Search,
  Database,
  Layers3,
  RefreshCw,
  ArrowRight,
  ArrowUpRight,
  ChevronLeft,
  ChevronRight,
} from "lucide-react";
import { Input } from "@/components/ui/input";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { CardImage } from "./CardImage";
import type { Overview } from "./types";
import { getCards } from "./api";
import { useCatalogFilters } from "./useCatalogFilters";
import { cardPath } from "./cardNavigation";
import { facetKey, facetName, navigationName, printingNames } from "./facets";
import { useI18n } from "@/shared/i18n";
export function CatalogPanel({
  overview,
  onCollect,
}: {
  overview?: Overview;
  onCollect: () => void;
}) {
  const { locale, t, languageName } = useI18n();
  const queryClient = useQueryClient();
  const location = useLocation();
  const {
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
  } = useCatalogFilters();
  const cards = useQuery({
    queryKey: ["cards", q, language, game, blockId, setId, page, locale],
    queryFn: () =>
      getCards(
        new URLSearchParams({
          q,
          language,
          display_language: locale,
          game: selectedBlock?.game ?? selectedSet?.game ?? game,
          source: selectedBlock?.source ?? selectedSet?.source ?? "",
          set_id: selectedSet?.id ?? "",
          block_id: selectedBlock?.id ?? "",
          page: String(page),
          page_size: "24",
        }),
      ),
    refetchInterval: 5000,
  });
  return (
    <section className="catalog-section">
      <div className="section-heading">
        <h2>
          {t("Toutes les cartes")}{" "}
          <Badge variant="secondary">{cards.data?.total ?? 0}</Badge>
        </h2>
        <Button
          variant="ghost"
          size="sm"
          onClick={() => queryClient.invalidateQueries()}
        >
          <RefreshCw size={14} />
          {t("Actualiser")}
        </Button>
      </div>
      <div className="filterbar">
        <div className="search">
          <Search size={17} />
          <Input
            aria-label={t("Rechercher une carte, un bloc ou une extension")}
            placeholder={t("Carte, bloc ou extension…")}
            value={q}
            onChange={(e) => updateFilter("q", e.target.value)}
          />
        </div>
        <select
          aria-label={t("Filtrer par TCG")}
          value={game}
          onChange={(e) => updateFilter("game", e.target.value)}
        >
          <option value="">{t("Tous les TCG")}</option>
          {overview?.games.map((g) => (
            <option key={g} value={g}>
              {g}
            </option>
          ))}
        </select>
        <select
          aria-label={t("Langue des cartes")}
          value={language}
          onChange={(e) => updateFilter("language", e.target.value)}
        >
          <option value="">{t("Toutes les langues")}</option>
          {overview?.languages.map((l) => (
            <option key={l} value={l}>
              {languageName(l)}
            </option>
          ))}
        </select>
        <select
          aria-label={t("Filtrer par bloc")}
          value={blockId}
          onChange={(e) => updateFilter("block", e.target.value)}
        >
          <option value="">{t("Tous les blocs")}</option>
          {overview?.blocks
            .filter((block) => !game || block.game === game)
            .map((block) => (
              <option key={facetKey(block)} value={facetKey(block)}>
                {facetName(block, locale)} ({block.id})
              </option>
            ))}
        </select>
        <select
          aria-label={t("Filtrer par set")}
          value={setId}
          onChange={(e) => updateFilter("set", e.target.value)}
        >
          <option value="">{t("Toutes les extensions")}</option>
          {overview?.sets
            .filter((s) => !game || s.game === game)
            .filter(
              (s) =>
                !selectedBlock ||
                (s.game === selectedBlock.game &&
                  s.source === selectedBlock.source &&
                  Object.values(s.block_ids).includes(selectedBlock.id)),
            )
            .map((s) => (
              <option key={facetKey(s)} value={facetKey(s)}>
                {facetName(s, locale)} ({s.id})
              </option>
            ))}
        </select>
      </div>
      {cards.isError ? (
        <div role="alert" className="empty">
          <Database />
          <h3>{t("Connexion indisponible")}</h3>
          <p>{t("Vérifie que l’API et PostgreSQL sont démarrés.")}</p>
          <Button variant="outline" onClick={() => cards.refetch()}>
            {t("Réessayer")}
          </Button>
        </div>
      ) : cards.isPending ? (
        <div className="card-grid" aria-label={t("Chargement")}>
          {[0, 1, 2, 3].map((n) => (
            <div className="skeleton" key={n} />
          ))}
        </div>
      ) : cards.data.items.length === 0 ? (
        <div className="empty">
          <Layers3 />
          <h3>
            {q || language || game || blockId || setId
              ? t("Aucune carte ne correspond")
              : t("Votre catalogue commence ici")}
          </h3>
          <p>
            {q || language || game || blockId || setId
              ? t("Essayez un autre filtre ou une autre recherche.")
              : t(
                  "Lancez une première collecte pour retrouver vos cartes ici.",
                )}
          </p>
          <Button
            variant="outline"
            onClick={
              q || language || game || blockId || setId ? reset : onCollect
            }
          >
            {q || language || game || blockId || setId
              ? t("Réinitialiser les filtres")
              : t("Nouvelle collecte")}
            <ArrowRight size={15} />
          </Button>
        </div>
      ) : (
        <>
          <div className="card-grid">
            {cards.data.items.map((card) => (
              <article
                className="card-tile"
                key={`${card.game}/${card.source}/${card.source_id}`}
              >
                <Link
                  className="card-main-link"
                  to={cardPath(card)}
                  state={{ from: location.pathname + location.search }}
                >
                  <div className="card-stage">
                    <span className="lang-tag">
                      {card.language.toUpperCase()}
                    </span>
                    <CardImage card={card} />
                    <span className="card-peek">
                      <ArrowUpRight size={17} />
                    </span>
                  </div>
                  <div className="card-info">
                    <div className="card-game">
                      {card.game}
                      <span>#{card.number}</span>
                    </div>
                    <h3>{card.name}</h3>
                    <div className="card-meta">
                      <span title={card.set_id}>
                        {navigationName(
                          overview?.sets,
                          {
                            game: card.game,
                            source: card.source,
                            id: card.set_id,
                          },
                          locale,
                          printingNames(card.versions, "set", card.set_id),
                        )}
                      </span>
                      <span className="format-tag">WEBP</span>
                    </div>
                  </div>
                </Link>
                <nav
                  className="card-languages"
                  aria-label={t("Versions disponibles")}
                >
                  {card.versions.map((version) => (
                    <Link
                      key={version.language}
                      to={cardPath(version)}
                      state={{ from: location.pathname + location.search }}
                      title={languageName(version.language)}
                      aria-label={`${version.language.toUpperCase()} · ${languageName(version.language)}`}
                      className={
                        version.language === card.language ? "selected" : ""
                      }
                    >
                      {version.language.toUpperCase()}
                    </Link>
                  ))}
                </nav>
              </article>
            ))}
          </div>
          <div className="pagination">
            <span>
              {t(
                cards.data.total === 1
                  ? "{count} carte · Page {page} sur {pages}"
                  : "{count} cartes · Page {page} sur {pages}",
                {
                  count: cards.data.total.toLocaleString(locale),
                  page,
                  pages: Math.max(1, Math.ceil(cards.data.total / 24)),
                },
              )}
            </span>
            <div>
              <Button
                variant="outline"
                size="sm"
                aria-label={t("Page précédente")}
                disabled={page === 1}
                onClick={() => setPage(page - 1)}
              >
                <ChevronLeft />
              </Button>
              <Button
                variant="outline"
                size="sm"
                aria-label={t("Page suivante")}
                disabled={page * 24 >= cards.data.total}
                onClick={() => setPage(page + 1)}
              >
                <ChevronRight />
              </Button>
            </div>
          </div>
        </>
      )}
    </section>
  );
}
