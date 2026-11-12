# Séparation du frontend, de l’API et du scraping

> Conception réalisée, conservée comme historique. L’« état constaté » ci-dessous
> décrit le dépôt avant la refonte. Pour le fonctionnement actuel, lire
> [l’architecture](../../architecture.md), [l’API](../../api.md) et
> [le guide de contribution](../../../CONTRIBUTING.md).

Statut : conception approuvée par l’utilisateur le 12 novembre 2026.
Le 12 novembre 2026, l’utilisateur a choisi des applications et des dépendances
séparées, avec un socle métier partagé, puis validé la présente conception.
L’implémentation est suivie dans le plan associé.

## Intention et périmètre

Un nouveau contributeur doit pouvoir identifier immédiatement où travailler sur
l’interface, une route HTTP, une règle métier, la persistance ou une collecte.
L’API doit fonctionner sans installer Scrapy, Playwright ou Chromium ; le worker
doit fonctionner sans installer FastAPI ni Uvicorn. La séparation doit être
vérifiée par les outils, et pas seulement annoncée dans la documentation.

Le périmètre couvre l’ensemble du dépôt : Python, frontend, tests, configuration,
images Docker, Compose, CI, commandes de développement et documentation. Il s’agit
d’une refonte structurelle à comportement public conservé. Les améliorations
internes servent cette séparation et la lisibilité, sans ajouter de fonctionnalités.

## État constaté

- `src/tcg_catalog/` contient les couches métier, SQL, HTTP et Scrapy. Les points
  d’entrée API, worker et réindexation partagent `interfaces/`.
- Le `pyproject.toml` installe toutes les dépendances ensemble. L’image Docker
  commune installe aussi Chromium pour l’API et le service de migration.
- `domain/collection.py` interprète directement des clés de statistiques Scrapy.
  `application/collections.py` regroupe soumission et exécution des collectes.
- `interfaces/api.py` assemble les ressources, déclare toutes les routes, lit les
  journaux et sert le frontend. Les lectures de jobs contournent les cas d’usage.
- `image_paths.py` mélange nommage pur et empreinte de requête Scrapy ; la commande
  de migration des images dépend donc indirectement de Scrapy.
- Le frontend possède déjà des fonctionnalités, mais `App.tsx` orchestre aussi
  les collectes, `api.ts` mélange transport et contrats métier, et `CatalogMedia.tsx`
  contient aussi les journaux de collecte.
- Les tests et règles métier existants sont utiles. Leur conservation précède
  toute extraction. L’ancien refactoring du catalogue reste acquis ; ses garanties
  de comportement restent valables, mais pas l’obligation de conserver les anciens
  chemins d’import internes dans cette refonte plus large.
- Le checkout n’a pas de commit initial et les fichiers applicatifs sont non
  suivis. Une référence temporaire des fichiers concernés permettra la comparaison
  et la revue sans créer de commit ni inclure `.env`, `data/` ou les dépendances.

## Approches examinées

1. **Applications et dépendances séparées dans un monorepo — choix de l’utilisateur.**
   Les trois applications ont un emplacement explicite. Deux bibliothèques Python
   partagées distinguent le métier de SQL. Un workspace uv et un lockfile commun
   gardent le développement coordonné ; les installations de production sont
   sélectives. Cela nécessite d’adapter le packaging et Docker, mais donne une
   séparation démontrable sans dupliquer le métier.
2. **Dossiers séparés avec une installation Python commune.** Plus simple à déplacer,
   mais conserve les dépendances Scrapy/Chromium dans l’environnement API. Cette
   option n’a pas été retenue par l’utilisateur.

Des dépôts, une base ou un service réseau supplémentaires ne répondent pas à un
besoin de cette installation locale. Ils ajouteraient du déploiement et de la
synchronisation sans améliorer la frontière de responsabilité demandée.

## Arborescence cible

