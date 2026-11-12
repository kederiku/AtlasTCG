# Navigation multilingue — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Naviguer par carte, bloc et extension indépendamment de leurs traductions, avec une interface FR/EN/ES.

**Architecture:** Conserver les observations localisées ; ajouter une projection de lecture groupée paginée. Le domaine sélectionne l’impression représentative, SQL recherche les traductions, l’API présente les médias. Un contexte React fournit la langue de l’interface et les traductions typées.

**Tech Stack:** Python/Pydantic/SQLAlchemy/FastAPI, React/TypeScript/Intl, pytest/BDD/Vitest.

**Spec:** [Conception approuvée](../specs/2026-11-12-navigation-multilingue-design.md).

## Global Constraints

- Interface français, anglais, espagnol ; préférence locale, français par défaut.
- Identités, observations, images, dates et langues de collecte préservées ; aucun prix.
- Repli des noms : langue d’interface, français, anglais, code de langue trié, identifiant.
- Pagination par groupes ; anciens contrats d’impressions conservés.
- Aucun commit, migration ou redémarrage de la pile personnelle.

## Review Focus

- Langue absente et préférence navigateur invalide : repli stable sans changer les filtres.
- Même identifiant dans plusieurs sources/jeux : aucune fusion.
- Métadonnées différentes entre traductions : respecter les filtres et préserver chaque version.
- Groupe à cheval sur une page : une seule occurrence, total exact, toutes ses langues accessibles.
- Accès direct/rechargement/retour fiche : langue d’interface persistée et URL localisée conservée.

## Task 1: Projection groupée et recherche multilingue

Files: `packages/core/src/tcg_core/catalog/queries.py`, nouveau `navigation.py`,
`packages/persistence/src/tcg_persistence/catalog_reader.py`, `catalog.py`,
`apps/api/src/tcg_api/{routes,schemas,presentation}/catalog.py`,
nouveaux tests `tests/acceptance/features/navigation.feature`, `test_navigation.py`,
`packages/persistence/tests/test_catalog_navigation.py`.

Interfaces: `CatalogService.browse(display_language: str = "fr", **filters)` ;
`CatalogReader.browse(**filters)` renvoie une page de groupes avec versions et
langues correspondant aux filtres. `GET /api/card-groups` renvoie des résumés
avec `versions: CardSummary[]`, mêmes filtres que `/api/cards`, plus
`display_language`. Le détail ajoute `versions` sans changer son identité.

- [x] Écrire et observer l’échec HTTP 404 d’un scénario FR/ES : un groupe, deux versions, nom représentatif selon interface.
- [x] Ajouter contrat de lecture, requête groupée avant pagination, recherche des noms de carte/bloc/set dans toutes leurs traductions, projection HTTP explicite.
- [x] Tester filtres cumulatifs, absence de langue, caractères littéraux, collisions de jeu/source, pagination et conservation des détails.
- [x] Exécuter pytest du périmètre et mypy core ; attendu : vert.

## Task 2: Langue d’interface persistante

Files: nouveau `apps/frontend/src/shared/i18n/`, `src/app/App.tsx`, `WorkspaceLayout.tsx`, `src/shared/format.ts`.
Interfaces: `I18nProvider`, `useI18n() -> {locale, setLocale, t, languageName}` ;
`t(key, parameters?)` utilise un dictionnaire FR/EN/ES à clés identiques.

- [x] Test React : sélecteur global, changement FR/EN/ES, localStorage, document.lang, préférence inconnue et stockage indisponible ; observer rouge.
- [x] Implémenter contexte/dictionnaires et sélecteur, dates/nombres localisés.
- [x] Exécuter Vitest ciblé et build ; attendu : vert.

## Task 3: Parcours catalogue regroupé

Files: `features/catalog/{types,api,facets,useCatalogFilters,CatalogPanel,CardDetailPage,CardImage}.tsx/ts`, tests voisins, `index.css`.
Interfaces: consommation `/api/card-groups`, versions sous chaque carte et dans le détail ; noms de navigation issus de `overview` et de la langue d’interface.

