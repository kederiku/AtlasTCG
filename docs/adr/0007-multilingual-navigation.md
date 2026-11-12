# ADR 0007 — Navigation commune et interface multilingue

Statut : accepté le 12 novembre 2026. Précise les ADR 0002, 0003 et 0005 sans
remplacer les identités localisées ni les URLs des fiches.

## Problème

Utiliser la langue des cartes pour nommer blocs/extensions change les repères de
navigation. Une grille d’impressions répète chaque carte lorsque plusieurs langues
sont collectées. L’interface était uniquement française.

## Décision

Séparer la langue d’interface (`fr`, `en`, `es`) de la langue des cartes et des
langues de collecte. La préférence d’interface reste locale au navigateur, française
par défaut, sans compte utilisateur. Les dictionnaires TypeScript ont les mêmes
clés et couvrent les textes applicatifs ; les contenus source ne sont pas traduits.

Les blocs/extensions sont regroupés en lecture par `(game, source, source_id)`.
Leur nom suit la langue d’interface, avec repli français, anglais, puis premier code
de langue trié, enfin identifiant. Changer la langue des cartes conserve la sélection
d’extension. Les noms connus dans les différentes langues servent à la recherche.

`GET /api/card-groups` pagine les groupes de cartes partageant cette même identité
sans langue. Chaque groupe porte une impression représentative et toutes ses
versions collectées. Les filtres déterminent les impressions admissibles ; le cas
d’usage choisit parmi elles selon la langue d’interface et le repli ci-dessus.
Les langues régionales restent des versions distinctes. La pagination et son total
portent sur les groupes, avec un ordre stable indépendant de l’interface.

Les routes existantes d’impressions sont conservées. Le détail expose aussi les
résumés des versions pour naviguer entre les URLs localisées. Les images HTTP sont
construites dans l’API ; aucun accès HTTP, SQL ou fichier n’entre dans core.

## Conséquences et limites

Aucune migration ni réindexation : les observations, métadonnées, fichiers et dates
restent inchangés. Ce regroupement de lecture n’est pas une fusion persistée, un
rapprochement inter-sources, ni une équivalence déduite d’un nom ou numéro de carte.
Des éditions à codes différents restent distinctes. Les correspondances dépendent
des identifiants de la source ; les traductions absentes ne sont pas inventées.
Les métadonnées propres aux différentes impressions restent consultables.

Les résultats de recherche groupée peuvent correspondre à une autre traduction
que l’impression affichée. Le filtre de langue des cartes reste contraignant.
La statistique de stockage compte toujours les impressions ; le résultat de
navigation compte les cartes regroupées. Les journaux et diagnostics source restent
dans leur langue d’origine.

## Validation

BDD via l’API FR/ES ; pagination, caractères littéraux et collisions de jeu/source
sur base temporaire ; tests React de préférence, noms, filtres, versions et collecte
FR/EN/ES ; parcours navigateur et tests d’installations et de pile PostgreSQL isolée.