```text
apps/
  frontend/                     Application React/Vite et ses tests
    src/
      app/                      Composition, routage et mise en page générale
      features/catalog/         Catalogue, détail, médias, filtres, contrats et requêtes
      features/collections/     Formulaire, historique, journaux, contrats et requêtes
      shared/http/              Transport HTTP et erreurs communs
      components/ui/            Composants visuels génériques existants
  api/                          Distribution Python tcg-api
    src/tcg_api/
      app.py                    Fabrique FastAPI et durée de vie des ressources
      routes/                   Catalogue, collectes, disponibilité
      schemas/                  Contrats HTTP explicites
      presentation/             Projection des médias vers les URLs HTTP
      security.py               Contraintes de l’admin local
      static.py                 Fichiers et frontend compilé
    tests/
  scraping/                     Distribution Python tcg-scraping
    src/tcg_scraping/
      worker.py                 Boucle, verrou et signaux du worker unique
      runner.py                 Sous-processus, timeout, arrêt et résultat normalisé
      settings.py               Configuration Scrapy uniquement
      sources/tcgdex/           Normalisation pure et spider séparés
      pipelines/                Validation, médias, persistance
      middleware.py             Filtrage des cartes déjà présentes
      extensions/               Capture des statistiques Scrapy
      cli/                      Lancement explicite et réindexation hors ligne
    tests/
    scrapy.cfg
packages/
  core/                         Distribution Python tcg-core, dépendance Pydantic
    src/tcg_core/
      catalog/                  Contrats, règles, ports, consultation, réindexation
      collections/              Demandes, résultats, ports, soumission, consultation, exécution
    tests/
  persistence/                  Distribution Python tcg-persistence
    src/tcg_persistence/        Connexion, schéma, dépôts SQL et maintenance des images
    migrations/                 Historique Alembic existant déplacé, versions inchangées
    tests/
tests/
  acceptance/                   Parcours BDD traversant plusieurs applications
  architecture/                 Règles de dépendance et contrats d’installation
  fixtures/                     Données partagées sans accès fournisseur
scripts/                        Vérification de pile et outils du dépôt
docs/                           Architecture, exploitation, métier et décisions
pyproject.toml                  Workspace uv et outils communs
uv.lock                         Résolution commune des dépendances Python
alembic.ini                     Entrée commune vers les migrations de persistance
compose.yaml                    Assemblage de l’installation locale
Dockerfile                      Cibles distinctes api, scraping et migrate
Makefile                        Commandes courtes et explicites depuis la racine
```

Les noms exacts des petits modules restent à l’implémenteur. Chaque découpage doit
correspondre à une responsabilité réelle ; pas de fichier par classe par principe,
de réexport systématique, de dépôt générique ni de bus d’événements.

## Règles de dépendance

| Élément | Peut dépendre de | Ne doit pas dépendre de |
|---|---|---|
| `tcg_core` | Bibliothèque standard, Pydantic | SQLAlchemy, FastAPI, Scrapy, processus, applications |
| `tcg_persistence` | `tcg_core`, SQLAlchemy, pilote SQL, Alembic pour les migrations | API, Scrapy, Playwright |
| `tcg_api` | `tcg_core`, `tcg_persistence`, FastAPI/Uvicorn | `tcg_scraping`, Scrapy, Playwright, Chromium |
| `tcg_scraping` | `tcg_core`, `tcg_persistence`, Scrapy, Pillow, Playwright, filelock | `tcg_api`, FastAPI/Uvicorn |
| Frontend | Ses fonctionnalités, composants et client HTTP | Code Python, détails SQL, exécution Scrapy |

Les routes assemblent ou appellent des cas d’usage ; elles ne construisent ni SQL
ni commandes système. Les cas d’usage définissent des ports étroits avec des types
explicites aux frontières. Le stockage implémente ces ports. Les points d’entrée
possèdent et ferment les ressources qu’ils construisent.

La soumission, la consultation et l’exécution d’une collecte deviennent des
responsabilités explicites. Le runner Scrapy traduit code de sortie et statistiques
en résultat typé avant de le fournir au cas d’usage. Le métier n’interprète plus
`finish_reason`, `log_count/ERROR` ou `item_dropped_count`. Les statistiques restent
conservées comme diagnostics opaques pour maintenir les réponses et journaux actuels.

Le catalogue déclaratif des connecteurs autorisés est partagé sans import de spider
ni découverte dynamique de Scrapy. L’identifiant externe existant `spider` et la
route `/api/spiders` restent compatibles. Les règles propres à TCGdex restent dans
son adaptateur ; le modèle des autres jeux ne reçoit aucune hypothèse Pokémon.

