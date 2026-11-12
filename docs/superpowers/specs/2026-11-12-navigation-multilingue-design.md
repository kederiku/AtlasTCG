# Navigation du catalogue et interface multilingue

Statut : validé par l’utilisateur le 12 novembre 2026 ; implémentation autorisée.

## Besoin et décisions exprimées

Un bloc ou une extension représente le même élément de navigation dans ses
différentes langues : « Noir et Blanc » / « Negro y Blanco », puis
« Destinées Futures » / « Destinos Futuros ». L’utilisateur veut explorer les
cartes sans devoir reconnaître ces traductions comme des entrées distinctes.

Décisions confirmées dans la conversation :

- La langue des cartes est indépendante de celle de l’interface.
- Avec une interface française, les blocs/extensions restent nommés en français
  même lorsque les cartes sont filtrées en espagnol.
- L’interface doit être disponible en français, anglais et espagnol.

L’utilisateur délègue le choix de présentation des vignettes à l’agent, avec pour
critère le parcours le plus intuitif. Choix proposé par l’agent : une vignette par
carte avec accès direct à ses impressions localisées. Ce choix évite de répéter
une même carte quand plusieurs langues ont été collectées.

## Constats vérifiés

- Les identités persistées incluent jeu, source, identifiant source et langue.
- `/api/overview` regroupe déjà blocs/extensions par jeu, source et identifiant,
  avec leurs noms par langue. Les noms eux-mêmes ne servent pas d’identité.
- Le frontend choisit actuellement le nom des facettes avec la langue des cartes.
  Un exemple local FR/ES reproduit le changement de repère décrit.
- Changer la langue des cartes efface actuellement l’extension sélectionnée.
- La grille liste les impressions localisées : deux langues produisent deux tuiles.
- Les services personnels étaient arrêtés lors du diagnostic. Le signalement de
  doublons d’extensions n’a pas été reproduit sur la base personnelle. Une fixture
  avec un même identifiant et deux langues ne produit qu’une extension dans l’API.

## Approches

1. **Une seule langue de cartes active.** Changement limité, mais masque les cartes
   disponibles uniquement dans d’autres langues et ne sépare pas à lui seul la
   langue des repères de celle du contenu. Ne répond pas au besoin complet.
2. **Navigation commune au-dessus des observations localisées.** Conserver les
   identités existantes, présenter les noms selon la langue de l’interface et
   permettre de filtrer/ouvrir les versions linguistiques. Approche recommandée,
   cohérente avec le parcours confirmé ; aucun nouveau schéma de stockage nécessaire.
3. **Nouvelles tables d’entités communes et de traductions.** Possible si un futur
   besoin impose des correspondances entre codes distincts, mais aucune règle de
   rapprochement nouvelle n’est établie ici. Une migration ne corrige pas, seule,
   le couplage actuel entre langue des cartes et libellés de navigation.

Les choix techniques ci-dessous sont proposés par l’agent. Ils ne sont pas
présentés comme des décisions prises par l’utilisateur.

## Parcours et règles d’affichage

Un sélecteur global propose « Français », « English », « Español ». La préférence
est mémorisée localement ; le français est le défaut en l’absence de préférence
valide. Un stockage navigateur indisponible n’empêche pas de changer de langue
pendant la session. Le document HTML porte la langue choisie.

Le sélecteur « Langue des cartes » reste indépendant et propose les langues
réellement collectées. Un changement de langue d’interface ne modifie ni filtres,
ni page, ni identité de la fiche ouverte. Un changement de langue des cartes garde
bloc et extension, et revient à la première page. Une extension sans carte dans
cette langue produit un état vide explicite, sans élargir silencieusement le filtre.

Blocs et extensions n’ont qu’une entrée par `(game, source, source_id)`. Ce repère
commun est utilisé dans les menus, les tuiles, les titres et liens des fiches.
Ordre de repli proposé pour un nom absent : langue d’interface, français, anglais,
puis première traduction connue par code de langue trié, enfin identifiant source.
Ce repli est stable et ne dépend pas du filtre des cartes. Aucune traduction de
données absentes n’est inventée ni téléchargée automatiquement.

La recherche accepte le nom d’une carte, d’une extension ou d’un bloc dans les
traductions collectées. Ainsi « Destinos Futuros » retrouve les cartes de cette
extension avec des repères français. Les correspondances restent limitées au même
jeu et à la même source. Les filtres explicites restent cumulatifs. La recherche
conserve ses règles actuelles de sous-chaîne sans distinction de casse et de
caractères `%` et `_` littéraux ; pas de recherche approximative ni traduction libre.

## Vignettes regroupées

Une carte de navigation regroupe uniquement les impressions partageant
`(game, source, source_id)`, jamais un nom ou un numéro seul. Ce regroupement
de lecture ne fusionne pas les observations, ne crée pas d’identité universelle
entre fournisseurs et ne rapproche pas des éditions à codes différents.

