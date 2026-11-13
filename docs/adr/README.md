# Décisions d’architecture

Les ADR conservent l’historique du raisonnement. Une décision ultérieure précise
ou remplace explicitement une décision antérieure ; ne pas réécrire le passé comme
si la contrainte avait toujours existé.

| ADR | Décision | État actuel |
|---|---|---|
| [0001](0001-admin-and-collections.md) | Admin local, contextes et worker séparé | Précisé par 0004 et 0006 ; organisation/imports remplacés par 0006 |
| [0002](0002-rich-multigame-catalog.md) | Extensions localisées et contrat de règles versionné | Maintenu ; `raw` limité par 0003, blocs ajoutés par 0005 |
| [0003](0003-card-pages-and-no-prices.md) | Fiches par URL et exclusion des prix | Maintenu |
| [0004](0004-local-docker-stack.md) | Pile Docker complète et données persistantes | Image commune remplacée par 0006 ; garanties opérationnelles maintenues |
| [0005](0005-localized-blocks.md) | Blocs localisés facultatifs, relations et filtre | Maintenu |
| [0006](0006-separated-applications.md) | Applications, dépendances et images séparées | Maintenu |
| [0007](0007-multilingual-navigation.md) | Navigation regroupée et langue d’interface indépendante | Précise 0002, 0003 et 0005 ; stockage localisé maintenu |
| [0008](0008-image-repair.md) | Réparation des médias sur les impressions existantes | Précise 0001, 0003 et 0006 ; observations et dates préservées |
| [0009](0009-scoped-collections.md) | Choix distants et collecte complète par bloc ou extension | Complète 0001, 0005, 0006 et 0007 ; demandes historiques conservées |

Un nouvel ADR indique le problème, la décision, ses conséquences/limites et la
validation attendue. Les règles opérationnelles courantes sont dans
[le guide d’exploitation](../operations.md), les règles de développement dans
[engineering.md](../engineering.md).
