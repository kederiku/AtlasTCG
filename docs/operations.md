# Exploitation locale

## Démarrage et arrêt

Créer `.env` depuis [.env.example](../.env.example) s’il est absent, renseigner le
mot de passe et les UID/GID (`id -u`, `id -g`), puis :

```sh
mkdir -p data/images data/jobs/admin
docker compose up --build -d --wait
docker compose ps --all
```

L’admin est sur `http://127.0.0.1:8000`. `migrate` doit finir avec le code 0 ;
`postgres` et `api` doivent être healthy, `worker` en cours d’exécution.
Le worker n’a pas de sonde indépendante : son log de démarrage et les états de jobs
permettent de confirmer son fonctionnement.

```sh
docker compose logs -f api worker migrate
docker compose logs --tail 100 postgres
```

`make status` affiche les services. `make logs` affiche les 100 dernières lignes
par service applicatif puis se termine ; `make logs-follow` suit les nouveaux
messages jusqu’à Ctrl+C, sans arrêter les services.

Avant un arrêt, une reconstruction ou une maintenance, cesser de soumettre des
demandes et laisser finir la file. L’historique de l’admin ne montre que les 50
dernières demandes ; cette lecture SQL vérifie tous les travaux encore actifs :

```sh
docker compose exec -T postgres sh -c 'psql -U "$POSTGRES_USER" -d "$POSTGRES_DB"' <<'SQL'
SELECT id, status, created_at
FROM collection_jobs
WHERE status IN ('queued', 'running')
ORDER BY created_at;
SQL
```

Quand il n’en reste aucun, `docker compose down` arrête la pile. `stop` et `down`
n’attendent pas la fin d’une collecte : le worker termine son sous-processus et
marque le job `interrupted`. Après un arrêt brutal, ce statut est régularisé au
prochain démarrage. Les résultats partiels sont conservés.

`down` conserve le volume PostgreSQL et le dossier hôte `data/`. Un `down --volumes`
supprime la base : ne l’utiliser que pour une suppression explicitement souhaitée.
Le premier build télécharge les dépendances et Chromium ; les suivants utilisent
le cache. Une modification du code exige `docker compose up --build -d --wait`.
Pour une mise à jour avec migration, suivre la procédure dédiée ci-dessous.

## Configuration

Compose lit `.env` pour substituer les valeurs ; ce fichier n’est ni copié dans
l’image ni intégralement transmis aux conteneurs. Les variables sont explicites.
Sur l’hôte, `make api`, `make worker` et `make migrate` chargent `.env` via uv.
Les autres commandes Python/CLI nécessitent `uv run --env-file .env ...` ou des
variables exportées : l’application ne charge pas `.env` elle-même.

| Variable | Sens / défaut |
|---|---|
| `POSTGRES_DB`, `POSTGRES_USER` | Base/utilisateur, `tcg` |
| `POSTGRES_PASSWORD` | Obligatoire pour Compose |
| `POSTGRES_PORT` | Port publié sur l’hôte, `5432` ; interne toujours `5432` |
| `TCG_UID`, `TCG_GID` | Identité des processus applicatifs, `1000:1000` par défaut |
| `TCG_DATA_DIR` | Répertoire hôte partagé, `./data` |
| `TCG_USER_AGENT` | Identité du collecteur, `TCGCatalog/0.1` |
| `TCG_DATABASE_URL` | Connexion explicite pour le développement hôte ; non transmise par Compose |
| `POSTGRES_HOST` | Connexion structurée si aucune URL explicite ; Compose fixe `postgres` |
| `TCG_IMAGES_DIR` | Chemin applicatif : hôte `data/images`, image Docker `/data/images` |
| `TCG_JOBS_DIR` | Chemin applicatif : hôte `data/jobs/admin`, image Docker `/data/jobs/admin` |
| `TCG_FRONTEND_DIR` | Build servi si configuré ; `make api` fixe `apps/frontend/dist`, Docker `/app/frontend/dist` |

`TCG_DATA_DIR` ne configure que le montage Docker. Sur l’hôte, renseigner
séparément `TCG_IMAGES_DIR` et `TCG_JOBS_DIR` pour des fichiers hors de `data/`.
Dans les images, ces deux chemins sont fixés sous `/data` ; les changer dans le
`.env` de Compose seul ne les remplace pas. Un chemin relatif est résolu depuis
le répertoire de lancement. Si `TCG_DATA_DIR` est personnalisé, préparer ses
sous-dossiers `images/` et `jobs/admin/` avec les bons droits avant `make up`.

