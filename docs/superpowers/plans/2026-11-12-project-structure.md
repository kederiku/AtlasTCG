# Project Structure Implementation Plan

> Plan réalisé, conservé pour retracer l’exécution et les validations de la refonte.
> Les guides [d’architecture](../../architecture.md), [d’exploitation](../../operations.md)
> et [de contribution](../../../CONTRIBUTING.md) décrivent l’état courant, y compris
> les nettoyages effectués après ce plan.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox syntax for tracking.

**Goal:** Séparer réellement frontend, API et scraping, avec un métier indépendant des frameworks et des contrôles durables.

**Architecture:** Monorepo `apps/{frontend,api,scraping}` et `packages/{core,persistence}`. Workspace uv, installations et images sélectives, base et fichiers partagés par l’API et le worker unique.

**Tech Stack:** Python 3.14, uv, Pydantic, SQLAlchemy/Alembic, FastAPI, Scrapy/Playwright ; React/TypeScript/Vite ; pytest/BDD, Vitest, Ruff, mypy.

**Spec:** `docs/superpowers/specs/2026-11-12-project-structure-design.md`, approuvée le 12 novembre 2026.

## Global Constraints

- Aucun commit, publication, collecte fournisseur ou arrêt de l’installation personnelle.
- Préserver contrats HTTP, identités, prix exclus, fichiers, provenance, dates et historique Alembic.
- Réutiliser le checkout sans commit initial ; référence et journal temporaires hors dépôt.
- Tests de comportement avant les nouvelles frontières, puis déplacement sous tests verts.
- Une revue indépendante finale ; exécution continue déjà autorisée par la validation de conception.

## Review Focus

- API sans frontend compilé : les routes API restent disponibles (tâche 3).
- Répertoire courant extérieur au dépôt : CLI Scrapy et installation non éditable fonctionnent (tâches 2 et 5).
- Journal absent, multioctet ou supérieur à 64 Ko : attente ou suffixe décodé sans erreur (tâche 3).
- Code Scrapy zéro avec erreur/rejet, timeout et interruption : résultat fiable et enfant terminé (tâche 2).
- Données préexistantes et références images : déplacement de migrations sans réécriture ni perte (tâches 1 et 5).

## Tâche 1 — Workspace et bibliothèques partagées

**Files:** `pyproject.toml`, `uv.lock`, `packages/core/pyproject.toml`, `packages/persistence/pyproject.toml`, `apps/{api,scraping}/pyproject.toml`, tous les imports Python, `alembic.ini`.

**Interfaces:** `tcg_core.catalog.{models,retention,media,queries,reindex}`, `tcg_core.collections.{models,service}`, `tcg_persistence.{catalog,catalog_reader,schema,jobs,configuration,migrate_images}`, `tcg_api.app:create_app`, `tcg_scraping.{settings,runner,worker}`.

- [x] Ajouter un test d’import du nommage avec Scrapy interdit : `image_path` produit le chemin existant. Observer l’échec dû à l’import Scrapy.
- [x] Séparer nommage pur et empreinte Scrapy ; vérifier les tests image existants.
- [x] Déplacer les modules vers quatre distributions et mettre à jour tous les imports et chemins configurés, sans anciens modules de compatibilité.
- [x] Déplacer les migrations sans changer leurs versions ; adapter seulement env/config.
- [x] Configurer uv workspace et l’installation de développement de tous les membres ; verrouiller les dépendances.
- [x] Ajouter le contrôle des imports et déclarations de dépendance autorisés, avec vérification d’un exemple interdit.
- [x] Exécuter `uv run --all-packages pytest` et Ruff. Les comportements existants restent verts.

## Tâche 2 — Collectes indépendantes de Scrapy

**Files:** `packages/core/src/tcg_core/collections/{models,ports,submission,queries,execution}.py`, `apps/scraping/src/tcg_scraping/{runner,worker}.py`, `apps/scraping/src/tcg_scraping/{cli,pipelines,extensions,sources}/`, tests associés.

