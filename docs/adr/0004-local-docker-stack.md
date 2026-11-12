# ADR 0004 — Pile locale complète avec Docker Compose

Statut : accepté. Précise le mode d’exécution local de l’ADR 0001.


Précision ultérieure : [ADR 0006](0006-separated-applications.md) remplace
l’organisation des paquets/imports et l’image commune. Le texte ci-dessous décrit
la décision historique ; les garanties métier et opérationnelles restent valables.

## Problème

PostgreSQL tournait seul dans Docker ; Python/uv, le build Node et le worker devaient
être démarrés séparément sur l’hôte. Une installation complète devait pouvoir être
lancée avec une seule commande, sans déplacer les données existantes.

## Décision

Une image applicative commune construit React avec Node 24, installe Python 3.14.7
et les dépendances verrouillées avec uv 0.12.5, puis installe Chromium et ses
bibliothèques système. Le runtime sert le build via FastAPI ; Node reste dans le
stage de build. L’installation Python est non éditable, avec chemin du frontend
explicite. Les processus applicatifs sont non root.

Compose garde le service PostgreSQL et son volume. Il ajoute `migrate` (Alembic,
exécution unique), `api` et `worker`. Les dépendances attendent PostgreSQL sain et
la réussite des migrations. L’API dispose d’une sonde légère de disponibilité SQL.
Le worker reste unique avec son verrou et son timeout existants.

Le dossier hôte `data/` est partagé sous `/data`, avec UID/GID configurables.
Les images et jobs actuels restent à leur place. Une connexion interne structurée
sur `postgres:5432` évite d’utiliser l’URL `127.0.0.1` de l’hôte et encode correctement
les identifiants. La résolution de connexion est partagée par tous les points d’entrée.

Les ports publiés restent attachés à la boucle locale. L’écoute `0.0.0.0` dans le
conteneur est nécessaire au port Docker et ne transforme pas l’admin en service réseau.
Aucune authentification distante ni orchestration multi-hôtes n’est ajoutée.

## Conséquences

- Docker seul suffit pour utiliser l’application ; le mode hôte reste disponible
  pour développer avec Vite et uv.
- Le changement de code exige un rebuild. Une migration structurelle se fait avec
  API/worker arrêtés après fin des collectes et sauvegarde.
- Ne pas faire tourner le worker hôte et celui de Docker simultanément.
- La même image contient Chromium pour l’API et le worker : simplicité privilégiée
  pour ce projet local, au prix d’une image plus grande.
- Les lockfiles figent les bibliothèques ; les tags système de Node/PostgreSQL peuvent
  recevoir des corrections. Le build n’est pas présenté comme reproductible bit à bit.

## Validation

Un test de pile dans un projet Compose unique vérifie migrations PostgreSQL, API,
lien direct de carte, WebP, collecte d’une carte déjà enregistrée, démarrage Chromium
et conservation des données après redémarrage. Il ne dépend pas de TCGdex et supprime
uniquement ses propres ressources temporaires. La CI exécute également ce test.