L’URL explicite a priorité ; sinon `POSTGRES_HOST` active la construction sûre de
l’URL depuis les paramètres séparés. Sans les deux, le repli est
`sqlite:///data/catalog.db`. Exécuter Alembic sur chaque base utilisée. Docker ne
migre pas les données d’une ancienne base SQLite vers PostgreSQL.

Les identifiants `POSTGRES_*` initialisent seulement un volume vide. Modifier `.env`
ne change pas les identifiants d’un volume déjà initialisé. Avec un mot de passe
contenant `$`, utiliser une valeur entre apostrophes dans `.env` pour éviter
l’interpolation Compose. Pour le développement hôte, encoder les caractères réservés
dans `TCG_DATABASE_URL`. La connexion structurée Docker fait cet encodage elle-même.

Le volume existant conserve son nom de projet Compose. Lancer depuis le même dossier,
avec le même nom de projet ; ne pas renommer la pile sans plan de migration du volume.

## Passer des processus hôte à Docker

1. Laisser finir les collectes en cours et arrêter les anciens `make worker` et
   `make admin` avec Ctrl+C. Ne pas laisser un sous-processus Scrapy orphelin.
2. Conserver `.env`, `data/` et le volume PostgreSQL existants ; vérifier les UID/GID.
3. Exécuter la commande de démarrage complète. Le même catalogue et ses fichiers
   deviennent accessibles dans l’admin Docker.

Le verrou de fichier n’est pas une coordination distribuée entre hôte et conteneur.
Ne pas compter sur lui pour autoriser deux workers concurrents.

## Collecter et actualiser

