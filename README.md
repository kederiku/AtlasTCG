# TCG Catalog · atlasTCG

Catalogue local de cartes TCG multilingues et de leurs images WebP. L’admin permet
la recherche par nom, jeu, langue, bloc et extension, la consultation d’une fiche par URL,
et le lancement/suivi des collectes.

**Connecteur disponible : Pokémon via TCGdex.** Les extensions peuvent être rattachées à un bloc localisé. Le modèle commun est extensible
à d’autres jeux ; leurs connecteurs ne sont pas encore implémentés. Les prix sont
exclus, y compris des données brutes. Les coûts de jeu sont conservés.

## Se repérer dans le dépôt

```text
apps/frontend/        Interface React, fonctionnalités catalogue et collectes
apps/api/             Serveur HTTP FastAPI, routes, schémas, sécurité, fichiers
apps/scraping/        Worker, Scrapy, connecteurs, images et réindexation
packages/core/        Métier et cas d’usage ; aucun HTTP, SQL ou Scrapy
packages/persistence/ Dépôts SQL, connexion, migrations et maintenance des fichiers
tests/                Acceptation, intégrations entre applications, architecture
scripts/              Vérifications des installations et de la pile Docker
docs/                 Modèle, architecture, pratiques et exploitation
```

**Où commencer ?** Une règle métier : `packages/core/src/tcg_core/` ; une route :
`apps/api/src/tcg_api/routes/` ; une collecte : `apps/scraping/src/tcg_scraping/` ;
un écran : `apps/frontend/src/features/`. Chaque application et bibliothèque possède
ses tests. Les scénarios qui traversent plusieurs composants vivent dans `tests/`.

L’API enregistre les demandes et consulte les résultats. Le worker seul exécute
Scrapy. Ils partagent PostgreSQL et les fichiers, sans s’importer mutuellement.
L’API s’installe sans Scrapy/Chromium, le scraping sans FastAPI. Le frontend est une
application source distincte ; son build est servi par l’API sur la même origine.
Voir [l’architecture et les règles de dépendance](docs/architecture.md).

## Démarrer tout avec Docker

Prérequis : Docker Engine avec Compose v2.24.4+ ou Docker Desktop. Python, Node et
uv sur l’hôte ne sont pas nécessaires pour lancer l’application.

1. Créer `.env` depuis [.env.example](.env.example) **s’il n’existe pas déjà**.
2. Renseigner `POSTGRES_PASSWORD`. Régler `TCG_UID` et `TCG_GID` sur les résultats
   de `id -u` et `id -g` pour que les conteneurs puissent écrire dans `data/`.
3. Démarrer :

```sh
mkdir -p data/images data/jobs/admin
docker compose up --build -d --wait
```