La normalisation TCGdex reste pure, même rangée avec son connecteur dans le scraping.
La réindexation associe cette normalisation au cas d’usage partagé depuis sa CLI.
Le nommage des fichiers devient une fonction pure du catalogue ; seule l’empreinte
de requête reste dans Scrapy. La maintenance des fichiers peut ainsi fonctionner
avec core/persistence seuls.

## API et frontend

L’API conserve les URLs, paramètres, codes HTTP, réponses et protections actuels.
Les schémas de collectes et de connecteurs deviennent explicites comme ceux du
catalogue. La lecture des derniers 64 Ko de journaux utilise un port de lecture,
implémenté par un adaptateur fichier côté API ; elle n’importe pas le worker.

Le frontend reste servi sur la même origine par l’API dans l’installation locale.
Le code source et le build appartiennent à `apps/frontend` ; l’API ne reçoit que
les fichiers compilés et leur chemin de configuration. Il n’est pas nécessaire
d’ajouter un serveur Node ou Nginx à l’exécution. Sans build frontend, l’API seule
doit pouvoir démarrer et répondre à ses routes.

`App` compose les pages et la mise en page générale. Les opérations de collecte,
le formulaire et les journaux appartiennent à `features/collections`. Les images
et règles de cartes appartiennent à `features/catalog`. Les types et accès HTTP
spécifiques suivent leurs fonctionnalités ; le transport commun reste petit.
Les filtres du catalogue conservent leur représentation dans l’URL.
Les tests de composants restent proches du comportement testé.

## Installation, exploitation et compatibilité

Chaque application Python et bibliothèque dispose d’un `pyproject.toml`. Le
workspace uv lie les dépendances locales et permet une installation complète pour
développer. Des installations isolées par application vérifient aussi l’absence
des frameworks interdits ; le succès dans l’environnement complet ne suffit pas.

Docker produit des images distinctes à partir de cibles dédiées. Seul le scraping
installe Chromium et ses bibliothèques. L’image API reçoit le frontend compilé.
L’image de migration contient core/persistence et Alembic, sans framework HTTP ou
scraping. Le test de pile et la CI construisent toutes les images nécessaires.

Compose conserve les noms de services `postgres`, `migrate`, `api` et `worker`,
l’ordre de disponibilité, les ports locaux, les montages, UID/GID et variables
existantes. Il conserve la base partagée et le worker unique. L’API persiste une
demande ; le worker la prend ensuite en charge indépendamment.

Les commandes Make existantes restent utilisables ; `make api` devient le nom
explicite du démarrage HTTP et `make admin` reste un alias documenté. Les nouvelles
CLI de scraping/réindexation et de maintenance sont nommées et documentées. Le
lanceur Scrapy configure explicitement son module de réglages, sans dépendre de la
découverte d’un `scrapy.cfg` dans le répertoire courant. Les commandes du dépôt
s’exécutent depuis sa racine, avec les mêmes chemins de données qu’auparavant.

Les anciens imports Python internes `tcg_catalog.*` sont remplacés dans tous les
appelants du dépôt ; aucun paquet de compatibilité mêlant à nouveau les applications
n’est conservé. Les changements de commandes sont documentés. Les identifiants
Alembic et le contenu des versions déjà appliquées ne sont pas modifiés ; seul le
chemin de l’historique et son assemblage sont adaptés. Aucun changement de schéma
ou déplacement des fichiers utilisateurs n’est prévu.

La refonte ne redémarre pas l’installation personnelle pour se valider. Les tests
utilisent des ressources temporaires isolées. Une éventuelle bascule opérationnelle
devra attendre la fin des collectes et suivre les instructions de sauvegarde.

## Critères d’acceptation

1. Étant donné une installation API seule sans Scrapy, Twisted, Playwright, Pillow
   ou filelock, les lectures catalogue, les images, la soumission d’une collecte,
   sa consultation et ses journaux fonctionnent. La demande reste en attente sans
   worker et peut être exécutée lorsqu’un worker devient disponible.
2. Étant donné une installation scraping seule sans FastAPI/Uvicorn, le worker
   exécute une collecte sur une source HTTP locale et persiste carte, extension,
   bloc et WebP ; l’API retrouve ensuite ces observations.
3. Une collecte avec code zéro mais statistiques d’échec reste en échec. Le succès,
   les rejets d’image, le timeout, la file vide et la reprise des états après arrêt
   gardent leurs comportements ; les résultats partiels restent conservés.
