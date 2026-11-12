import { useI18n } from "@/shared/i18n";
import type { Overview } from "./types";
import { cardPath } from "./cardNavigation";
import { useQuery } from "@tanstack/react-query";
import { ArrowLeft, ArrowUpRight } from "lucide-react";
import { Link, useParams, useLocation } from "react-router-dom";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { CardImage } from "./CardImage";
import { date, calendarDate } from "@/shared/format";
import { ApiError } from "@/shared/http/client";
import { getCard } from "./api";
import { CardRules } from "./CardRules";
import { navigationName, facetKey, printingNames } from "./facets";
export function CardDetailPage({ overview }: { overview?: Overview }) {
  const { t, locale, languageName } = useI18n();
  const { game = "", source = "", language = "", sourceId = "" } = useParams();
  const location = useLocation();
  const from = location.state?.from;
  const backTo =
    typeof from === "string" && (from === "/" || from.startsWith("/?"))
      ? from
      : "/";
  const identity = { game, source, language, source_id: sourceId };
  const result = useQuery({
    queryKey: ["card-detail", identity],
    queryFn: () => getCard(identity),
    retry: false,
  });
  if (result.isPending)
    return (
      <section className="card-detail-page" aria-busy="true">
        <Link to={backTo}>{t("Retour au catalogue")}</Link>
        <p role="status">{t("Chargement des caractéristiques…")}</p>
      </section>
    );
  if (result.isError)
    return (
      <section className="card-detail-page" role="alert">
        <Link to={backTo}>{t("Retour au catalogue")}</Link>
        <h1>
          {result.error instanceof ApiError && result.error.status === 404
            ? t("Carte introuvable")
            : t("Impossible de charger la fiche")}
        </h1>
        <p>{t("Vérifie le lien ou reviens au catalogue.")}</p>
        <Button onClick={() => result.refetch()}>{t("Réessayer")}</Button>
      </section>
    );
  const detail = result.data;
  const setName = navigationName(
    overview?.sets,
    { game: detail.game, source: detail.source, id: detail.set_id },
    locale,
    printingNames(detail.versions ?? [detail], "set", detail.set_id),
  );
  const block = detail.set_info.block;
  const blockName = block
    ? navigationName(
        overview?.blocks,
        { game: detail.game, source: detail.source, id: block.id },
        locale,
        printingNames(
          detail.versions ?? [
            { ...detail, block_id: block.id, block_name: block.name },
          ],
          "block",
          block.id,
        ),
      )
    : "";
  return (
    <article className="card-detail-page">
      <title>{`${detail.name} · ${setName} · atlasTCG`}</title>
      <Link className="back-to-catalog" to={backTo}>
        <ArrowLeft size={16} />
        {t("Retour au catalogue")}
      </Link>
      <header className="card-page-heading">
        <div className="eyebrow">
          {t("FICHE DE CARTE")} · {detail.game}
        </div>
        <h1>{detail.name}</h1>
        <p>
          {setName} · #{detail.number} · {detail.language.toUpperCase()}
        </p>
      </header>
      <nav
        className="card-languages detail-languages"
        aria-label={t("Versions disponibles")}
      >
        {(detail.versions ?? [detail]).map((version) => (
          <Link
            key={version.language}
            to={cardPath(version)}
            state={{ from: backTo }}
            aria-current={
              version.language === detail.language ? "page" : undefined
            }
            className={version.language === detail.language ? "selected" : ""}
          >
            {version.language.toUpperCase()} · {languageName(version.language)}
          </Link>
        ))}
      </nav>
      <div className="detail-grid">
        <div className="detail-image">
          <CardImage card={detail} />
        </div>
        <div className="detail-info">
          <Badge variant="secondary">{detail.source}</Badge>
          <h3>{setName}</h3>
          <dl>
            <dt>{t("Code de l’extension")}</dt>
            <dd>{detail.set_id}</dd>
            <dt>{t("Numéro de collection")}</dt>
            <dd>
              {detail.number}
              {detail.set_info.official_count
                ? ` / ${detail.set_info.official_count}`
                : ""}
            </dd>
            <dt>{t("Bloc")}</dt>
            <dd>
              {detail.set_info.block ? (
                <Link
                  className="source-link"
                  to={
                    "/?" +
                    new URLSearchParams({
                      game: detail.game,
                      language: detail.language,
                      block: facetKey({
                        game: detail.game,
                        source: detail.source,
                        id: detail.set_info.block.id,
                      }),
                    })
                  }
                >
                  {blockName}
                </Link>
              ) : (
                t("Non renseigné")
              )}
            </dd>
            <dt>{t("Sortie du set")}</dt>
            <dd>
              {detail.set_info.release_date
                ? calendarDate(detail.set_info.release_date, locale)
                : t("Non renseignée")}
            </dd>
            <dt>{t("Dernière collecte")}</dt>
            <dd>{date(detail.updated_at, locale)}</dd>
          </dl>
          <a
            href={detail.source_url}
            target="_blank"
            rel="noreferrer"
            className="source-link"
          >
            {t("Voir la source")}
            <ArrowUpRight size={14} />
          </a>
          {detail.image_urls.map((url, index) => (
            <a
              className="source-link"
              key={url}
              href={url}
              target="_blank"
              rel="noreferrer"
            >
              {t("Ouvrir l’image WebP {number}", { number: index + 1 })}
              <ArrowUpRight size={14} />
            </a>
          ))}
        </div>
      </div>
      <CardRules card={detail} />
      <details className="raw-payload">
        <summary>{t("Données de la source (hors prix)")}</summary>
        <pre>{JSON.stringify(detail.raw, null, 2)}</pre>
      </details>
    </article>
  );
}
