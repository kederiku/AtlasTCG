# Langage du domaine

Deux contextes : **Catalogue** et **Collectes**. Aucun nom de carte ne sert d'identité.

| Terme | Sens canonique |
|---|---|
| TCG / jeu | Jeu auquel une carte appartient, code stable (`pokemon`). |
| Bloc / série | Regroupement optionnel d’extensions fourni par une source ; code stable et nom localisé. |
| Set / extension | Édition identifiée par son code dans une source (`base1`). |
| Impression localisée | Carte d'un set, dans une langue, identifiée par `(game, source, source_id, language)`. |
| Numéro de collection | Chaîne imprimée dans l'extension ; conserver lettres et zéros initiaux. |
| Source | Fournisseur des observations et images, distinct du jeu. |
| Observation | Dernières informations validées pour une impression ; `raw` conserve la réponse source hors prix. |
| Asset / image | Fichier WebP local associé à une impression, éventuellement plusieurs faces. |
| Demande de collecte | Paramètres validés, enregistrés avant toute exécution. |
| Périmètre de collecte | Bloc entier ou extension identifiée dans la source, parcouru dans les langues demandées sans limite de candidats. Les choix distants ne sont pas des observations du catalogue. |
| Réparation des images | Demande portant sur les impressions existantes : compléter leurs WebP manquants, avec recherche d’URL TCGdex si nécessaire, sans remplacer leurs observations. |
| Collecte / job | Exécution d'une demande : queued → running → succeeded ou failed. Une interruption devient interrupted. |
| Worker | Processus unique qui exécute séquentiellement les demandes en attente, sur l’hôte ou dans Docker. |

Invariants : pas de fusion entre langues ou sources ; pas de SQL dans le domaine ;
pas de commande shell issue du frontend ; ne pas considérer un code de sortie zéro
comme une collecte réussie sans examiner les statistiques Scrapy.
Les prix ne font pas partie du domaine : les champs monétaires reconnus sont retirés
récursivement, y compris des variantes. Les coûts de jeu et identifiants tiers restent.

## Catalogue enrichi

- **Bloc localisé** : entité dans `localized_blocks`, identité
  `(game, source, source_id, language)`. Aucune déduction depuis le code d’un set.
- **Extension localisée** : entité distincte dans `localized_sets`, identité
  `(game, source, source_id, language)`, nom traduisible, code stable, rattachement facultatif à un bloc de la même source/langue.
- **Face** : surface logique d'une carte ; ne suppose pas une seule face par impression.
- **Texte** : bloc classé (règles, ambiance, rappel), conservé dans sa langue source.
- **Coût** : symboles/valeur/texte, sans équivalence automatique entre jeux.
- **Capacité** : action ou règle nommée, éventuellement une attaque avec dégâts/coût.
- **Normalisation** : projection versionnée de `raw` vers le contrat commun.
- **Réindexation** : reconstruction hors ligne de cette projection, sans changer la
  provenance, les images ni la date d'observation.

## Périmètre actuel

La **carte de navigation** est un regroupement de lecture des impressions partageant
`(game, source, source_id)` : une vignette, plusieurs langues accessibles. Elle ne
remplace pas leur identité localisée. Blocs et extensions ont aussi une seule entrée
de navigation par identité sans langue. La **langue d’interface** (FR/EN/ES) détermine
les libellés et noms de navigation ; la **langue des cartes** filtre les impressions.
Les langues d’une demande de collecte constituent un troisième choix indépendant.

Pokémon/TCGdex est le seul connecteur réel. Les autres TCG sont prévus par le contrat,
sans collecte implémentée. L’admin reste local, sans comptes utilisateurs. Une fiche
est une page identifiée par jeu/source/langue/identifiant ; le catalogue conserve ses
filtres dans l’URL.

Le code distingue `apps/frontend`, `apps/api`, `apps/scraping`, le métier partagé
`packages/core` et le stockage `packages/persistence`. Compose lance PostgreSQL,
une migration préalable, l’API avec le frontend compilé et le worker, depuis trois
images applicatives distinctes. Les images et journaux restent dans un dossier partagé persistant.
Il s’agit d’une seule installation locale, pas d’une collecte distribuée.

Voir [le modèle](docs/catalog-model.md), [les règles](docs/engineering.md) et
[les ADR](docs/adr/README.md) pour les garanties et limites.