Ou utiliser `make up`. `make` seul affiche désormais l’aide, sans lancer la pile.
Ouvrir [atlasTCG](http://127.0.0.1:8000) et
[la documentation API](http://127.0.0.1:8000/docs).

Compose lance PostgreSQL, attend sa disponibilité, applique les migrations Alembic,
puis démarre l’API et le worker. Trois images distinctes servent l’API, le scraping et les migrations. Le frontend
React compilé est inclus uniquement dans l’image API. Chromium et ses dépendances
sont installés uniquement dans l’image scraping pour les spiders Playwright. Le service `migrate` terminé avec le code 0 est normal.

Les services sont accessibles uniquement depuis la machine locale. Avant un arrêt
ou une reconstruction, laisser finir les collectes et cesser les nouvelles
soumissions ([vérification des travaux actifs](docs/operations.md#démarrage-et-arrêt)).
Arrêter ensuite l’ensemble en conservant les données :

```sh
docker compose down
```

**Installation existante :** garder le même `.env`, le même dossier et le volume
PostgreSQL existant. Avant la bascule, laisser finir les collectes puis arrêter les
anciens `make admin` / `make worker`. Ils ne doivent pas tourner en parallèle avec
leurs équivalents Docker. Ne pas changer le nom du projet Compose sans prévoir
explicitement le transfert du volume.

## Utilisation

Depuis **Nouvelle collecte**, choisir les langues, un bloc puis **Tout le bloc**
ou une extension. Avec **Tous les blocs**, choisir une extension précise, même
si elle n’a pas encore été importée. Les listes proviennent de TCGdex ; les langues
indisponibles sont indiquées. Toutes les cartes du périmètre sont parcourues. Les cartes
déjà au contrat courant sont ignorées avant le téléchargement du détail et des images.
Une ancienne version du contrat peut être recollectée. L’option
actualisation force la relecture des données ; elle conserve le cache des images.

La [référence API](docs/api.md#soumettre-et-suivre-une-collecte) montre comment
soumettre la même demande depuis un script en utilisant la file du worker.
Pour un crawl Scrapy direct, suivre la [procédure CLI](docs/operations.md#collecter-et-actualiser),
qui évite les collectes concurrentes et explique le rafraîchissement des images.
La saisie **Cartes précises (avancé)** accepte jusqu’à 100 identifiants, sans
combinaison avec un bloc/une extension. Le formulaire et l’API exposent les 18 langues
déclarées par le connecteur ; français et anglais sont cochés par défaut.
L’API historique conserve les demandes bornées ; la CLI accepte aussi `-a limit=0`.

Une fiche dispose d’une URL stable, par exemple
[/cards/pokemon/tcgdex/fr/base1-4](http://127.0.0.1:8000/cards/pokemon/tcgdex/fr/base1-4).
Le retour au catalogue conserve recherche, filtres et pagination. Le filtre de bloc
restreint les extensions proposées ; un lien sur la fiche ouvre les cartes du bloc. Les vrais noms
d’extension sont affichés séparément de leur code stable.

## Données conservées

- PostgreSQL : blocs, extensions et impressions localisées, règles et historique des collectes.
- `data/images/<jeu>/<langue>/<set>/<numéro>-<set>.webp` : images locales.
- `data/jobs/admin/<identifiant>/` : journaux et statistiques des collectes.

L’identité d’une carte est `(game, source, source_id, language)` ; les noms ne sont
jamais des identifiants. Textes, illustrateurs, rareté, faces, capacités, coûts,
statistiques et légalité sont conservés selon ce que fournit la source. Aucun prix
n’est retenu. L’absence de donnée ne vaut pas zéro.

La base et les fichiers persistent après `docker compose down`. Ne pas utiliser
`down --volumes` sur la pile réelle, sauf suppression volontaire de la base.
Sauvegarder ensemble PostgreSQL et les fichiers : [guide d’exploitation](docs/operations.md).

## Développement et qualité

Le runtime Python est épinglé à **3.14.7** dans `.python-version` et le Dockerfile.
Le frontend utilise React, TypeScript, shadcn/ui et Vite ; son build Docker utilise
Node 24. `uv.lock` et `apps/frontend/package-lock.json` verrouillent les dépendances.
Une montée de version nécessite une validation explicite, pas un téléchargement
silencieux d’une version « latest ».

Pour travailler sur l’hôte avec rechargement frontend, suivre
[CONTRIBUTING.md](CONTRIBUTING.md). Vérifications :

```sh
make test         # Ruff, mypy strict sur core, pytest/BDD, Prettier, Vitest et build
make test-installations # quatre environnements Python séparés, installations non éditables
make docker-build
make docker-test  # pile temporaire isolée, jamais la base personnelle
```

La CI exécute ces contrôles et teste aussi Docker/PostgreSQL. Le test Docker vérifie
le démarrage, le worker, les doublons, le service WebP, Chromium et la persistance
après redémarrage, sans dépendre de l’API TCGdex.

## Documentation du projet

| Document | Contenu |
|---|---|
| [CONTEXT.md](CONTEXT.md) | Vocabulaire et périmètre du domaine |
| [CONTRIBUTING.md](CONTRIBUTING.md) | Environnement de développement et démarche de contribution |
| [Règles et pratiques](docs/engineering.md) | DDD, BDD, ATDD, TDD, conventions et critères de livraison |
| [Architecture](docs/architecture.md) | Couches, flux, API et processus |
| [Référence API](docs/api.md) | Paramètres, réponses, exemples de collecte et erreurs HTTP |
| [Modèle du catalogue](docs/catalog-model.md) | Champs communs, mapping Pokémon et ajout d’un TCG |
| [Exploitation](docs/operations.md) | Configuration, Docker, sauvegardes, migrations et dépannage |
| [Acceptation](docs/acceptance.md) | Comportements attendus et tests associés |
| [Décisions](docs/adr/README.md) | Historique des décisions et précisions ultérieures |
| [AGENTS.md](AGENTS.md) | Instructions de travail pour les agents du dépôt |

Pour une première contribution : lire le vocabulaire, choisir le composant dans
la carte du dépôt, puis suivre le guide de contribution et les tests associés.
`docs/superpowers/` conserve les conceptions et plans réalisés ; les guides ci-dessus
décrivent le fonctionnement actuel. Les ADR gardent l’historique des décisions.

Pour une installation antérieure aux blocs, suivre la [mise à jour du modèle](docs/operations.md#mettre-à-jour-le-schéma-ou-le-modèle) :
migration 0005 puis réindexation hors ligne, avant de relancer le worker. Aucune image
n’est retéléchargée ou déplacée pour cette évolution.
