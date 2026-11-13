# Collectes TCGdex par périmètre — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Choisir un bloc ou une extension et collecter toutes ses cartes dans les langues demandées.

**Architecture:** Une nouvelle variante de demande conserve les contrats historiques.
Un cas d’usage de découverte agrège des choix localisés fournis par un adaptateur
HTTP de l’API. Le spider existant découvre uniquement le périmètre demandé ; React
présente les deux listes liées.

**Tech Stack:** Python/Pydantic, FastAPI, urllib standard, Scrapy, React/React Query, TypeScript.

**Spec:** [Conception approuvée](../specs/2026-11-13-scoped-tcgdex-collections-design.md).

## Global Constraints

- Une demande cible un seul bloc ou une seule extension.
- Aucun prix, aucune fusion des identités localisées, aucune migration nécessaire.
- L’API et le scraping ne s’importent pas mutuellement.
- Conserver les demandes historiques et `ImageRepairRequest`.
- Sans limite implicite de dix cartes pour un périmètre ; timeout existant d’une heure.
- Pas de collecte réelle, commit, publication ou redémarrage de la pile personnelle.
- Préserver les modifications préexistantes de réparation des images.

## Review Focus

- Un code avec point (`swsh12.5`) reste valide, les chemins et options shell sont refusés (tâche 1).
- Les langues utilisées seulement pour traduire les noms n’ajoutent pas des choix inadmissibles (tâche 2).
- Une erreur réseau ne devient pas une liste vide ou partielle (tâche 2).
- L’enrichissement d’une extension ne collecte pas les autres extensions du bloc (tâche 1).
- Un changement rapide de langue/bloc ne soumet pas une sélection périmée (tâche 3).

## Task 1: Demande ciblée et exécution sans élargissement

**Files:**
- Modifier `packages/core/src/tcg_core/collections/models.py`.
- Modifier `apps/scraping/src/tcg_scraping/runner.py` et `sources/tcgdex/spider.py`.
- Tester `tests/acceptance/features/collection.feature`, `tests/acceptance/test_collection_admin.py`,
  `apps/scraping/tests/test_scoped_collection.py`, `apps/scraping/tests/test_runner.py`.

**Interfaces:**
- Produire `CollectionScope(kind: Literal['block', 'set'], id: str)` et
  `ScopedCollectionRequest(kind='collect_scope', spider='tcgdex', languages, scope, force)`.
- `JobRequest` conserve les trois variantes ; `job_request_adapter` les valide.
- Le spider reçoit `block_id` ou `set_id`, `languages`, `force`. `limit=None` dans
  son constructeur distingue l’omission d’une limite explicite incompatible.

- [x] Écrire l’acceptation d’un POST `collect_scope` (202 et paramètres persistés),
  des champs contradictoires (422), des codes à point et des anciennes variantes.
- [x] Exécuter ces tests ; observer 422 au lieu de 202 pour la nouvelle demande.
- [x] Ajouter les modèles stricts en partageant seulement les langues/force communs.
- [x] Vérifier l’acceptation et les tests core/API existants.
- [x] Écrire un parcours spider réel sur HTTP local : bloc contenant 12 cartes dans
  deux sets, extension seule et autre set interdit, FR absent/EN présent, tous
  absents, source malformée, set annoncé absent, métadonnées indépendantes.
- [x] Exécuter le premier scénario et observer la découverte générale au lieu du périmètre.
- [x] Ajouter les branches de découverte, validation des réponses, gestion des
  absences racines et compteurs `scope/languages_found`, `scope/languages_unavailable`.
  Chaque callback distingue explicitement expansion et enrichissement.
- [x] Traduire la demande dans le runner, avec arguments sans shell et sans limite.
- [x] Vérifier la suite scraping et l’acceptation (fixtures HTTP, jamais TCGdex).

## Task 2: Préparation des choix distants

