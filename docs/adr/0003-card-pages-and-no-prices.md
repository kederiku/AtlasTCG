# 0003 — Fiches navigables et exclusion des prix

Statut : accepté. Précise la conservation des données décrite par l'ADR 0002.

L’exécution et les procédures de migration actuelles sont précisées par
[l’ADR 0004](0004-local-docker-stack.md) et [le guide d’exploitation](../operations.md).

## Décision

La fiche d'une impression localisée est une page
`/cards/:game/:source/:language/:sourceId`. Son identité ne dépend pas de l'état
du catalogue. React Router gère les liens et l'historique ; FastAPI sert le point
d'entrée HTML sur ces routes et sur `/collections`. Les routes API et fichiers
manquants continuent de répondre 404. Les filtres et la page du catalogue sont
dans l'URL ; le lien de retour les conserve.

Les prix ne sont pas un besoin métier. La conservation intégrale de `raw` prévue
dans l'ADR 0002 comporte désormais cette exception : les champs monétaires sont
retirés récursivement à l'import. La validation du domaine applique la même
politique aux cartes et aux extensions, indépendamment du connecteur. Les coûts
de jeu et les identifiants tiers restent conservés.

La migration 0004 applique une copie figée de la politique aux documents JSON
existants, par lots ordonnés par clé primaire. Elle ne modifie ni les images, ni les
identités, ni les dates. Une migration inverse ne peut pas recréer des données
supprimées. Une sauvegarde antérieure reste historique : après restauration,
appliquer les migrations avant de relancer les collectes.

## Vérification

Tests des URL directes et des erreurs, navigation frontend, import de prix imbriqués,
conservation des coûts de jeu et migration de plus d'un lot de données existantes.