**Interfaces:** `CollectionResult(status, stats, error=None)` ; `Collector.run(identifier, request) -> CollectionResult` ; `RequestCollection.request(request)`, `ExecuteCollection.execute_next(collector)`, `CollectionQueries.list/get/logs`, ports `JobQueue`, `JobReader`, `JobLogReader`.

- [x] Tester l’exécution métier avec un collecteur fournissant un résultat typé et des diagnostics opaques ; observer rouge avant extraction.
- [x] Séparer soumission, lectures et exécution ; déplacer l’interprétation des clés Scrapy dans le runner.
- [x] Tester succès, rejet, sortie zéro en erreur et timeout sur les frontières de processus ; préserver les résultats partiels et la reprise.
- [x] Extraire les pipelines par responsabilité ; garder normalisation pure et spider voisins, avec imports indépendants.
- [x] Ajouter `tcg-scrape`, `tcg-worker`, `tcg-reindex`, `tcg-migrate-images`, sans dépendance à la découverte du répertoire courant.
- [x] Exécuter tests core, scraping et BDD collections.

## Tâche 3 — API composée par responsabilité

**Files:** `apps/api/src/tcg_api/{app,security,static,logs}.py`, `routes/{catalog,collections,health}.py`, `schemas/{catalog,collections}.py`, `presentation/catalog.py`, `apps/api/tests/`.

**Interfaces:** fabrique publique `create_app(database_url=None, images_dir=None, jobs_dir=None, *, frontend_dir=None)` conservée ; routes construites à partir de cas d’usage injectés ; `FileJobLogs.read(identifier) -> str`.

- [x] Caractériser les journaux absent/long/multioctet, les réponses de collecte, les protections et le démarrage sans frontend.
- [x] Extraire routes, schémas, fichiers et sécurité ; faire passer les lectures de jobs par les cas d’usage.
- [x] Garder la construction/fermeture des ressources dans la fabrique ; configurer explicitement le build frontend.
- [x] Exécuter les tests API et BDD, dont médias encodés, 404 et mutations refusées.

## Tâche 4 — Frontend par fonctionnalité

**Files:** `apps/frontend/`, `src/app/`, `src/features/{catalog,collections}/`, `src/shared/http/` ; configuration alias et tests colocalisés.

**Interfaces:** `shared/http/client.ts` expose `api<T>` et `ApiError` ; chaque fonctionnalité expose types, requêtes et composants ; `app/App.tsx` compose routage et shell.

- [x] Conserver les tests de parcours existants et caractériser ouverture/soumission de collecte et affichage des journaux avant extraction.
- [x] Déplacer le frontend ; répartir transport/types, médias/journaux et formulaire ; extraire l’orchestration de collecte de `App`.
- [x] Regrouper filtres/navigation du catalogue dans sa fonctionnalité sans changer les URLs.
- [x] Exécuter Prettier, Vitest et build TypeScript/Vite ; vérifier le parcours navigateur sur une installation de test.

## Tâche 5 — Installations et images isolées

**Files:** `Dockerfile`, `compose.yaml`, `scripts/{docker_smoke,check_installations}.py`, `Makefile`, `.github/workflows/ci.yml`, `.dockerignore`, `.gitignore`.

**Interfaces:** images `tcg-api:local`, `tcg-scraping:local`, `tcg-migrate:local` ; services Compose existants conservés ; commandes Make existantes plus `api`, `typecheck`, `test-installations`.

- [x] Vérifier en environnements temporaires réellement séparés l’absence des frameworks interdits et les comportements API, core, persistence, scraping.
- [x] Construire les cibles Docker sélectives ; Chromium uniquement dans scraping ; frontend compilé uniquement dans API.
- [x] Adapter test de pile : toutes les images construites, migration, collecte locale, statut, images, redémarrage et isolation des dépendances.
- [x] Adapter commandes et CI ; introduire mypy sur core et les ports avec annotations effectives.
- [x] Exécuter `make test`, `make test-installations`, `make docker-build && make docker-test`.

## Tâche 6 — Documentation et revue finale

**Files:** README, CONTRIBUTING, CONTEXT, `docs/{architecture,engineering,operations,catalog-model,acceptance}.md`, ADR 0006 et index.