Sans filtre de langue, une tuile présente une impression représentative, choisie
par langue d’interface, puis français, anglais, puis code de langue trié. Elle
affiche les langues collectées ; chacune ouvre la fiche existante correspondante.
Le lien principal ouvre l’impression représentative. Avec un filtre de langue,
seuls les groupes possédant cette impression apparaissent et cette impression
fournit le nom et l’image de la tuile. Les autres versions collectées restent
accessibles par leurs liens explicites. La recherche sur une autre traduction
peut retrouver le groupe sans changer la langue de l’impression affichée.

La pagination est réalisée sur les groupes avant de charger leurs versions :
24 cartes par page, chaque groupe apparaît sur une seule page. Le total des
résultats compte les groupes. La statistique globale conserve le nombre
d’impressions collectées et porte un libellé explicite. L’ordre des groupes reste
stable et indépendant de la langue d’interface.

Les fiches conservent leurs URLs localisées, leurs textes et images source. Les
liens vers les langues disponibles conservent le chemin de retour au catalogue.
Si la même identité source comporte des métadonnées d’extension différentes entre
langues, les valeurs propres à chaque impression restent conservées : aucune
réécriture ni équivalence entre codes n’est déduite de ce regroupement.

## Couverture de traduction de l’interface

Traduire navigation, titres, métriques, filtres, pagination, états de chargement,
états vides, erreurs applicatives, libellés accessibles, boutons et dialogues,
formulaire de collecte, historique, statuts, fiche, rubriques de règles et messages
d’image absente. Dates et nombres sont formatés selon la langue d’interface.

Les contenus des cartes, noms d’attaques, textes imprimés, valeurs source, réponses
brutes et journaux techniques ne sont pas traduits. Les erreurs applicatives ont
un message localisé ; un diagnostic brut utile peut rester présenté séparément.
Les 18 langues de collecte restent proposées ; les trois langues d’interface ne
réduisent pas les capacités du connecteur. Les choix de collecte FR/EN par défaut
restent indépendants de la préférence d’interface.

## Répartition proposée

- Frontend : contexte de langue, dictionnaires FR/EN/ES avec les mêmes clés
  vérifiées par TypeScript, formatage `Intl`, sélecteur et traduction des écrans.
  Pas de nouvelle dépendance nécessaire pour ce périmètre.
- Core : contrats et cas d’usage de navigation groupée ; invariants d’identité
  et choix d’impression explicites.
- Persistence : recherche dans les traductions et pagination correcte des groupes.
  Ne pas charger tout le catalogue en mémoire ni faire une requête par vignette.
- API : réponse explicite pour la navigation groupée, en conservant les routes
  actuelles de consultation des impressions et leurs identités.
- Documentation : compléter contrat d’acceptation, API et modèle ; nouvel ADR
  précisant les ADR 0002/0003/0005 pour distinguer regroupement de lecture et identité.

La forme précise des nouveaux types et endpoints reste au plan d’implémentation.
Les fonctions de regroupement/choix ne doivent pas être cachées dans les routes.

## Acceptation

1. Étant donné un bloc et une extension collectés en FR/ES avec les mêmes codes,
   quand l’interface est française et les cartes espagnoles, alors les menus
   contiennent une seule entrée « Noir et Blanc » et « Destinées Futures ».
2. Quand je passe les cartes de FR à ES, alors l’extension reste sélectionnée,
   ses repères restent français et seuls les résultats en espagnol sont retenus.
3. Quand je passe l’interface à EN ou ES, alors les contrôles et noms de navigation
   suivent ce choix sans modifier filtres, langue des cartes ni fiche ouverte.
4. Quand je recharge l’application, alors la préférence d’interface est restaurée.
5. Quand je cherche une traduction collectée du bloc ou de l’extension, alors ses
   cartes sont retrouvées en respectant jeu, source et langue des cartes.
6. Une traduction absente utilise le repli documenté. Deux jeux ou sources avec
   les mêmes codes ou noms restent séparés. Une extension sans bloc reste navigable.
7. Deux impressions FR/ES d’une même carte donnent une seule tuile, deux liens
   de langues et un total de un ; les
   pages n’ont ni doublon de groupe ni résultats perdus entre deux pages.
8. Le formulaire et l’historique fonctionnent dans les trois langues, avec les
   mêmes paramètres HTTP et capacités de collecte qu’avant le changement.

## Validation et exploitation

Observer les échecs attendus des tests d’acceptation avant chaque tranche de code.
Fixtures déterministes et bases temporaires uniquement, sans API TCGdex nécessaire
aux tests. Couvrir les limites de pagination et collisions de jeu/source du
catalogue groupé. Vérifier le parcours navigateur dans les trois langues et sur
une largeur mobile, y compris retour de fiche et rechargement.

Terminer par `make test`. Les changements Python et de lecture SQL impliquent
également `make test-installations`, `make docker-build` et `make docker-test`.
Pas de modification du schéma, migration de la base personnelle, réindexation,
suppression d’observation, changement de fichier image ou de date de collecte.
Pas de commit ni de redémarrage de la pile personnelle dans cette proposition.
