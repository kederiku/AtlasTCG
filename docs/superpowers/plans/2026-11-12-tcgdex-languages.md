# Plan d’implémentation — Langues TCGdex

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Proposer les 18 langues TCGdex, avec `fr` et `en` seuls sélectionnés par défaut.

**Architecture:** Le registre core reste l’autorité des capacités exposées par
`GET /api/spiders`. Le formulaire React charge ce contrat via React Query.

**Tech Stack:** Python/Pydantic/FastAPI, pytest-bdd, React/TypeScript, Vitest.

**Spec:** [Conception](../specs/2026-11-12-tcgdex-languages-design.md).

## Contraintes globales

- Liste exacte : `en,fr,es,es-mx,it,pt,pt-br,pt-pt,de,nl,pl,ru,ja,ko,zh-tw,id,th,zh-cn`.
- Pas de fusion des variantes, de migration, de dépendance ou de collecte réelle.
- Préserver le checkout existant et les fichiers non suivis. Aucun commit demandé.
- Exécuter dans cette session ; tests externes simulés à la frontière HTTP.

## Points de revue

- Code inconnu : refus API, aucune demande enregistrée (tâche 1).
- Sélection vide : soumission désactivée (tâche 2).
- Chargement ou panne du registre : soumission désactivée, nouvelle tentative (tâche 2).
- Connecteur absent : indisponibilité visible (tâche 2).
- Codes régionaux : routes/identités inchangées (tâche 1).

## Tâche 1 : accepter toutes les langues

**Fichiers :** `packages/core/src/tcg_core/collections/{connectors,models}.py`,
`tests/acceptance/features/collection.feature`,
`tests/acceptance/test_collection_admin.py`, `apps/scraping/tests/test_spider.py`.

**Interface :** `GET /api/spiders` garde son schéma `languages: list[str]` ;
`POST /api/jobs` accepte une demande avec les 18 codes.

- [x] Ajouter un scénario BDD vérifiant les 18 capacités puis leur soumission
  et leur conservation dans l’historique ; attendre HTTP 202 et les codes exacts.
- [x] Observer le refus attendu avant correction avec
  `uv run --locked pytest tests/acceptance/test_collection_admin.py`.
- [x] Compléter `CONNECTORS[0]["languages"]` et dériver la borne de validation
  de la longueur du registre pour ne pas conserver une limite divergente.
- [x] Vérifier le refus d’une langue inconnue et caractériser les requêtes du
  spider pour `es-mx`, `pt`, `pt-br`, `pt-pt`, `zh-tw`, `zh-cn` sans réseau.
- [x] Exécuter les suites d’acceptation collecte et spider ; résultat attendu vert.

## Tâche 2 : synchroniser le formulaire

**Fichiers :** `apps/frontend/src/features/collections/types.ts`, `api.ts`,
`CollectForm.tsx`, `CollectForm.test.tsx`, `CollectionDialogs.tsx` dans le même
dossier, et `apps/frontend/src/app/App.test.tsx`.

**Interfaces :** ajouter `Connector` (`id`, `name`, `game`, `languages`) et
`getConnectors(): Promise<Connector[]>` vers `/spiders`. Le contrat de props de
`CollectForm` ne change pas ; le composant utilise le QueryClient existant.

- [x] Ajouter un test HTTP simulé des 18 choix, des deux défauts et de la
  soumission intégrale ; observer l’absence des choix avant correction.
- [x] Charger les capacités dans `CollectForm`, afficher les libellés français
  avec les codes régionaux conservés ; ne pas coder une seconde liste de capacités.
- [x] Ajouter puis faire passer les tests chargement, erreur/réessai, connecteur
  absent et sélection vide. Adapter le test de navigation à `/api/spiders`.
- [x] Exécuter `npm test --prefix apps/frontend -- CollectForm App` ; attendu vert.

## Tâche 3 : documentation et livraison

**Fichiers :** `docs/api.md`, `docs/acceptance.md`, `CONTRIBUTING.md`.

- [x] Documenter les 18 codes et le formulaire construit depuis le registre.
- [x] Exécuter `make test` avec un cache uv accessible ; résultat attendu vert.
- [x] Vérifier le formulaire et une soumission dans le navigateur avec une base
  temporaire, sans worker ni accès à la base personnelle.
- [x] Faire relire les changements par un agent de revue conformément au workflow
  d’exécution, corriger les défauts importants et consigner les résultats.

## Journal

- Portée et approche validées par l’utilisateur ; exécution dans le checkout
  partagé, sans création de commit ni worktree.
- Pré-vérification : tests React existants verts (3). Le cache uv habituel est
  hors sandbox ; les commandes Python utilisent `/private/tmp/tcg-uv-cache`.

- Tâche 1 terminée : échecs observés sur les capacités manquantes, puis HTTP 422
  avec 18 codes ; correction du registre et de la borne, 13 tests ciblés verts.
- Tâche 2 terminée : échec observé (6 choix au lieu de 18), puis chargement,
  erreur/réessai et connecteur absent couverts ; 9 tests ciblés verts.
- Ajustement constaté dans le navigateur : les 18 choix dépassaient la hauteur
  disponible. La fenêtre de collecte est maintenant bornée à la hauteur de
  l’écran et défilable ; titre, fermeture et soumission restent accessibles.
- Vérification finale : `UV_CACHE_DIR=/private/tmp/tcg-uv-cache make test` réussit
  (Ruff, mypy, 68 tests Python/BDD, 15 tests frontend, Prettier, build). Le test
  HTTP local a nécessité une exécution autorisée hors sandbox. Un avertissement
  de dépréciation Starlette/httpx préexistant reste présent, sans échec.
- Parcours navigateur : 18 choix visibles, seuls français/anglais cochés au
  départ, soumission des 18 langues avec limite 1, historique en attente avec
  tous les codes. Base SQLite temporaire et aucun worker ; serveur arrêté et
  répertoire temporaire nettoyé après vérification.
- Revue indépendante : aucun défaut critique ou important. Aucun changement
  de packaging, dépendance, stockage ou Docker ; tests d’installation/Docker
  non requis pour ce périmètre. Aucune collecte réelle ni redéploiement.
