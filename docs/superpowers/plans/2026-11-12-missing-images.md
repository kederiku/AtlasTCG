# Réparation des images manquantes — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Réparer les images du catalogue depuis Collectes, avec téléchargement des URL connues et découverte TCGdex si elles manquent.

**Architecture:** Une demande de réparation distincte partage la file et le worker existants. Core décide des images à réparer via des ports typés ; persistence écrit seulement les médias ; un spider dédié réutilise le téléchargement et la conversion WebP.

**Tech Stack:** Python/Pydantic, SQLAlchemy, Scrapy/Pillow, FastAPI, React/TypeScript/React Query, pytest/BDD/Vitest.

**Spec:** [Conception approuvée](../specs/2026-11-12-missing-images-design.md).

## Global Constraints

- Toutes les impressions existantes et toutes leurs langues ; aucune nouvelle carte.
- Préserver les fichiers présents, identités, observations, données brutes et dates.
- Découverte d’URL uniquement Pokémon/TCGdex ; téléchargement des URL déjà connues.
- Même worker unique, mêmes limites réseau et même timeout ; aucun nouveau service.
- Aucun commit, redémarrage de la pile personnelle ou collecte réelle.
- Réutiliser le checkout courant et ses dépendances verrouillées.

## Review Focus

- Les anciens paramètres sans type doivent rester lisibles et exécutables (tâche 1).
- Des métadonnées d’images absentes avec un fichier déjà présent ne doivent pas provoquer de remplacement (tâche 2).
- Plusieurs faces dont une échoue doivent conserver les fichiers précédents (tâche 3).
- Un chemin enregistré traversant le stockage, notamment via un lien symbolique, doit être refusé (tâche 3).
- Une reprise répétée, une source indisponible ou une réponse incorrecte ne doivent pas produire un faux succès ni arrêter les autres impressions (tâches 3 et 4).

### Task 1: Soumettre et exécuter une demande typée de réparation

**Files:** `packages/core/src/tcg_core/collections/{models,submission,execution,ports}.py`, `apps/api/src/tcg_api/{routes,schemas}/collections.py`, `apps/scraping/src/tcg_scraping/runner.py`, `tests/acceptance/features/collection.feature`, `tests/acceptance/test_collection_admin.py`, `apps/scraping/tests/test_runner.py`.

**Interfaces:** Ajouter `ImageRepairRequest(kind="repair_images")`, `JobRequest = CollectionRequest | ImageRepairRequest`, `parse_job_request(parameters)` ; `POST /api/jobs` accepte les deux demandes et les anciens paramètres restent valables. Le runner choisit le spider `repair_images` uniquement pour ce type autorisé.

- [x] Écrire le scénario API : `POST {"kind":"repair_images"}` retourne 202 ; historique et détail conservent exactement cette demande ; paramètres libres refusés.
- [x] Exécuter le scénario et observer 422 avant implémentation.
- [x] Introduire le contrat, la validation et le dispatch ; couvrir aussi l’exécution d’un ancien job sans `kind`.
- [x] Exécuter les tests API/BDD, core et runner ; résultat attendu : tous verts.

### Task 2: Sélectionner et enregistrer seulement les médias à réparer

**Files:** créer `packages/core/src/tcg_core/catalog/image_repair.py`, `packages/persistence/src/tcg_persistence/image_repair.py`, tests associés dans chaque paquet.

**Interfaces:** `ImageAsset` (référence locale validée préservant ses métadonnées), `RepairCandidate` (identité, numéro, set, URL et images), `ImageDownload(index, url, path)`, `RepairPlan(candidate, images, downloads, needs_discovery)`. `ImageRepair(store, files)` expose `plan(candidate)`, `discover(candidate, urls)` et `complete(plan, downloaded)` ; ports `ImageRepairStore` (candidats, écriture URL, écriture images) et `ImagePresence.exists(path)`.

- [x] Écrire puis faire échouer les tests de planification : fichier présent ignoré, référence absente reconstruite, URL connue téléchargée au bon index, absence d’URL à découvrir.
- [x] Implémenter les règles pures et les ports ; vérifier les tests et mypy core.
- [x] Écrire puis faire échouer un test SQLite réel : conserver une URL découverte puis rattacher un média ne change aucune autre colonne, extension ou langue.
- [x] Implémenter le dépôt SQL avec lecture par lots et mises à jour ciblées ; vérifier les tests de persistance.

### Task 3: Réparer les fichiers et découvrir les URL via Scrapy

**Files:** créer `apps/scraping/src/tcg_scraping/sources/repair_images.py`, `apps/scraping/src/tcg_scraping/image_repair.py`, `apps/scraping/tests/test_image_repair.py` ; réutiliser `pipelines/media.py` et `sources/tcgdex/normalize.py` sans sauvegarde complète des observations.

**Interfaces:** `LocalImagePresence(root).exists(path)` confine les chemins. Spider `repair_images` assemble `ImageRepair` et le dépôt, produit des items contenant le plan, interroge uniquement les fiches nécessaires, puis ferme ses ressources. Pipeline média dédié réutilise la préparation WebP ; pipeline de persistance appelle `complete`.

