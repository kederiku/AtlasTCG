# Contribuer

Lire [CONTEXT.md](CONTEXT.md), les [règles du projet](docs/engineering.md) et les
[ADR](docs/adr/README.md) du périmètre concerné avant un changement.

## Environnement sur l’hôte

Pour utiliser uniquement l’application, suivre le démarrage Docker du README.
Pour développer : uv, Python épinglé par `.python-version`, Node 24 et Docker.

```sh
make install
# Créer/configurer .env s’il est absent ; ne pas écraser une configuration existante.
docker compose up -d --wait postgres
make migrate
make build
```

Garder `make api` et `make worker` dans deux terminaux, puis `make dev` dans un
troisième pour le frontend avec rechargement sur `http://127.0.0.1:5173`.
Vite transmet `/api` au serveur local sur le port 8000. Pour servir les changements
sur le port 8000, relancer `make build`. Le serveur lancé par `make api` n’utilise
pas `--reload` : le redémarrer après une modification Python. Pour travailler
uniquement sur l’interface, le worker peut rester arrêté ; les demandes restent
alors en attente.

Ne pas lancer simultanément l’API et le worker de Docker et ceux de l’hôte. Pour
passer de Docker au développement hôte, laisser finir les collectes puis exécuter
`docker compose stop api worker` ; PostgreSQL reste démarré.

`TCG_DATABASE_URL` désigne PostgreSQL sur `127.0.0.1`, avec `POSTGRES_PORT` publié.
Les valeurs `POSTGRES_*` et le mot de passe encodé dans cette URL doivent correspondre.
Les conteneurs construisent leur propre URL sur le service `postgres`.

Pour un spider utilisant le navigateur : `uv run playwright install chromium`.
TCGdex utilise directement HTTP et n’ouvre pas Chromium.

## Démarche de changement

1. Définir le comportement attendu avec des exemples Étant donné / Quand / Alors.
2. Choisir le niveau de test pertinent : cas d’usage, API, pipeline, migration ou UI.
3. Faire échouer un test observable, implémenter une petite tranche verticale, puis
   refactorer sous tests verts. Conserver le test comme non-régression.
4. Appliquer les [invariants](docs/engineering.md), sans coupler le domaine à HTTP,
   SQL ou Scrapy. Documenter une décision structurante par un nouvel ADR.
5. Mettre à jour la documentation et les exemples impactés dans le même changement.
6. Exécuter les contrôles pertinents, puis `make test` avant livraison.

```sh
uv run --locked pytest apps/scraping/tests/test_price_retention.py packages/persistence/tests/test_price_migration.py
npm test --prefix apps/frontend -- CardDetailPage
make test
```

Les tests unitaires et d’acceptation ne contactent pas de fournisseur externe.
Le test d’intégration du pipeline utilise un serveur HTTP local. Les tests BDD sont
exécutés par pytest-bdd, les tests React par Vitest/Testing Library.

## Commandes Make

