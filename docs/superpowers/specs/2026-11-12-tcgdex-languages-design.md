# Langues TCGdex

## Intention et portée retenue

Rendre sélectionnables les 18 codes TCGdex : `en`, `fr`, `es`, `es-mx`, `it`,
`pt`, `pt-br`, `pt-pt`, `de`, `nl`, `pl`, `ru`, `ja`, `ko`, `zh-tw`, `id`, `th`,
`zh-cn`. Conserver français et anglais cochés par défaut, conformément au choix
de l’utilisateur. Une langue acceptée ne garantit pas la disponibilité de chaque
carte chez le fournisseur.

## Approches

- Compléter séparément les listes du formulaire et de l’API serait plus court,
  mais conserverait la cause de leur divergence actuelle (6 contre 11 langues).
- Alimenter le formulaire depuis le registre exposé par `GET /api/spiders`
  fournit une seule liste de capacités. C’est l’approche proposée et retenue.

## Conception

Le registre de core déclare les 18 codes ; la demande autorise leur sélection
simultanée et continue de rejeter les codes inconnus. Le formulaire charge ce
registre via les outils HTTP/React Query existants, présente des libellés français
et empêche la soumission tant que les capacités sont indisponibles. Un échec de
chargement est visible et permet une nouvelle tentative.

Le spider construit déjà les routes avec le code complet. Les identités, chemins
d’image, données et dates existants restent inchangés : aucune fusion entre `pt`,
`pt-br`, `pt-pt`, ni entre les autres variantes. Pas de migration, de dépendance
ajoutée, de collecte réelle ou de changement de sélection par défaut.

## Acceptation

- Étant donné le connecteur TCGdex, quand je consulte ses capacités puis soumets
  les 18 langues, alors la demande est enregistrée en attente avec les 18 codes.
- Étant donné le formulaire ouvert, alors les 18 langues du registre sont
  sélectionnables et seuls `fr` et `en` sont cochés initialement.
- Quand je choisis des variantes régionales, alors la soumission et les requêtes
  du spider conservent les codes complets.
- Quand le registre ne peut pas être chargé, alors le formulaire explique le
  problème et ne soumet aucune demande ; une nouvelle tentative reste possible.

## Vérification

Tests d’acceptation/API, tests React et test du spider avec données locales ;
boucles rouge/vert, puis `make test` et parcours navigateur dans un environnement
temporaire sans worker. Mettre à jour la référence API, le contrat d’acceptation
et les consignes d’ajout de source.

## Référence source

[Types officiels TCGdex](https://github.com/tcgdex/cards-database/blob/master/interfaces.d.ts)
consultés le 12 novembre 2026 : les 18 codes figurent dans `SupportedLanguages`.
