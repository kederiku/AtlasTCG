# Modèle du catalogue

Vocabulaire : [CONTEXT.md](../CONTEXT.md). Invariants transverses :
[règles du projet](engineering.md). La structure décrite ici est commune aux modes
hôte et Docker ; seul le stockage local des fichiers est monté différemment.

## Structure

La structure ci-dessous est celle des observations conservées. Pour naviguer,
l’interface regroupe blocs, extensions et cartes par jeu/source/identifiant sans
langue, puis donne accès aux impressions localisées. Ce modèle de lecture ne
fusionne aucune observation. Voir [l’ADR 0007](adr/0007-multilingual-navigation.md).

```text
Bloc localisé facultatif (jeu, source, code, langue)
  nom, logo, réponse source hors prix
  └── Extension localisée (jeu, source, code, langue)
        nom, date, nombres de cartes, logo, symbole, source brute
        └── Impression localisée (jeu, source, identifiant, langue)
              numéro, rareté, illustrateurs, légalité, images
              ├── Face(s) : nom, types, traits, textes, statistiques,
              │            coûts nommés, capacités et attaques
              ├── game_data.<jeu> : spécificités structurées
              └── raw : payload source hors données monétaires
```

## Mapping Pokémon réellement implémenté

| Source TCGdex | Catalogue |
|---|---|
| `set.name`, `set.id` | nom localisé et code d'extension distincts |
| détail de set `serie` | référence de bloc localisé `set_info.block` et relation SQL |
| détail de bloc `/series/{id}` | nom, logo et données source du bloc |
| détail de set `releaseDate`, `cardCount` | date, nombres de cartes |
| `illustrator`, `rarity` | `illustrators`, `rarity` |
| `hp` | `faces[0].statistics.hp` |
| `category`, `types`, `stage`, `suffix`, `trainerType`, `energyType` | types et traits de la face |
| `effect`, `description` | textes de règles et d'ambiance séparés |
| `attacks`, `abilities` | capacités typées attaque/capacité, avec textes et coûts |
| `retreat` | coût de retraite (0 est conservé) |
| `legal` | statut par format, sans assimiler « non légal » à « banni » |
| `weaknesses`, `resistances`, `evolveFrom`, `dexId` | données Pokémon structurées |
| `regulationMark`, `variants`, `variants_detailed` | données Pokémon structurées |
| `thirdParty`, `updated` | identifiants externes et date source conservés sous Pokémon |
| `pricing`, `prices`, évaluations monétaires | exclus, également dans les variantes et `raw` |
| autres champs, dont les futurs | `raw` conservé et consultable, après exclusion des champs monétaires reconnus |

Les prix ne font pas partie du catalogue. La politique du domaine
`packages/core/src/tcg_core/catalog/retention.py` retire récursivement les champs monétaires reconnus à l'import,
avant persistance. Elle conserve les coûts de jeu (énergie, mana, retraite), les
textes imprimés et les identifiants externes. Chaque nouvelle source doit fournir
des exemples de ses éventuels champs monétaires pour compléter cette politique.

Les variantes TCGdex restent des données de `game_data.pokemon`. Elles ne créent
pas automatiquement plusieurs impressions ni plusieurs fichiers d’image. Le
catalogue conserve la dernière observation, pas l’historique complet de ses versions.

## Versions et observations

`CATALOG_VERSION` vaut actuellement `2`. Chaque carte porte `schema_version` ; cette
version de projection métier est distincte de la révision Alembic du schéma SQL.
Une migration de tables n’actualise pas nécessairement les projections des cartes.
La réindexation reconstruit celles d’une ancienne version depuis leur `raw` conservé,
sans réseau et sans changer identité, provenance, images ou `updated_at`.

Une collecte normale ignore les impressions dont `schema_version` est au moins la
version courante, même sans image locale. Les anciennes projections sont éligibles
à une nouvelle collecte sans `force`. Réindexer avant de relancer le worker permet
d’éviter cette recollecte lorsqu’une reconstruction hors ligne suffit.

Pour une extension partielle, les champs non nuls reçus remplacent leurs équivalents,
les champs absents/nuls conservent les valeurs existantes, et `raw` est fusionné
avec priorité aux clés entrantes. Pour un bloc partiel, les valeurs existantes
non nulles et les anciennes clés `raw` priment. Un détail complet fait autorité.
Cette distinction préserve les métadonnées omises par les résumés sans promettre
que tout résumé d’extension est ignoré après la réception d’un détail.

## Extension à d'autres TCG

Le schéma accepte les jeux `magic`, `one-piece`, `naruto`, `yugioh`, `cyberpunk`,
`altered`, `riftbound`, comme tout nouveau code stable. Cela ne signifie pas que
leurs données ont été collectées. Le test multi-jeux vérifie la capacité du contrat
à stocker plusieurs faces, des statistiques symboliques et des coûts différents.

Pour chaque future source :

1. Identifier précisément le jeu/édition (notamment Naruto et Cyberpunk), la source,
   ses langues, sa licence et ses identifiants d'impressions/variantes.
2. Ajouter des fixtures de vraies réponses et des critères d'acceptation sur leur mapping.
3. Écrire un adaptateur pur vers `Card`, `LocalizedSet` et, si la source en fournit,
   `LocalizedBlock` ; préserver `raw` hors prix.
4. Réutiliser les champs communs seulement si leur sens correspond. Les mécaniques
   spécifiques vont sous `game_data.<jeu>`, les statistiques dans des clés stables.
5. Ajouter le spider, le registre et la validation des collectes autorisées, puis
   adapter le formulaire et la réindexation si nécessaire ([guide de contribution](../CONTRIBUTING.md#ajouter-une-source)).
6. Vérifier noms de set, langues, faces, variantes, absence vs zéro et stabilité d'identité.

Ne pas forcer des cartes non-Pokémon à avoir des PV, de l'énergie ou des attaques.
Ne pas reconstruire le texte imprimé depuis une valeur calculée ou une traduction.
Si une nouvelle normalisation modifie le contrat, incrémenter `CATALOG_VERSION`,
ajouter un test de migration/réindexation et conserver la compatibilité documentée.

Les procédures de réindexation, migration d’images et sauvegarde sont dans
[le guide d’exploitation](operations.md). Les anciennes sauvegardes doivent être
migrées après restauration avant d’être remises en service.

## Blocs et contrat v2

Un bloc appartient à un jeu, une source et une langue. Une extension peut être sans
bloc ; ne pas en créer un artificiellement pour uniformiser un TCG qui n’en a pas.
`SetInfo.block` porte `{id, name}` ou `null`. Les noms renvoyés sont ceux de la table
`localized_blocks`. La FK composite interdit un rattachement dans une autre langue
ou une autre source. Les images restent organisées par set, sans dossier de bloc.

La migration 0005 récupère les anciennes métadonnées de série. La réindexation hors
ligne met les cartes au contrat v2 sans accès réseau et préserve dates et images.
Voir [l’ADR 0005](adr/0005-localized-blocks.md).

## Emplacement du modèle et des connecteurs

Les contrats communs résident dans `packages/core/src/tcg_core/catalog/models.py`.
Le mapping TCGdex réside dans `apps/scraping/src/tcg_scraping/sources/tcgdex/normalize.py` ;
le spider voisin appelle ce mapping, mais la normalisation ne dépend pas de Scrapy.
La réindexation compose le même adaptateur avec le cas d’usage de core. Les tables
et transactions sont définies dans `packages/persistence/src/tcg_persistence/`.