**Files:**
- Créer `packages/core/src/tcg_core/collections/discovery.py`.
- Créer `apps/api/src/tcg_api/discovery.py`, `routes/collection_options.py`.
- Modifier `apps/api/src/tcg_api/app.py`.
- Tester `packages/core/tests/test_collection_discovery.py`,
  `apps/api/tests/test_collection_options.py`.

**Interfaces:**
- `LocalizedChoice(id: str, name: str, language: str)` et
  `CollectionChoice(id: str, name: str, languages: list[str])`.
- Port `CollectionDiscovery.choices(kind: Literal['block','set'], languages: list[str],
  block_id: str | None) -> list[LocalizedChoice]` ; exception `DiscoveryUnavailable`.
- `CollectionOptions(discovery).list(kind, languages, locale, block_id=None)` valide,
  choisit les langues de libellés et regroupe en `list[CollectionChoice]`.
- `TCGdexDiscovery` réalise ce port par urllib : HTTPS fixé, concurrence globale
  de quatre lectures, délai socket 5 s, réponses de 2 Mio max, aucun redirect vers
  un autre hôte. Le contexte de l’API possède et ferme son exécuteur.
- `create_app(..., discovery: CollectionDiscovery | None = None)` permet de composer
  les tests sans source réelle ; l’adaptateur par défaut ne contacte rien au démarrage.
- Deux routes `/api/collection-options/tcgdex/blocks` et `/sets`, paramètres de la spec.

- [x] Écrire les exemples de regroupement/noms/admissibilité à la frontière du
  cas d’usage, ainsi que validation d’une langue ou d’un bloc invalide.
- [x] Observer l’échec de fonctionnalité, puis implémenter modèles, port et cas d’usage.
- [x] Écrire les tests API via serveur HTTP local : blocs, sets tous/filtrés,
  404 absent, 500/JSON invalide/incohérence/temps dépassé/taille excessive = 503,
  paramètres invalides = 422, réponses strictes et sans données brutes.
- [x] Observer l’échec, ajouter l’adaptateur et les routes, puis vérifier core/API
  et les installations isolées pour confirmer l’absence de dépendance scraping.

## Task 3: Formulaire, historique et livraison

**Files:**
- Modifier `apps/frontend/src/features/collections/{types,api,CollectForm,CollectionsPanel,JobLogs}.tsx/ts`
  selon leurs extensions existantes et `shared/i18n/messages.ts`, styles si nécessaire.
- Tester `CollectForm.test.tsx`, les scénarios de langues et `ImageRepair.test.tsx`.
- Mettre à jour CONTEXT, docs/acceptance, docs/api, docs/architecture, docs/operations,
  ajouter ADR 0009 et son index.

**Interfaces:**
- Types TypeScript pour les trois variantes ; gardes `isImageRepair` et `isScopedCollection`.
- `getCollectionOptions(kind, languages, locale, blockId?)` consomme les routes tâche 2.
- Le formulaire soumet la variante tâche 1 ; l’historique expose son code et type.

- [x] Écrire le test du choix bloc/extension qui soumet une demande sans `limit`,
  et observer l’absence des sélecteurs.
- [x] Implémenter les listes via React Query avec clés complètes, cache 5 minutes,
  état courant validé contre les résultats, et bloc par défaut « Tous les blocs ».
- [x] Ajouter avant leur comportement les tests avancé/cartes, disponibilité,
  chargement/erreur/retry, zéro langue, changement de bloc/langues, réponses tardives.
- [x] Implémenter ces états, traductions FR/EN/ES et l’historique compatible.
- [x] Vérifier tous les tests frontend ; mettre à jour la documentation et ADR.
- [x] Exécuter `make test`, `make test-installations`, un parcours navigateur isolé.
  Docker build/test si les dépendances ou le packaging changent.
- [x] Faire relire l’ensemble par un nouveau reviewer ; traiter les défauts
  matériels par test rouge/vert, puis relancer les contrôles nécessaires.
