# ADR 0006 — Applications et dépendances séparées

Statut : accepté le 12 novembre 2026. Précise l’organisation de l’ADR 0001 et
remplace son maintien des imports internes de compatibilité. Remplace le choix
d’image applicative commune de l’ADR 0004 ; ses garanties opérationnelles restent.

## Problème

L’API et le worker étaient deux processus, mais partageaient un paquet Python et
une image contenant HTTP, Scrapy et Chromium. Leur emplacement ne permettait pas
à un contributeur d’identifier rapidement le propriétaire d’un comportement. Le
métier interprétait les statistiques de Scrapy et le nommage des images importait
le framework de collecte jusque dans la maintenance.

## Décision

Conserver un monorepo, avec `apps/frontend`, `apps/api`, `apps/scraping` et deux
bibliothèques `packages/core`, `packages/persistence`. Chaque paquet Python a ses
propres dépendances et partage le verrou du workspace uv. Core porte les modèles,
invariants, ports et cas d’usage ; persistence réalise SQL et la configuration.
Les applications dépendent des bibliothèques et ne s’importent pas mutuellement.

API possède routes, schémas, sécurité et service des fichiers. Scraping possède
worker, processus, acquisition, normalisations et pipelines. Les normalisations
restent pures ; le registre commun de capacités ne charge pas de spider. Le runner
traduit les résultats techniques avant de les remettre au cas d’usage d’exécution.
Le nommage pur des images appartient à core.

Le frontend distingue composition, fonctionnalités catalogue/collectes et transport
HTTP commun. Son build reste servi par l’API sur la même origine. Aucun serveur
supplémentaire n’est ajouté à l’installation locale.

Trois images non éditables sont construites : API, scraping et migration. Chromium
appartient uniquement au scraping. PostgreSQL et les fichiers restent partagés,
avec un worker unique. Les noms Compose, volumes, variables et contrats HTTP sont
conservés. Les cinq versions Alembic sont déplacées sans modification de contenu.

Les anciens imports `tcg_catalog.*` sont remplacés dans le dépôt. Les commandes
publiques sont Make et les CLI `tcg-scrape`, `tcg-worker`, `tcg-reindex`,
`tcg-migrate-images`. `make admin` reste un alias de `make api`.

## Conséquences et limites

- Les responsabilités et dépendances sont visibles dans l’arbre et le packaging.
- Installer le workspace complet facilite le développement ; cela ne démontre pas
  l’indépendance des installations. Des contrôles dédiés sont obligatoires.
- Les images sont plus ciblées, mais il faut toutes les reconstruire lors d’une mise
  à jour coordonnée. Les procédures de fin de collecte et sauvegarde restent valables.
- Le stockage partagé reste un choix d’installation locale ; il ne constitue pas
  une architecture distribuée ni un contrat de versions indépendantes du schéma.
- Le typage strict couvre core et ses ports. Les adaptateurs de frameworks restent
  vérifiés par leurs contrats et tests ; le dépôt ne prétend pas typer strictement
  toutes les API dynamiques de Scrapy/SQLAlchemy.

## Validation

Tests de comportement métier, HTTP, collecte locale, frontend et migrations sur
données existantes. Ruff, mypy strict sur core, Prettier, TypeScript et build.
Contrôles des imports et tests en quatre environnements installés séparément, avec
absence des frameworks interdits. Test Compose/PostgreSQL temporaire avec les trois
images, contrôle de leurs dépendances, worker, médias, Chromium et persistance.
