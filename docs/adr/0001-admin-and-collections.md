# ADR 0001 — Admin local, domaines et worker séparé

Statut : accepté pour le périmètre local demandé.

Précisions ultérieures : [0003](0003-card-pages-and-no-prices.md) pour les fiches
et les prix, [0004](0004-local-docker-stack.md) pour l’exécution complète via Compose.
Dans Docker, la publication sur l’hôte reste locale ; l’API écoute toutes les
interfaces à l’intérieur de son conteneur.


Précision ultérieure : [ADR 0006](0006-separated-applications.md) remplace
l’organisation des paquets/imports et l’image commune. Le texte ci-dessous décrit
la décision historique ; les garanties métier et opérationnelles restent valables.

## Décision

- `domain/` : contrat d'impression localisée, demande validée, règles de résultat.
- `application/` : consultation du catalogue et orchestration des collectes ; ports Protocol.
- `infrastructure/` : dépôts SQLAlchemy, exécution subprocess, statistiques Scrapy.
- `interfaces/` : HTTP FastAPI et boucle CLI du worker.
- Spiders/pipelines : adaptateurs d'acquisition. Ils continuent à fonctionner en CLI.
- `storage.py` et `models.py` gardent des imports de compatibilité ; les nouvelles
  implémentations résident dans les couches explicites.

Le catalogue est un modèle de lecture et d'ingestion simple. Pas d'agrégats artificiels
ni de framework de bus d'événements pour encapsuler des opérations CRUD.
Les identités et règles métier restent explicites ; les domaines n'importent ni
FastAPI, ni SQLAlchemy, ni Scrapy. Pydantic décrit leurs contrats de données.

L'API persiste la demande et répond 202. Le worker exécute un processus Scrapy
par collecte, sans shell, avec paramètres typés et spider autorisé. Un verrou de
fichier garantit un seul worker dans le répertoire de jobs local. Tous les processus
doivent partager ce répertoire et la même configuration de base. Ce n'est pas une
file distribuée multi-hôtes. Les demandes queued survivent aux redémarrages ; les
running sont marquées interrupted à la reprise. Une nouvelle demande peut reprendre
la collecte grâce au filtre des cartes déjà enregistrées.

Le worker borne une exécution à une heure et termine son enfant à l'arrêt normal.
Un SIGKILL du worker peut laisser un enfant vivant : vérifier les processus avant
redémarrage dans ce cas. Un ordonnanceur durable distribué avec leases/heartbeats
sera nécessaire avant un déploiement multi-machine. L'API n'exécute jamais les
spiders avec BackgroundTasks.

Les journaux et statistiques sont locaux dans `TCG_JOBS_DIR` ; l'historique et les
paramètres sont en base. Les résultats partiels restent dans le catalogue même si
une collecte échoue. Le log HTTP est limité aux 64 derniers Ko ; l'original complet
reste sur disque. Les snapshots de stats sont écrits à la fin du spider ; les logs
sont consultables pendant l'exécution.

## Interface et exposition

React + TypeScript + React Query ; composants shadcn/ui générés par la CLI officielle,
Vite et Tailwind. FastAPI sert le build en même origine. En développement Vite proxy
`/api` vers FastAPI. Pas de CORS permissif. Host limité, en-tête d'intention admin et
vérification Origin sur les mutations. API et interface liées à 127.0.0.1 seulement.
Pas d'authentification réseau : ne pas exposer ce serveur avant d'ajouter des comptes.

## Validation

Scénarios Gherkin exécutables avec pytest-bdd (ATDD/BDD) sur l'API et une vraie base
SQLite temporaire. TDD par tranches verticales : scénario rouge, implémentation,
refactoring puis suite de non-régression. Tests de composants React sur le formulaire.
Les contrôles navigateur complètent ces tests ; ils ne les remplacent pas.
Les tests historiques sur images et spiders sont conservés lors du refactoring.