Le formulaire de l’admin et `POST /api/jobs` enregistrent une demande exécutée par
le worker unique. Utiliser cette [API](api.md#soumettre-et-suivre-une-collecte) pour
piloter les collectes depuis un script et conserver leur historique.

Pour un crawl CLI direct, vérifier d’abord la fin de la file comme décrit plus
haut, puis garder API et worker habituels arrêtés pendant la commande :

```sh
docker compose stop api worker
docker compose run --rm --no-deps worker tcg-scrape crawl tcgdex \
  -a languages=fr,en -a card_ids=base1-4 -a limit=1
# Une fois la commande terminée :
docker compose start api worker
```

La CLI ne prend pas le verrou du worker et ne crée aucun job dans l’admin.
Ne pas lancer ce crawl avec `exec worker` pendant que sa boucle peut prendre une
nouvelle demande. La base doit déjà être démarrée et migrée pour `--no-deps`.

Ajouter `-a force=true` pour relire les cartes et `-s FILES_EXPIRES=0` pour
renouveler aussi les images (cache de 30 jours par défaut). Une carte déjà au contrat
courant, même sans image, est ignorée par défaut ; une ancienne version peut être
recollectée. `limit` borne les premiers candidats de chaque langue, avant le
filtrage des existants, même avec des identifiants explicites. Il ne borne pas le
nombre de nouvelles cartes et ne constitue pas un curseur de progression.
La CLI accepte `-a limit=0` pour tous les candidats ; l’API exige 1 à 10 000.
Sans identifiants explicites, les listes source sont lues pour découvrir les candidats.

Reprise CLI avec `-s JOBDIR=/data/jobs/tcgdex-fr-001` : réutiliser ce dossier seulement
pour reprendre le même crawl. Une actualisation doit avoir un nouveau `JOBDIR`,
sinon le filtre de requêtes Scrapy peut ignorer les URL déjà visitées.

Pour les demandes de l’admin, les statistiques se trouvent dans
`data/jobs/admin/<id>/stats.json` en fin de collecte et le journal dans `crawl.log`.
La CLI affiche ses logs dans le terminal ; pour les conserver, préparer un dossier
dédié et ajouter `-s LOG_FILE=/data/jobs/<crawl>/crawl.log` ainsi que
`-s ADMIN_STATS_PATH=/data/jobs/<crawl>/stats.json`. `JOBDIR` est distinct de ces logs.

Une demande du worker est limitée à une heure. Au dépassement, son processus est
terminé et la demande passe à `failed` ; aucune variable d’environnement n’expose
actuellement cette durée. Les résultats partiels restent en base. Après échec ou
interruption, créer une nouvelle demande adaptée aux cartes restantes ; réutiliser
la même limite ne garantit pas de dépasser les premiers candidats. Les demandes
`queued` survivent au redémarrage. Ces limites et statuts ne sont pas appliqués par
le lanceur CLI direct.

## Sauvegarder

Pour un instantané cohérent, laisser finir les collectes, puis arrêter API et worker
pendant la sauvegarde. Utiliser un nom unique, jamais écraser une sauvegarde précédente.

```sh
docker compose stop api worker
mkdir -p data/backups
backup_stamp=$(date +%Y%m%d-%H%M%S)
docker compose exec -T postgres sh -c 'pg_dump -U "$POSTGRES_USER" -d "$POSTGRES_DB" -Fc' > "data/backups/tcg-$backup_stamp.dump"
tar -czf "data/backups/files-$backup_stamp.tar.gz" -C data images jobs
docker compose start api worker
```

Si `TCG_DATA_DIR` est personnalisé, adapter les chemins hôte de cette procédure.
Conserver le dump et l’archive ensemble. Les sauvegardes historiques peuvent contenir
les anciens champs monétaires ; elles ne sont pas réécrites par la migration 0004.

## Restaurer

Valider d’abord le dump et son archive de fichiers dans une pile séparée. Depuis
la racine du dépôt, dans le même terminal pour toutes les étapes, créer un dossier
de travail hors du dépôt (conservé jusqu’à suppression volontaire) :

```sh
restore_dir=$(mktemp -d "$HOME/tcg-restore.XXXXXX")
restore_project="tcg-restore-$(date +%Y%m%d%H%M%S)-$$"
mkdir -p "$restore_dir/data/images" "$restore_dir/data/jobs/admin"
cat > "$restore_dir/restore.env" <<EOF
POSTGRES_DB=tcg
POSTGRES_USER=tcg
POSTGRES_PASSWORD=choose-a-new-local-restore-password
TCG_UID=$(id -u)
TCG_GID=$(id -g)
TCG_DATA_DIR=$restore_dir/data
EOF
chmod 600 "$restore_dir/restore.env"
cat > "$restore_dir/compose.restore.yaml" <<'YAML'
services:
  postgres:
    ports: !override ["127.0.0.1::5432"]
  api:
    ports: !override ["127.0.0.1::8000"]
YAML
```

Choisir un mot de passe dédié dans `restore.env`. Les ports libres sont attribués
par Docker ; `!override` requiert Compose 2.24.4 ou plus. La fonction suivante cible
toujours ce projet et ces fichiers, en écartant les variables exportées susceptibles
de remplacer ses identifiants ou son dossier de données :

```sh
restore_compose() {
  env -u POSTGRES_DB -u POSTGRES_USER -u POSTGRES_PASSWORD -u POSTGRES_PORT \
    -u TCG_UID -u TCG_GID -u TCG_DATA_DIR \
    docker compose --env-file "$restore_dir/restore.env" \
    -p "$restore_project" -f compose.yaml \
    -f "$restore_dir/compose.restore.yaml" "$@"
}
restore_compose up -d --wait postgres
# Remplacer les deux chemins par le dump et l’archive de la même sauvegarde.
restore_compose exec -T postgres sh -c \
  'pg_restore --exit-on-error --no-owner --no-privileges -U "$POSTGRES_USER" -d "$POSTGRES_DB"' \
  < chemin/vers/tcg.dump
tar -xzf chemin/vers/files.tar.gz -C "$restore_dir/data"
restore_compose run --rm migrate
restore_compose up -d --wait api
restore_compose port api 8000
```

Utiliser l’adresse renvoyée pour consulter l’API et le frontend. Vérifier total,
fiche, WebP et historique. Garder le worker de restauration arrêté : les demandes
`queued` du dump seraient exécutées dès son démarrage. Le port temporaire n’est
pas autorisé pour les mutations depuis le navigateur ; cette vérification est
une consultation, pas une nouvelle installation opérationnelle.

Le dump inclut la version Alembic ; les migrations l’amènent au schéma actuel,
dont l’exclusion des prix. Les options `--no-owner --no-privileges` attribuent les
objets au compte de la pile de vérification, sans restaurer les anciens droits.
Si les images locales n’existent pas encore, construire les trois cibles avant
cette procédure. Ne pas poursuivre si une commande de restauration échoue.

`restore_compose down` arrête uniquement cette pile et conserve ses données.
Noter la valeur de `restore_project` et le chemin `restore_dir` avant de fermer
le terminal ; conserver ses fichiers de configuration et le dump pour retrouver
cette vérification. Remplacer la base habituelle reste une opération
distincte, à préparer avec sauvegarde et arrêt des collectes ; ne jamais injecter
le dump dans une base déjà remplie avec les commandes ci-dessus.

## Mettre à jour le schéma ou le modèle

Laisser finir les collectes, sauvegarder, puis :

```sh
docker compose stop api worker
docker compose build
docker compose run --rm migrate
```

Garder API et worker arrêtés pendant les éventuelles migrations de données ci-dessous.
Alembic ne réindexe pas automatiquement les anciennes observations enrichies :

```sh
docker compose run --rm --no-deps worker tcg-reindex
# Après vérification de l’aperçu, si des observations sont à mettre à jour :
docker compose run --rm --no-deps worker tcg-reindex --apply
```

Cette reconstruction hors ligne utilise `raw`, préserve images/dates/identités et
ignore les projections déjà à jour. Les observations invalides sont signalées.
Les scripts ne doivent pas modifier les migrations existantes.

Migration des anciens chemins d’image, également avec aperçu :

```sh
docker compose run --rm --no-deps migrate tcg-migrate-images
docker compose run --rm --no-deps migrate tcg-migrate-images --apply
```

Les originaux restent conservés, les conflits de contenu sont refusés, l’opération
est relançable. Après réussite des opérations nécessaires, redémarrer :

```sh
docker compose up -d --wait api worker
```

## Dépannage

| Symptôme | Vérification |
|---|---|
| Port 8000 occupé | Arrêter l’ancienne API hôte avant le lancement Docker. |
| Port 5432 occupé | Modifier `POSTGRES_PORT` et l’URL hôte ; le port interne reste 5432. |
| `Permission denied` sur `/data` | Vérifier `TCG_UID`, `TCG_GID` et les droits du dossier hôte ; ne pas utiliser `chmod 777`. |
| `migrate` échoue | Consulter ses logs et la connexion PostgreSQL ; API/worker attendent sa réussite. |
| Demande bloquée en attente | Vérifier `docker compose logs worker`, sa base et son dossier partagé. |
| Rien de nouveau téléchargé | Contrôler `cards/skipped_existing`, limite et `JOBDIR` avant de forcer. |
| Images absentes | Distinguer absence à la source et échec de téléchargement ; consulter les logs/statistiques. |
| API unhealthy | Vérifier `/api/health`, PostgreSQL et les migrations ; la sonde exige un catalogue accessible. |
| `/api/health` fonctionne mais `/` retourne 404 | Sans build configuré, l’API seule est normale ; sur l’hôte, faire `make build` puis `make api`. |
| Collecte refusée avec 403 | Vérifier `X-TCG-Admin: 1` et l’origine navigateur ; voir la référence API. |
| Ancien frontend ou ancien comportement | Les images contiennent le code construit ; attendre la fin des collectes puis reconstruire et recréer les services. |

Les logs Docker sont limités par rotation. Les fichiers `crawl.log` ne sont pas
purgés automatiquement : gérer leur conservation après sauvegarde si le catalogue
grandit. Les 404 d’un fournisseur sont visibles dans les logs ; le statut réussi
n’est pas une garantie d’exhaustivité de ses données.

## Références

- [Ordre de démarrage Compose](https://docs.docker.com/compose/how-tos/startup-order/).
- [Installation uv dans Docker](https://docs.astral.sh/uv/guides/integration/docker/).
- [Playwright et dépendances Docker](https://playwright.dev/python/docs/docker).

## Passage au contrat v2 avec blocs

Après sauvegarde et fin des collectes, garder API/worker arrêtés pendant la migration
et la réindexation pour éviter une recollecte des anciennes versions :

```sh
docker compose stop api worker
docker compose build
docker compose run --rm migrate
docker compose run --rm --no-deps worker tcg-reindex
docker compose run --rm --no-deps worker tcg-reindex --apply
docker compose up -d --wait api worker
```

La migration 0005 reconstruit les blocs depuis `series_id`/`series_name` ou les données
de série présentes dans les sets. Aucun bloc n’est deviné pour les références
absentes. L’admin affiche immédiatement les blocs connus ; un prochain crawl d’un
set pourra enrichir le détail de son bloc. Le chemin des WebP reste inchangé.

## Images et commandes après séparation des applications

| Service | Image | Contenu |
|---|---|---|
| `api` | `tcg-api:local` | FastAPI/Uvicorn, core, persistence, frontend compilé |
| `worker` | `tcg-scraping:local` | Scrapy, Playwright/Chromium, core, persistence |
| `migrate` | `tcg-migrate:local` | core, persistence et historique Alembic |

Les noms de services, le volume PostgreSQL, les montages et les variables de connexion
restent compatibles. Construire les trois images avec `docker compose build` avant
une bascule ; la procédure de sauvegarde et de fin des collectes reste nécessaire.
Les imports internes historiques `tcg_catalog.*` sont remplacés ; les commandes
ci-dessus constituent les points d’entrée documentés. Aucun déplacement des fichiers
utilisateurs ni nouvelle version de schéma n’est requis par cette réorganisation.