`make` sans cible affiche l’aide ; il ne démarre plus Docker. `make help` liste
les cibles et leurs effets. Les [droits d’utilisation par un agent](AGENTS.md#commandes-make-autorisées-pour-un-agent)
distinguent contrôles autonomes et actions sur l’environnement d’exécution.

```sh
make lint           # Règles Ruff
make format-check   # Formatage Python et frontend, sans réécriture
make typecheck      # mypy strict sur core
make test-python    # pytest, BDD et tests d’architecture/intégration
make test-frontend  # Vitest
make build          # TypeScript et build Vite
make test           # Tous les contrôles ci-dessus, en séquence
```

`make format` trie les imports Python et formate toutes les sources Python/frontend.
Relire le diff, particulièrement si des modifications étaient déjà présentes.
Les installations et commandes Python du Makefile utilisent le verrou uv.
`make logs` retourne les 100 dernières lignes par service applicatif ;
`make logs-follow` continue de les suivre jusqu’à Ctrl+C.

`.gitignore` exclut `.env` et ses variantes, les environnements, caches, builds,
rapports de couverture et le dossier `/data/`. `.env.example`, les verrous, les
migrations et les fixtures restent versionnables. Un dossier de données personnalisé
dans le dépôt doit être explicitement ignoré ; éviter les règles qui masquent des fixtures.

## Changements Docker, stockage ou déploiement

```sh
make test-installations
make docker-build
make docker-test
```

Ce test crée un projet Compose unique, un volume PostgreSQL et un répertoire de
fichiers temporaires. Il les supprime en fin de test ; il ne modifie pas les données
de la pile normale. Python 3 sur l’hôte suffit à exécuter le script.

Les évolutions de stockage nécessitent une nouvelle migration Alembic et un test
sur des données existantes. Ne pas modifier une migration appliquée. Les tests sur
SQLite sont complétés par la validation PostgreSQL dans Docker.

## Ajouter une source

Suivre [le modèle du catalogue](docs/catalog-model.md). Ajouter des fixtures, un
adaptateur pur, le spider et les tests ; étendre le registre de collectes et son
contrat validé si le lancement depuis l’admin est prévu. Vérifier que le formulaire
expose les paramètres autorisés. Aucun nom de commande libre ne vient du frontend.

Le registre est `packages/core/src/tcg_core/collections/connectors.py` ; la
validation est dans `collections/models.py`. Le formulaire
`features/collections/CollectForm.tsx` charge les langues du connecteur TCGdex depuis
`/api/spiders` ; leurs libellés français restent dans le frontend, avec le code
comme repli. La source du formulaire reste explicitement TCGdex : ajouter une
autre source nécessite d’étendre la validation et la sélection de source.
Les normalisations vont dans `apps/scraping/src/tcg_scraping/sources/<source>/`,
les tests et fixtures près de l’application scraping. Étendre la CLI de
réindexation si cette source doit être reconstruite hors ligne ; elle ne compose
actuellement que l’adaptateur TCGdex.

## Avant livraison

Comportement demandé démontré, tests pertinents verts, formatage vérifié,
configuration/migrations documentées, aucun secret ni donnée personnelle ajouté,
limites restantes décrites. Ne pas annoncer un TCG comme pris en charge tant que
son connecteur réel n’est pas implémenté et vérifié.

## Travailler dans les frontières du monorepo

Toutes les commandes ci-dessus partent de la racine. `make install` installe tous
les membres du workspace uv et leurs outils de développement. Chaque membre a son
`pyproject.toml` ; le verrou `uv.lock` est commun. `make admin` reste un alias de
`make api`, qui fournit explicitement le chemin `apps/frontend/dist` au serveur.
La fabrique API seule ne recherche pas le frontend à travers des chemins de sources.

| Changement | Code | Tests proches |
|---|---|---|
| Contrat, identité, invariant, cas d’usage | `packages/core/src/tcg_core/` | `packages/core/tests/` |
| SQL ou migration | `packages/persistence/` | `packages/persistence/tests/` |
| Contrat HTTP ou fichiers servis | `apps/api/src/tcg_api/` | `apps/api/tests/` |
| Source, téléchargement, processus worker | `apps/scraping/src/tcg_scraping/` | `apps/scraping/tests/` |
| Écran et navigation | `apps/frontend/src/features/` | Tests `.test.tsx` voisins |
| Parcours traversant plusieurs applications | Adaptateurs concernés | `tests/integration/`, `tests/acceptance/` |

`make test-installations` crée quatre environnements temporaires, installe chaque
paquet sans les autres applications, ajoute seulement pytest (et httpx pour les
tests HTTP), vérifie les imports absents et exécute la suite de ce paquet. Les
installations sont non éditables : le test vérifie aussi le packaging des sources.
Les paquets du workspace sont reconstruits explicitement afin qu’une ancienne roue
locale en cache ne masque pas les changements de sources ; le verrou reste appliqué.
Les dépendances de test sont verrouillées et ne sont pas incluses dans les images.

Pour installer une application seule depuis la racine, utiliser un environnement
séparé plutôt que remplacer `.venv`. Conserver `--package` et `--no-dev` également
à l’exécution : un `uv run` sans ces options peut réinstaller les dépendances de
développement du workspace complet.

Exemple API, avec la base préalablement migrée et `.env` configuré :

```sh
UV_PROJECT_ENVIRONMENT=/tmp/tcg-api-dev uv sync --locked --package tcg-api --no-dev
UV_PROJECT_ENVIRONMENT=/tmp/tcg-api-dev uv run --locked --package tcg-api --no-dev \
  --env-file .env uvicorn tcg_api.app:create_app --factory --host 127.0.0.1 --port 8000
```

Sans `TCG_FRONTEND_DIR` défini, ce lancement ne configure pas de frontend :
`/api/health`, `/api/cards` et `/docs` restent disponibles, tandis que `/` retourne
404. Pour servir le build, définir
`TCG_FRONTEND_DIR=apps/frontend/dist`. Arrêter l’API habituelle avant d’utiliser
son port. Pour une isolation physique, le répertoire cible doit être neuf ou
réservé à cette application ; éviter un environnement temporaire déjà utilisé.

| Paquet sélectionné | Import Python | Dépendances applicatives | Entrée principale |
|---|---|---|---|
| `tcg-core` | `tcg_core` | Pydantic | Bibliothèque, aucune commande |
| `tcg-persistence` | `tcg_persistence` | core, SQLAlchemy, Alembic, pilote PostgreSQL | `alembic`, `tcg-migrate-images` |
| `tcg-api` | `tcg_api` | core, persistence, FastAPI/Uvicorn | `uvicorn tcg_api.app:create_app --factory` |
| `tcg-scraping` | `tcg_scraping` | core, persistence, Scrapy/Playwright, images | `tcg-worker`, `tcg-scrape`, `tcg-reindex` |

La même commande `uv sync` s’applique aux autres lignes avec un autre répertoire
et le bon `--package`. Le frontend s’installe indépendamment avec
`npm ci --prefix apps/frontend`. Les migrations Alembic restent dans le dépôt,
dans `packages/persistence/migrations/` ; `alembic.ini` se trouve à la racine.
Installer le paquet persistence seul ne fournit pas cet historique dans sa wheel.
L’image `migrate` le copie explicitement.

Les groupes `test`, `api-test` et `dev` sont définis dans le `pyproject.toml` racine.
`make test-installations` ajoute les groupes minimaux aux quatre environnements,
et `--no-editable` pour vérifier le contenu réellement installé. Le typage strict
porte sur core ; les autres paquets s’appuient sur Ruff et leurs tests de contrats.

`tcg-scrape`, `tcg-worker` et `tcg-reindex` appartiennent à `tcg-scraping` ;
`tcg-migrate-images` appartient à `tcg-persistence`. Le lanceur `tcg-scrape` configure
Scrapy explicitement et fonctionne hors du répertoire de sources. Les chemins de
stockage relatifs restent relatifs au répertoire de lancement ; les définir par
`TCG_IMAGES_DIR`, `TCG_JOBS_DIR` et `TCG_DATABASE_URL` pour un autre répertoire.

## Faire évoluer le schéma

Créer une nouvelle révision depuis la racine avec une base de développement à jour :

```sh
uv run --env-file .env alembic revision --autogenerate -m "describe the schema change"
```

Relire la migration générée : les transformations de données nécessitent souvent
du code explicite. Ajouter un test partant de la révision précédente avec des
données représentatives, puis appliquer et contrôler sur la base de développement :

```sh
uv run --env-file .env alembic upgrade head
uv run --env-file .env alembic check
```

Ces commandes ciblent la base choisie dans `.env`, pas une base temporaire implicite.
Ne pas les utiliser sur la base personnelle pour élaborer une migration. La CI
les exécute aussi sur une SQLite neuve ; le test Docker valide les migrations sur
PostgreSQL. Les migrations de schéma et `CATALOG_VERSION` ont des rôles différents :
voir [le modèle du catalogue](docs/catalog-model.md#versions-et-observations).

## Mettre à jour la documentation

Une route ou un paramètre change : actualiser [la référence API](docs/api.md).
Un parcours d’installation ou de maintenance change : actualiser ce guide et
[l’exploitation](docs/operations.md). Un invariant change : mettre à jour modèle,
acceptation et ADR concernés. Les plans de `docs/superpowers/` restent des archives
d’exécution ; les liens et commandes à jour doivent être dans les guides courants.
Une correction documentaire seule appelle une vérification des références et
exemples, sans ajouter de tests artificiels ni redémarrer la pile personnelle.
