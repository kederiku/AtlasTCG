# Référence API locale

L’API est servie sur `http://127.0.0.1:8000`, avec ou sans frontend compilé.
[Swagger UI](http://127.0.0.1:8000/docs), [ReDoc](http://127.0.0.1:8000/redoc) et
[OpenAPI](http://127.0.0.1:8000/openapi.json) exposent les schémas générés depuis
les routes et modèles actuels. Les exemples ci-dessous supposent une base migrée.

## Accès local et erreurs

L’application n’a ni compte ni jeton d’authentification. Le serveur contrôle le
nom d’hôte (`localhost` ou `127.0.0.1`). Pour `POST /api/jobs`, il exige
`X-TCG-Admin: 1` et, si un en-tête `Origin` est présent, une origine HTTP locale
sur le port 8000 ou 5173. Cet en-tête d’intention n’est pas un mécanisme
d’authentification. Aucun CORS permissif n’est configuré.

Le frontend Vite utilise le proxy `/api` vers le port 8000 ; le frontend compilé
et l’API partagent directement la même origine. Une API publiée sur un autre port
reste consultable directement ; les mutations depuis son frontend seront refusées
par le contrôle d’origine. Cela n’autorise pas les appels JavaScript entre origines.

| Code | Signification |
|---|---|
| `200` | Lecture réussie |
| `202` | Demande de collecte persistée ; son exécution n’est pas encore acquise |
| `400` | Nom d’hôte refusé |
| `403` | En-tête d’administration absent ou origine refusée |
| `404` | Carte, collecte, fichier ou route introuvable |
| `422` | Paramètre, identité UUID ou corps de requête invalide |
| `503` | La sonde `/api/health` ne peut pas lire la table du catalogue |

Les erreurs des routes JSON exposent `detail`, sous forme de texte ou de liste
d’erreurs de validation. Le contrôle d’hôte peut répondre en texte brut.
La sonde ne vérifie ni le worker, ni l’intégralité du schéma, ni le frontend.

## Consulter le catalogue

| Route GET | Résultat |
|---|---|
| `/api/health` | `{"status":"ok"}` si le catalogue est accessible |
| `/api/cards` | Page `{items, total, page, page_size}` de résumés |
| `/api/card-groups` | Page de cartes regroupées avec leurs versions linguistiques |
| `/api/cards/detail` | Détail d’une impression localisée |
| `/api/overview` | Total, jeux, langues et facettes de blocs/extensions |
| `/api/blocks` | Tous les blocs localisés, sans pagination |
| `/api/sets` | Toutes les extensions localisées, sans pagination |
| `/api/images/<chemin>` | Fichier local, ou 404 s’il est absent |

`GET /api/cards` accepte ces paramètres combinables :

| Paramètre | Défaut / contrainte |
|---|---|
| `q` | Vide ; sous-chaîne du nom, sans distinction de casse, 200 caractères maximum ; `%` et `_` sont littéraux |
| `game`, `source`, `language` | Vides ; égalité exacte lorsqu’ils sont fournis |
| `set_id`, `block_id` | Vides ; codes source, à préciser avec `game` et `source` pour lever les ambiguïtés |
| `page` | `1`, minimum `1` |
| `page_size` | `24`, de `1` à `100` |

L’ordre est stable : jeu, source, extension, numéro, langue, identifiant source.
Le numéro est une chaîne : cet ordre n’est pas un tri numérique des numéros imprimés.
Une recherche sans résultat retourne une page vide, sans erreur 404.

```sh
curl --fail --get 'http://127.0.0.1:8000/api/cards' \
  --data-urlencode 'q=Dracaufeu' \
  --data-urlencode 'game=pokemon' \
  --data-urlencode 'source=tcgdex' \
  --data-urlencode 'language=fr' \
  --data-urlencode 'block_id=base' \
  --data-urlencode 'page_size=24'

curl --fail --get 'http://127.0.0.1:8000/api/cards/detail' \
  --data-urlencode 'game=pokemon' \
  --data-urlencode 'source=tcgdex' \
  --data-urlencode 'source_id=base1-4' \
  --data-urlencode 'language=fr'
```

Le détail exige les quatre composants d’identité ; l’exemple retourne 404 si cette
impression n’a pas été collectée. Les résumés exposent identité, noms, extension,
bloc, numéro, rareté, illustrateurs, version, date d’observation et URLs locales.
Le détail ajoute `source_image_urls`, `set_info`, `faces`, `legalities`, `game_data`
et `raw`, ainsi que `versions` (résumés des impressions de même jeu/source/identifiant).
`image_urls` désigne les images servies sous `/api/images/` ; les URLs
fournisseur sont dans `source_image_urls`. Sans image persistée, `image_urls` est
vide. Aucun prix n’est exposé, y compris dans `raw`.

Les facettes de `/api/overview` sont globales au catalogue, non limitées au filtre
courant. Elles regroupent chaque bloc/extension par `(game, source, id)` avec
`names` par langue ; les extensions ajoutent `block_ids` par langue. Une extension
connue peut apparaître sans carte. Voir le [modèle](catalog-model.md).

### Navigation regroupée

`GET /api/card-groups` accepte les mêmes filtres et limites que `/api/cards`, plus
`display_language` (défaut `fr`). Son `q` recherche les noms de carte, extension et
bloc dans toutes les traductions collectées, sans modifier la langue des cartes
filtrées. Les noms sont recherchés par sous-chaîne sans distinction de casse ;
`%` et `_` restent littéraux. Aucun rapprochement approximatif n’est effectué.

Chaque élément porte les champs d’un résumé représentatif et `versions`, la liste
de toutes ses impressions collectées (résumés légers avec URLs locales, sans raw).
Jeu/source/identifiant forment le groupe. Le choix représentatif respecte les
filtres puis préfère `display_language`, `fr`, `en`, puis le code de langue trié.
Une langue demandée absente donne zéro résultat ; aucune autre langue ne la remplace.

`total`, `page` et `page_size` portent sur les groupes. L’ordre est jeu, source,
plus petit code de set du groupe, plus petit numéro, identifiant source. Les clés
de groupe sont paginées avant le chargement des versions, sans requête par carte.
L’ordre est indépendant de `display_language`. Les routes `/api/cards` et
`/api/cards/detail` conservent leurs identités et leur sémantique localisées.

## Soumettre et suivre une collecte

| Route | Résultat |
|---|---|
| `GET /api/spiders` | Connecteurs déclarés : `id`, `name`, `game`, `languages` |
| `POST /api/jobs` | Demande créée avec statut `queued`, HTTP 202 |
| `GET /api/jobs` | Les 50 demandes les plus récentes, de la plus récente à la plus ancienne |
| `GET /api/jobs/{identifier}` | Une demande, identifiée par son UUID |
| `GET /api/jobs/{identifier}/logs` | Texte UTF-8 des derniers 64 000 octets du journal |

Seul `tcgdex` est implémenté. Le corps JSON n’accepte que les champs suivants :

| Champ | Défaut / contrainte |
|---|---|
| `spider` | `"tcgdex"`, seule valeur acceptée |
| `languages` | `["fr", "en"]` ; 1 à 18 entrées autorisées, doublons retirés |
| `card_ids` | `[]` ; 100 entrées maximum, chacune de 1 à 100 caractères `[A-Za-z0-9_-]`, doublons retirés |
| `limit` | `10` ; de `1` à `10000` candidats par langue |
| `force` | `false` ; relire aussi les impressions déjà au contrat courant |

Langues déclarées : `en`, `fr`, `es`, `es-mx`, `it`, `pt`, `pt-br`, `pt-pt`, `de`,
`nl`, `pl`, `ru`, `ja`, `ko`, `zh-tw`, `id`, `th`, `zh-cn`. Le formulaire charge
cette liste depuis `GET /api/spiders` et sélectionne seulement `fr` et `en` par
défaut. Les variantes régionales restent des identités distinctes. Une langue
autorisée ne garantit pas que chaque carte existe dans cette langue chez le fournisseur.

La limite est appliquée avant l’évitement des cartes existantes, y compris avec
`card_ids`. Relancer une demande identique ne parcourt pas automatiquement les
candidats suivants. `force` conserve le cache des images ; le rafraîchissement de
ce cache passe par la [CLI](operations.md#collecter-et-actualiser).

Cet exemple enregistre une demande réelle ; le worker actif pourra l’exécuter :

```sh
curl --fail 'http://127.0.0.1:8000/api/jobs' \
  -H 'Content-Type: application/json' \
  -H 'X-TCG-Admin: 1' \
  --data '{"spider":"tcgdex","languages":["fr"],"card_ids":["base1-4"],"limit":1,"force":false}'
```

Reprendre l’`id` renvoyé pour consulter `/api/jobs/{identifier}` et son `/logs`.
Sans worker, la demande reste `queued`. Les réponses comprennent `id`, `status`,
`parameters`, `stats`, `error`, `created_at`, `started_at`, `finished_at`.
Les dates de début/fin et l’erreur peuvent être nulles. `stats` contient les
diagnostics Scrapy, généralement renseignés en fin d’exécution.

États : `queued` → `running` → `succeeded` ou `failed` ; une interruption du worker
produit `interrupted`. Il n’existe pas d’endpoint d’annulation, de suppression ni
de reprise automatique. Une nouvelle demande est nécessaire pour poursuivre.
Un job connu dont le fichier de log n’existe pas encore renvoie
« En attente du worker… » ; un UUID inconnu renvoie 404. Le journal n’est pas un
flux temps réel : le client doit le relire. L’historique n’est pas paginé au-delà
des 50 dernières demandes, mais une demande ancienne reste accessible par son UUID.

Les règles de timeout, d’arrêt et de maintenance figurent dans
[le guide d’exploitation](operations.md). Les schémas HTTP vivent dans
`apps/api/src/tcg_api/schemas/`, leurs routes dans `apps/api/src/tcg_api/routes/`.