- [x] Tests rouges : FR reste stable avec cartes ES ; changement de langue des cartes conserve extension ; une tuile avec deux liens de langues ; retour et filtre URL.
- [x] Adapter requête, rendu et liens accessibles sans liens imbriqués ; garder les filtres parents cohérents, repli stable et ordre de navigation conservé.
- [x] Tester les traductions absentes, variantes régionales et aperçu sans overview chargé ; Vitest ciblé attendu vert.

## Task 4: Traduction complète des parcours

Files: `features/catalog/CardRules.tsx`, tous les composants `features/collections/`, `components/ui/dialog.tsx`, `shared/http/client.ts`, dictionnaires et tests App.

- [x] Tests rouges EN/ES : soumettre une collecte, consulter historique/journal, consulter fiche et messages d’erreur.
- [x] Traduire les textes applicatifs et libellés accessibles, conserver valeurs et journaux source ; retirer helpers devenus inutiles.
- [x] Exécuter toute la suite frontend ; attendu : vert.

## Task 5: Documentation, revue et vérification finale

- [x] Actualiser `CONTEXT.md`, `docs/catalog-model.md`, `docs/api.md`, `docs/acceptance.md`, ADR 0007 et index ; conserver l’historique des ADR.
- [x] Revue indépendante du diff contre la copie initiale, corriger les défauts avec régression observée.
- [x] Vérifier parcours navigateur FR/EN/ES sur données temporaires (desktop/mobile, détail, filtre, préférence persistée).
- [x] Exécuter `make test`, `make test-installations`, `make docker-build`, `make docker-test` ; lire les sorties et rapporter les limites.

## Journal d’exécution

- Initial : `make test` vert, 68 tests Python et 15 frontend ; build vert.
- Ruling : exécuter dans le checkout fourni, sans opération Git — tous les fichiers sont non suivis, et les consignes demandent de préserver le travail sans commit ; copie initiale à `/var/folders/9m/hqwvjl4j7glfk7qk_0b583sr0000gn/T/tcg-navigation-baseline-_2xqqr0p`.
- Ruling : procéder directement au plan et à son exécution — l’utilisateur a explicitement validé et demandé l’implémentation ; aucune nouvelle approbation du mode d’exécution nécessaire.
- Pre-flight : Task 1 fournit les versions et groupes à Task 3 ; Task 2 fournit contexte/traductions à Tasks 3/4 ; contrats compatibles avec les routes localisées conservées.

- Tasks 1–4 : comportement implémenté ; BDD 2/2, tests SQL 6/6, frontend 21/21 et build verts. Cas rouges observés : API 404, sélecteur absent, noms couplés à la langue des cartes, boutons de collecte non traduits.

- Revue indépendante : deux défauts relevés, aucun comportement écarté. Repli sans facettes corrigé avec les noms des versions déjà chargées ; dates civiles et compteurs désormais formatés selon la langue. Régressions observées rouges puis vertes.
- Ruling : le formatage, signalé mineur par la revue, est corrigé car explicitement inclus dans la conception ; aucune remarque différée.
- Vérification navigateur : FR/EN/ES, recherche espagnole avec repères français, changement d’impression et retour, préférence au rechargement, 27 groupes pour 81 impressions, page 2 avec 3 cartes, formulaire et journal sur base temporaire. Largeurs mobile/ordinateur contrôlées ; débordement du menu espagnol corrigé (375 px de contenu pour 375 px disponibles). Aucune erreur console.
- Installations : une roue locale ancienne a d’abord provoqué un échec ; le script reconstruit désormais explicitement les paquets locaux sans changer les versions verrouillées. Les quatre installations isolées passent.
- Validation finale : `make test` → Ruff/formatage/mypy verts, 76 tests Python et 22 frontend verts, build vert ; `make test-installations` → quatre installations vérifiées ; `make docker-build` et `make docker-test` → succès, recherche traduite et pagination groupée vérifiées sur PostgreSQL. Projet temporaire nettoyé.
- Livraison : sources et images locales prêtes, sans commit ni redémarrage de la pile personnelle. Aucun changement de schéma ou d’observation existante.