4. Les tests des modèles, du nommage et des cas d’usage métier s’exécutent sans
   FastAPI, SQLAlchemy ou Scrapy. Les dépendances interdites échouent aux contrôles
   d’architecture, y compris lorsqu’elles sont introduites par un module partagé.
5. Une installation persistence seule applique les migrations existantes et exécute
   la prévisualisation de maintenance des images sans Scrapy. Les migrations sont
   validées sur base neuve et sur données préexistantes, sans réinitialisation.
6. Identités localisées, absence de prix, provenance, dates, transactions, noms et
   ordre des images, filtres, pagination et codes HTTP passent les tests existants.
7. Le frontend conserve catalogue, liens directs, filtres URL, formulaire de collecte,
   suivi et journaux, avec états d’erreur/chargement et accessibilité existants.
8. Le test Docker isolé vérifie toutes les images, la communication par la base,
   les fichiers, le worker, Chromium côté scraping, la disponibilité API et la
   conservation des données après redémarrage des seuls services temporaires.
9. Un contributeur trouve dans le README l’arbre principal, la responsabilité de
   chaque application, les commandes et les liens vers les règles détaillées.

## Craftsmanship et méthode de validation

Travailler par petites tranches : exemples observables, test rouge pour les nouveaux
contrats de séparation, correction minimale, puis extraction sous tests verts.
Les tests existants caractérisent les comportements à conserver. Les contrôles
de frontières vérifient des règles d’architecture déclarées, sans figer la forme
privée des classes ou tester uniquement que des dossiers existent.

Conserver Ruff, Prettier, TypeScript, pytest/BDD et Vitest. Ajouter des contrôles
automatisés des imports interdits et des installations sélectives. Les contrats
modifiés portent des types explicites ; un contrôle statique Python sera introduit
avec un périmètre explicite sur core et les nouveaux ports, étendu uniquement si
les annotations des frameworks le permettent sans masquer les erreurs. Le choix
de l’outil et de la mécanique des contrôles est laissé à l’implémenteur.

La livraison exige `make test`, puis `make docker-build && make docker-test`.
Un parcours navigateur vérifie la composition frontend déplacée. Une revue
indépendante examine dépendances, comportements, packaging et documentation.
Les éventuelles limites de vérification sont rapportées précisément ; aucune
promesse abstraite de perfection ne remplace ces critères mesurables.

## Documentation et historique des décisions

Mettre à jour README, CONTRIBUTING, CONTEXT, architecture, engineering, exploitation,
modèle du catalogue et exemples d’acceptation lorsque les chemins ou responsabilités
changent. Ajouter un ADR 0006 qui précise 0001 (modules et imports de compatibilité)
et remplace le choix d’image commune de 0004. Actualiser l’index des ADR, en préservant
le contenu historique et en signalant les décisions remplacées. Les anciennes
spécifications décrivent leur tranche passée, pas l’architecture courante.

## Hors périmètre et décisions laissées à l’implémenteur

Pas de nouveau TCG, de refonte visuelle, d’authentification, de file distribuée,
de base par application, de publication ni de commit. Ne pas effectuer de collecte
sur un fournisseur externe pour valider la refonte.

L’implémenteur choisit les noms de petits modules, les extractions de composants,
la mécanique d’injection, le contrôle d’imports et les étapes du workspace uv,
dans les limites des contrats ci-dessus. L’étape suivante après approbation est
un plan d’implémentation traçable, puis son exécution et ses vérifications.

## Vérifications de préparation — 12 novembre 2026

- 48 tests Python passent dans le bac à sable ; le test HTTP local échoue à
  l’ouverture de son port de boucle locale. Relancé avec cette ouverture autorisée,
  il passe également : les 49 tests existants ont réussi, sans changement de code.
- Les 8 tests frontend passent. Ruff et le contrôle de formatage Python passent.
- Avertissement préexistant : dépréciation Starlette de l’utilisation de `httpx`
  dans TestClient. Aucun changement de dépendance n’a été effectué à ce stade.
- Le contrôle de construction frontend et le test Docker ne sont pas réexécutés
  pour cette conception documentaire ; ils restent obligatoires après implémentation.
- Relecture indépendante de la conception : aucune question importante restante
  pour établir le plan. Cela valide sa précision, pas une implémentation encore absente.