- [x] Test d’intégration avec serveur HTTP local : carte avec URL, carte sans URL, carte avec fichier, carte indisponible ; vérifier fichiers, requêtes reçues, références et observations inchangées. Observer l’échec avant implementation.
- [x] Implémenter le parcours et les statistiques `images/examined`, `images/downloaded`, `images/present`, `images/unavailable`, `images/errors` ; indisponibilité source différente d’une erreur technique.
- [x] Ajouter avant chaque extension son test rouge : réponse incorrecte/erreur réseau, reprise, plusieurs faces, chemins non sûrs et fichiers non référencés ; implémenter puis vérifier.
- [x] Exécuter tests scraping, tests métier/persistance affectés et tests d’intégration existants ; tout doit rester vert.

### Task 4: Déclencher et suivre la réparation dans l’admin

**Files:** `apps/frontend/src/features/collections/{types,api,useCollections,CollectionsPanel,JobLogs}.tsx` ou `.ts` selon le fichier existant, `apps/frontend/src/app/App.tsx`, traductions dans `shared/i18n`, tests voisins et `app/App.test.tsx`.

**Interfaces:** Union TypeScript des demandes ; `requestImageRepair()` et mutation distincte dans `useCollections`. Bouton « Réparer les images manquantes » avec texte de portée, états d’envoi/erreur ; historique distingue collecte/réparation et présente les compteurs propres aux médias.

- [x] Test React rouge : clic depuis Collectes envoie `{kind:"repair_images"}` et affiche la demande dans l’historique ; tester aussi erreur de soumission.
- [x] Implémenter le bouton, la mutation, les libellés et le bilan FR/EN/ES en préservant les anciens jobs.
- [x] Exécuter Vitest puis vérifier le parcours navigateur avec base temporaire et sans worker réel.

### Task 5: Documentation et vérification finale

**Files:** `CONTEXT.md`, `docs/{api,acceptance,architecture,engineering,operations}.md`, nouvel ADR si nécessaire pour préciser la réparation sans observation.

- [x] Actualiser les guides et les exemples d’acceptation ; consigner résultats et décisions dans ce plan.
- [x] Exécuter `make test`, `make test-installations`, `make docker-build` puis `make docker-test` ; lire tous les résultats.
- [x] Faire relire le diff complet par un agent indépendant ; corriger les défauts importants avec un test de régression puis rejouer les contrôles affectés.
- [x] Livrer le changement et les preuves, sans commit ni déploiement personnel.

## Progression

- Conception approuvée par l’utilisateur ; checkout initial propre sauf cette conception.
- Base observée : 11 tests collection/pipeline/core passent.
- Décision d’exécution : mise en œuvre dans cette session et checkout courant ; les autorisations de réalisation déjà données sont conservées, sans nouvelle demande de validation de routine.
- Pré-vérification des interfaces : tâche 1 fournit la demande aux tâches 3/4 ; tâche 2 fournit le plan typé et le dépôt à la tâche 3 ; pas de dépendance API → scraping.
- Tâches 1/2 : tests API 422→202, exécution et écritures SQL ciblées rouges puis verts ; mypy core vert. La validation des demandes utilise directement `TypeAdapter[JobRequest]`, sans fonction de transfert supplémentaire.
- Tâche 3 : téléchargement connu/découvert, fichiers présents, reprise, erreurs HTTP/réponse, chemins et plusieurs faces vérifiés sur HTTP local. Le contrôle d’architecture a imposé l’assemblage avec `Repository`, propriétaire du moteur, plutôt qu’un import SQLAlchemy depuis scraping.
- Tâche 4 : 8 tests de parcours collection/réparation verts, FR/EN/ES. Navigateur : soumission réelle sur base temporaire, ligne queued, ouverture du bilan/journal et vérification visuelle. Serveur de test arrêté ensuite.
- Première passe complète : 114 tests Python et 31 tests frontend verts ; quatre installations isolées vertes. Le test PostgreSQL a réparé le WebP, puis révélé une assertion de test oubliant les URL d’images dans `versions` ; comparaison corrigée pour vérifier séparément les données de chaque version.
- Revue indépendante : deux P2 reproduits. Valeurs source `image=[]/{}/false/0` maintenant refusées ; le test lent a observé 50 candidats avant le premier média, d’où une limite explicite de travaux en cours. Ce test a aussi reproduit une course de création de dossier dans le stockage Scrapy utilisé depuis les threads : publication sérialisée, conversion parallèle conservée.
- Limites examinées : fichiers présents corrompus et URL connues invalides restent les exclusions approuvées ; aucune collecte fournisseur réelle. Des lignes SQL corrompues hors des parcours d’écriture valides ne font pas l’objet d’une récupération spécialisée : la validation fait échouer le job avec diagnostics.
- Vérification finale après corrections : `make test` vert (119 tests Python, 31 tests frontend, Ruff, formatage, mypy et build) ; `make test-installations` vert (core 9, persistence 17, API 10, scraping 46) ; `make docker-build` et `make docker-test` verts. Le test Docker confirme une réparation prise en charge par le worker, un WebP restauré via HTTP local, les observations conservées et la persistance après redémarrage. Projet temporaire nettoyé. Avertissement existant FastAPI/httpx sans échec.
- Revue : deux P2 corrigés et vérifiés rouge→vert ; aucun mineur différé. Liens documentaires et `git diff --check` vérifiés. Aucun commit ni mise à jour des services personnels.
