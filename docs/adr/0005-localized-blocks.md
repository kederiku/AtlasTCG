# ADR 0005 — Blocs localisés et rattachement des extensions

Statut : accepté. Étend le modèle de l’ADR 0002 ; le bloc reste facultatif.

## Problème

Pokémon regroupe ses extensions en blocs, appelés `series` dans TCGdex. Les anciens
champs `series_id`/`series_name` dans le JSON de set conservaient cette information,
mais sans entité, intégrité référentielle ni navigation par bloc.

## Décision

Introduire `LocalizedBlock`, `BlockInfo` et `BlockReference`. Un bloc est un
regroupement d’extensions fourni par une source pour un jeu et une langue. Son
identité est `(game, source, source_id, language)`, comme celle des extensions.
Son nom est localisé ; son code reste stable. `localized_sets.block_id` référence
`localized_blocks` par une clé étrangère composite nullable, avec index.

Le contrat v2 expose `SetInfo.block = {id, name} | null`. Les anciennes clés
`series_id`/`series_name` restent acceptées à l’entrée pour normaliser les anciens
documents ; elles ne sont plus le contrat de sortie. Les résumés de carte exposent
également `block_id` et `block_name`. Les noms publics sont lus depuis la table
canonique des blocs pour éviter les copies obsolètes dans les résumés de set.

Un résumé d’extension crée un bloc partiel si nécessaire. Le détail du bloc fait
autorité sur son nom/logo ; un résumé ultérieur ne l’efface pas. La relation est
optionnelle : pas de bloc inventé depuis un préfixe de set ou un nom. Le modèle
n’impose pas cette organisation à tous les TCG.

TCGdex mappe `set.serie` vers la référence et récupère `/series/{id}` une fois par
langue et par crawl après le détail d’un set. Les logos restent des URL de métadonnées ;
ils ne sont pas rangés comme des images de carte. Les données de bloc sont également
filtrées par la politique sans prix.

## Migration et exploitation

Alembic 0005 reconstruit les blocs depuis les métadonnées de sets existantes, par
lots, sans réseau. Les cartes, dates et images restent inchangées. Le contrat étant
passé en version 2, exécuter la réindexation hors ligne avant de relancer le worker
pour conserver le bénéfice de l’évitement des cartes déjà collectées.

La structure des images reste `<jeu>/<langue>/<set>/<numéro>-<set>.webp` : le bloc
n’entre ni dans leur chemin ni dans l’identité des cartes. Un changement de
rattachement ne déplace donc aucun fichier. Un downgrade retire la table des blocs
et perd ses métadonnées détaillées ; les références des sets redeviennent les
anciens champs de série. Préférer une restauration préparée si nécessaire.

## API et interface

`GET /api/blocks` expose les blocs localisés. `/api/overview` expose leurs facettes
sans charger leurs réponses brutes. `/api/cards?block_id=...` filtre via la relation
extension/bloc, combinable avec jeu, source, langue et extension. Toujours préciser
jeu et source pour cibler un bloc unique ; un code seul recherche dans tous les jeux.

L’admin conserve le filtre dans l’URL, le rétablit après rechargement et le retour
d’une fiche, et réinitialise les filtres enfants lorsqu’un parent change. Le bloc
sur la fiche est un lien vers ses cartes. Le catalogue reste utilisable sans bloc.

## Limites et validation

Une extension a au plus un bloc par source/langue. Pas de hiérarchie de blocs ni
regroupement inter-sources sans besoin vérifié. Les noms traduits ne créent pas de
fusion entre langues. Les autres TCG restent des contrats possibles, pas des
connecteurs implémentés.

Tests : filtrage API multi-jeux/langues, migration de plusieurs lots avec conservation
des observations, métadonnées partielles/complètes, découverte Scrapy dédupliquée,
pipeline réel sur HTTP local, navigation React et parcours Docker/PostgreSQL.

Référence : [séries TCGdex](https://tcgdex.dev/rest/serie) et
[rattachement des sets](https://tcgdex.dev/rest/set).
