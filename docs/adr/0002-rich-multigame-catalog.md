# ADR 0002 — Extensions localisées et documents de règles versionnés

Statut : retenu pour le catalogue local, novembre 2026.

Précision ultérieure : [l’ADR 0003](0003-card-pages-and-no-prices.md) exclut les prix
de `raw` et de tous les documents normalisés. La conservation intégrale décrite dans
la décision initiale ci-dessous comporte désormais cette exception.

## Problème

Les payloads complets étaient stockés dans `raw`, mais le modèle public ne portait
que l'identité et les images. `base1` était affiché comme un nom et les règles de
jeu n'étaient pas consultables sans lire le JSON source. Une colonne SQL par
particularité de jeu produirait rapidement un schéma clairsemé et couplé à Pokémon.

## Décisions

**Identité relationnelle.** Une extension localisée est identifiée par
`(game, source, source_id, language)` dans `localized_sets`. La carte conserve son
identité de source et référence son extension par une clé étrangère composite.
Le code de l'extension ne change jamais selon sa traduction. Une source peut nommer
une extension différemment d'une autre : pas de fusion par nom. Les images restent
rangées par codes stables, pas par noms traduits.

**Contrat de règles.** Le domaine définit des Value Objects Pydantic stricts
(`extra=forbid`) : `CardFace`, `ResourceCost`, `Ability`, `TextBlock`, `SetInfo`.
La carte porte rareté et illustrateurs ; les faces portent textes, traits, statistiques,
capacités et coûts. Les statistiques peuvent être numériques ou symboliques (`*`,
`100+`). Un coût absent n'est pas un coût nul. Les symboles répétés sont conservés
sans calculer un équivalent arbitraire entre jeux. Chaque face peut référencer un
index d'image. Le catalogue décrit les cartes, il n'interprète pas les règles.

**Persistance hybride.** Identités, noms, rareté, dates et clés sont relationnels ;
les documents validés sont en JSONB PostgreSQL (JSON SQLite pour les tests).
`game_data` contient les extensions nommées par jeu ; `raw` conserve intégralement
la réponse source, y compris les champs encore inconnus. Les noms de statistiques
sont stables par adaptateur et documentés ; ne pas traduire leurs clés selon la langue.
Les index existants et l'index composite du set servent la navigation. Ajouter des
index JSONB ciblés uniquement à partir de requêtes réelles et mesures de performance.

**Adaptateur anti-corruption.** `adapters/tcgdex.py` est une fonction pure qui
transforme une réponse source en contrat de domaine ; il ne connaît ni Scrapy, ni
SQL, ni HTTP. Le spider gère seulement requêtes, découverte et callbacks. Il collecte
le détail de chaque set une fois par langue dans un crawl qui observe ses cartes.
Un résumé de set embarqué dans une carte ne doit pas effacer une date/série déjà
obtenue depuis le détail du set. La sauvegarde carte + extension est transactionnelle.

**Migration sans réseau.** Alembic 0003 crée le stockage et les références ; les
anciens enregistrements restent en version 0. Le cas d'usage `reindex` reconstruit
les documents depuis `raw`, par lots, de façon idempotente. Il garde images, identité,
réponse brute et date de collecte. Les observations invalides sont comptées et restent
anciennes ; aucun résultat n'est inventé. Le middleware de doublons ne bloque plus
les anciennes versions, qui peuvent donc être recollectées. La migration de schéma
reste figée et n'importe pas les adaptateurs applicatifs évolutifs.

**API et frontend.** Schémas de réponse FastAPI explicites. La liste expose un résumé,
la fiche complète est chargée via `/api/cards/detail`. `/api/sets` expose les sets
localisés ; les filtres sont délimités par jeu/source/code. L'admin affiche textes,
coûts, PV/statistiques, capacités, illustrateurs, rareté, légalité et détails par jeu.
Le frontend est découpé en modules fonctionnels catalogue/collectes.

## Limites assumées

- TCGdex/Pokémon est le seul adaptateur réel et spider actuellement disponible.
- Les contrats multi-jeux sont testés sur des exemples synthétiques, pas des
  connecteurs réels Magic, One Piece, Naruto, Yu-Gi-Oh!, Cyberpunk, Altered ou Riftbound.
- Les variantes détaillées sont préservées, mais pas éclatées automatiquement en
  impressions séparées. Il faut définir leur identité et leur nommage d'image avant.
- Le set d'une carte ignorée n'est pas rafraîchi automatiquement : utiliser un crawl
  forcé d'une carte du set pour obtenir son détail actuel.
- Ce sont les dernières observations, pas un historique de règles ou de prix.
- L'exhaustivité dépend des champs et langues disponibles à la source ; `null` ou
  champ absent n'est jamais remplacé par une valeur supposée.

Références : [TCGdex cartes](https://tcgdex.dev/rest/card),
[TCGdex sets](https://tcgdex.dev/rest/set),
[Scryfall types de faces/coûts](https://github.com/scryfall/api-types),
[YGOPRODeck](https://ygoprodeck.com/api-guide/).