- [x] Livrer les changements, résultats et limites sans commit ou déploiement.

## Progression et décisions

- Conception approuvée : « cela me va » le 13 novembre 2026.
- Ruling: exécution native dans le checkout courant, sans commit — continuité avec
  le travail présent et préférence de l’environnement pour réutiliser le checkout.
  L’autorisation d’implémenter est acquise ; pas de nouvelle validation du plan.
- Ruling: suivi dans ce document et journaux `/tmp/tcg-scoped-*` — aucun besoin de
  modifier `.git` ou de multiplier les répertoires de travail.
- Pre-flight: tâche 1 → tâche 3 (`ScopedCollectionRequest`) et tâche 2 → tâche 3
  (`CollectionChoice`, routes) : mêmes champs/discriminants dans tous les contrats.
- Base : fonctionnalités précédentes vérifiées (119 tests Python, 31 frontend) ;
  aucun changement de produit effectué depuis, seulement la conception approuvée.
- Task 1: complete — rouge API (422 au lieu de 202), rouge spider (0 au lieu de
  11/12 cartes), rouge erreurs (9 scénarios), puis suite scraping + acceptation :
  73 tests réussis (`/tmp/tcg-scoped-task1.log`).
- Ruling: le regroupement des choix core est exercé via la frontière API et un
  vrai serveur source local ; pas de duplication de ces assertions dans des tests
  unitaires core. Les erreurs de transport sont testées sur cette même frontière.
- Task 2: complete — rouge sur routes absentes, puis core/API/architecture :
  36 tests réussis (`/tmp/tcg-scoped-task2.log`). Mypy strict : 17 fichiers valides.
- Task 3: interface et historique verts — 35 tests frontend. Rouge supplémentaire
  sur une extension devenue indisponible : le passage silencieux au bloc entier
  est empêché par une sélection explicitement invalidée.
- Ruling: `CollectionScopePicker.tsx` sépare la préparation du périmètre du
  formulaire, et `CollectionTarget.tsx` partage l’affichage historique/journal.
- Navigateur : formulaire, bloc entier, extension précise, langue indisponible,
  demande persistée et journal vérifiés sur SQLite temporaire sans worker.
  Capture : `/tmp/tcg-scoped-form.jpg`. Instance de test arrêtée ensuite.
- Relecture indépendante : deux défauts importants reproduits. Une carte existante
  déclenchait l’errback et un faux échec ; les métadonnées pouvaient être comptées
  comme cartes ajoutées. Correction par exception explicite `CardAlreadyStored`
  (sous-classe compatible d’`IgnoreRequest`) et absence de repli sur le nombre
  d’items pour les demandes ciblées. Tests rouges de relance complète/partielle
  et d’historique à zéro, puis verts. Aucun défaut mineur différé.
- Ruling: aucun packaging, dépendance runtime, stockage ni Docker modifié pour
  cette fonctionnalité ; validations `make test` et `make test-installations`,
  sans nouvelle construction Docker. La fonctionnalité de réparation précédente
  conserve sa validation Docker déjà effectuée.

- Task 3: complete — `make test` final : Ruff, formatage, mypy strict, 153 tests
  Python/BDD, 36 tests frontend et build réussis. `make test-installations` final :
  core 9, persistence 17, API 22, scraping 60 tests réussis. Journaux :
  `/tmp/tcg-scoped-final-test.log`, `/tmp/tcg-scoped-final-installations.log`.
- Nettoyage : style et traduction de l'ancien champ facultatif devenus inutiles
  retirés ; formatage vérifié et suite frontend/build exécutés après ce retrait.
- Ruling: conservation des modifications non commitées dans le checkout courant,
  conformément à AGENTS.md ; aucune intégration Git ni mise à jour de la pile
  personnelle n'a été demandée. Les nouveaux services doivent être reconstruits
  et recréés pour rendre cette version visible dans la pile Docker existante.
