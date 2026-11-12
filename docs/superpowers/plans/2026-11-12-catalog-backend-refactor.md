# Catalogue backend — Implementation Plan

> Document historique de la première tranche catalogue. L’organisation et les
> imports ont ensuite été remplacés par la [refonte globale approuvée](../specs/2026-11-12-project-structure-design.md),
> précisée par l’[ADR 0006](../../adr/0006-separated-applications.md).


> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Clarifier les responsabilités du catalogue sans changer ses réponses HTTP ni ses observations persistées.

**Architecture:** Les cas d’usage restent indépendants de HTTP. Un présentateur HTTP projette les médias ; un lecteur SQL porte les requêtes, tandis que `Repository` garde le moteur et les écritures transactionnelles.

**Tech Stack:** Python, FastAPI/Pydantic, SQLAlchemy, pytest/pytest-bdd ; PostgreSQL et SQLite.

**Spec:** `docs/superpowers/specs/2026-11-12-catalog-backend-refactor-design.md`

## Global Constraints

- Préserver les signatures publiques de `Repository`, ses exports historiques et `engine`.
- Préserver identités localisées, provenance, images, dates, absence de prix et transactions.
- Aucune dépendance, migration, modification frontend, collecte externe ou interruption du worker personnel.
- Aucun commit ni publication. Les fichiers sont actuellement non suivis et le dépôt n’a pas de commit initial : conserver un état de référence temporaire pour la revue.
- Réutiliser le checkout courant ; l’accord « go » autorise l’exécution du périmètre approuvé.

## Review Focus

- Images absentes : listes vides sans URL locale inventée (tâche 1).
- Chemins avec espaces, accents, `#`, `?` ou `%` : URLs encodées qui servent le bon fichier (tâche 1).
- Lecteur réutilisant un résultat : consultation et présentation sans modification des observations (tâche 1).
- Recherche de `%`/`_` et pagination : recherche littérale, ordre stable et frontières source/langue (tâche 2).
- Échec d’insertion d’une impression : aucune extension ni aucun bloc partiellement enregistré (tâche 2).

## Tâche 1 : Présentation HTTP indépendante

**Files:** créer `interfaces/catalog_presenter.py`, `tests/test_catalog_presentation.py` ; modifier `application/catalog.py`, `interfaces/api.py` (sous `src/tcg_catalog/`).

**Interfaces:** `present_card(card: Mapping[str, Any]) -> dict[str, Any]` et `present_page(page: Mapping[str, Any]) -> dict[str, Any]`. Consomment les documents de consultation existants ; produisent les documents validés par les schémas HTTP existants.

- [x] Ajouter les tests HTTP de caractérisation : `image_urls == []` sans média ; sinon deux URLs encodées dans le même ordre, fichiers servis, `source_image_urls` uniquement dans le détail ; identité inconnue → 404.
- [x] Exécuter `uv run pytest tests/test_catalog_presentation.py` : caractérisation verte sur le code initial.
- [x] Ajouter un test de cas d’usage avec un lecteur réutilisant une page et une observation : `result['image_urls']` reste l’URL source et les entrées restent identiques à une copie préalable, pour recherche et détail.
- [x] Exécuter le test : rouge parce que le service transforme actuellement les URLs et modifie la page de recherche.
- [x] Déplacer la projection HTTP dans le présentateur, appelé par les deux routes ; faire retourner les données du lecteur par le service.
- [x] Tester la présentation d’une observation et d’une page en lecture seule : résultat HTTP correct, entrées inchangées.
- [x] Exécuter `uv run pytest tests/test_catalog_presentation.py tests/test_admin_routes.py tests/acceptance tests/test_blocks.py` : tous verts.

## Tâche 2 : Lectures SQL isolées

**Files:** créer `infrastructure/catalog_reader.py`, `tests/test_catalog_queries.py` ; modifier `infrastructure/catalog.py` (sous `src/tcg_catalog/`) et `docs/architecture.md`.

**Interfaces:** `SqlCatalogReader(engine: Engine)` reçoit le moteur existant. Méthodes `contains`, `check_ready`, `search`, `get`, `list_sets`, `list_blocks`, `overview`, `observations` avec signatures et résultats actuels. `Repository` délègue explicitement ces méthodes et possède seul la durée de vie du moteur.

- [x] Ajouter les tests publics de caractérisation avec SQLite temporaire : recherche littérale `100%_`, filtres, pages de taille 1, résultat vide, observation absente ; parcours des observations par lots 1 et 2 ; rollback après rejet SQL d’une impression.
- [x] Exécuter `uv run pytest tests/test_catalog_queries.py tests/test_normalization.py tests/test_catalog_upgrade.py tests/test_blocks.py` : verts avant extraction.
- [x] Déplacer les requêtes et jointures sans modifier les expressions SQL, les règles de fusion ou les écritures. Garder l’identité d’écriture locale à `Repository` et l’ordre de parcours local au lecteur.
- [x] Déléguer explicitement depuis `Repository`, avec les mêmes valeurs par défaut et paramètres nommés.
- [x] Actualiser `docs/architecture.md` pour les responsabilités et le flux HTTP.
- [x] Réexécuter les tests ciblés, puis `make test` : tous verts.
- [x] Exécuter `make docker-build` puis `make docker-test` : pile temporaire PostgreSQL, API, fichiers et worker validés puis nettoyés.
- [x] Faire relire les fichiers modifiés et leur comparaison avec l’état initial par un agent indépendant ; traiter les défauts importants avec reproduction rouge puis correction verte.

## Suivi d’exécution

L’état initial et le journal de travail sont conservés dans un répertoire temporaire
propre à cette exécution. Les cases ci-dessus seront cochées au fur et à mesure.
Les contrôles ne nécessitant pas de serveur local utilisent
`UV_CACHE_DIR=/tmp/tcg-refactor-uv-cache` ; la suite complète et Docker peuvent
nécessiter une autorisation du bac à sable.


## Résultat — 12 novembre 2026

- Deux tests de préservation des observations ont été observés rouges avant le
  déplacement de la présentation, puis verts. Les contrats HTTP et SQL ont été
  caractérisés avant extraction ; aucune modification des expressions SQL.
- `make test` : 49 tests Python et 8 tests frontend réussis ; Ruff, Prettier,
  compilation TypeScript et build réussis.
- `make docker-build` et `make docker-test` : réussis. PostgreSQL, API, images,
  worker, doublons, Chromium et persistance après redémarrage vérifiés dans une
  pile temporaire, supprimée à la fin du contrôle.
- Revue indépendante : aucun défaut critique, important ou mineur. Les neuf
  méthodes SQL déplacées et sept méthodes d’écriture/fermeture ont été comparées
  au code initial sans différence de corps.
- Avertissement préexistant conservé : dépréciation Starlette concernant `httpx`
  dans `TestClient` ; les dépendances ne font pas partie de ce refactoring.

### Décisions d’exécution

- Réutilisation du checkout avec référence temporaire, sans commit : le dépôt ne
  possède pas de révision initiale et ses instructions interdisent les commits.
  Le comparatif de revue est donc conservé hors dépôt ; il ne remplace pas un
  historique Git durable.
- Projections HTTP par copie du premier niveau, sans modification des entrées :
  les routes sérialisent immédiatement le résultat. Une copie profonde n’est pas
  nécessaire à ce contrat ; un futur consommateur modifiant les objets imbriqués
  devrait définir son besoin d’isolation et le tester.