- [x] Décrire arbre, responsabilités, règles de dépendance, commandes et parcours d’entrée pour nouveau contributeur.
- [x] Documenter les imports/CLI remplacés et l’ADR qui précise 0001 et remplace l’image commune de 0004 ; conserver l’historique.
- [x] Comparer les migrations au snapshot initial et rechercher les anciens imports/chemins dans les documents actifs.
- [x] Faire relire indépendamment implémentation, plan et conception avec référence initiale et résultats des tests.
- [x] Corriger les défauts importants par reproduction rouge/verte, puis repasser les contrôles affectés ; rapporter les limites réelles.

## Suivi

Le chemin de la référence temporaire et du journal est conservé dans
`/tmp/tcg-structure-session-path`. Le journal consigne les décisions et preuves
de chaque tranche, sans commit ni modification des données personnelles.


## Résultat — 12 novembre 2026

- Arbre frontend/API/scraping et core/persistence en place ; anciens imports
  `tcg_catalog.*` supprimés du code et des commandes actives.
- Nouveaux contrats observés rouges puis verts : nommage sans Scrapy, résultat
  métier indépendant des diagnostics techniques, schéma OpenAPI des collectes,
  lanceur Scrapy hors répertoire de sources. Comportements existants caractérisés
  avant extraction. Le contrôle d’architecture rejette un import Scrapy injecté
  temporairement dans core ; ce fichier de vérification a été retiré.
- `make test` réussi : **66 tests Python, 9 tests frontend**, Ruff, mypy strict sur
  les 14 modules de core, Prettier, TypeScript et build Vite.
- `make test-installations` réussi : **4 tests core, 10 persistence, 10 API,
  21 scraping**, chacun dans son installation non éditable séparée avec absence
  des frameworks interdits. Ces tests sont un sous-ensemble de la suite complète.
- `make docker-build && make docker-test` réussi : trois images, migrations
  PostgreSQL, indépendance des dépendances, API, worker, fichiers, Chromium,
  doublons et persistance après redémarrage. Projet temporaire nettoyé.
- Les cinq fichiers de versions Alembic sont identiques octet pour octet à la
  référence initiale. Le schéma et les données personnelles ne sont pas modifiés.
- Parcours navigateur sur une base temporaire : catalogue, filtres par bloc,
  fiche, rechargement direct, formulaire, soumission, historique et journal sans
  worker. Rendu inspecté ; serveurs temporaires arrêtés ensuite.
- Revue indépendante : aucun défaut introduit nécessitant correction. Le reviewer
  a comparé les extractions au snapshot et relancé 25 tests ciblés avec succès.

### Décisions d’exécution et limites

- Checkout actuel conservé avec référence temporaire, car aucun commit initial
  n’existe et les commits ne sont pas autorisés. La copie temporaire aide la revue,
  mais ne remplace pas un historique Git durable.
- Exécution inline après validation de la conception, avec une revue indépendante
  finale. Les détails d’installation et de découpage ont été réglés dans le cadre
  approuvé, sans nouvelle demande de confirmation.
- SQLite restitue les dates sans fuseau : comportement préexistant conservé ; les
  tests comparent l’instant. La sérialisation HTTP existante reste explicite.
- Le contrôle de types strict porte sur core et ses ports ; les adaptateurs
  dynamiques ne sont pas annoncés comme intégralement couverts par mypy.
- Avertissement préexistant TestClient/httpx conservé. Il ne fait échouer aucun test.
- Aucun commit ni publication. Aucune collecte externe ni intervention sur les
  services personnels. Aucun défaut mineur différé par la revue.

### Points de revue clôturés

API sans build : disponibilité des routes et racine 404 conformes. Journaux absents,
longs et multioctets : attente ou suffixe borné corrects. CLI hors dépôt : découverte
explicite validée. Code Scrapy zéro avec erreur/rejet : échec conservant les stats.
Timeout/interruption : enfant terminé. Reprise : file conservée. Migrations et
maintenance : observations et originaux préservés. Aucun de ces points n’a été
écarté sans vérification.
