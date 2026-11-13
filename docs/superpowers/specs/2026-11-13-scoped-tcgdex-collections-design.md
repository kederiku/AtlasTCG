# Collecter un bloc ou une extension TCGdex

Date : 13 novembre 2026. Statut : conception approuvée par l’utilisateur.

Relecture indépendante effectuée le même jour : aucune question indispensable
restante pour établir le plan. Les liens locaux du document ont été vérifiés.

## Intention et périmètre

Dans l’admin, remplacer le choix d’un nombre maximal de cartes par le choix
d’un bloc entier ou d’une extension. Collecter toutes les cartes que TCGdex
fournit dans ce périmètre, pour les langues cochées, avec le traitement actuel
des cartes déjà présentes et des images WebP.

L’utilisateur a retenu la proposition recommandée : deux listes liées, bloc puis
extension, avec « Tout le bloc ». Le choix doit permettre une première collecte :
les options viennent de TCGdex, pas seulement du catalogue local.

Une demande cible un seul bloc ou une seule extension. Ni sélection multiple de
blocs, ni collecte automatique récurrente, ni rapprochement entre codes différents.
La réparation des images déjà développée conserve son parcours indépendant.

## Approches considérées

1. **Deux listes liées, retenu.** Le bloc filtre les extensions ; « Tout le bloc »
   collecte toutes ses extensions. La hiérarchie rend le périmètre visible, au prix
   d’une sélection supplémentaire quand on connaît déjà le nom de l’extension.
2. **Recherche unique mélangeant blocs et extensions.** Plus directe par nom,
   mais exige de distinguer clairement les deux types et montre moins bien leur
   rattachement. Non retenue après la proposition et la réponse « ok ».

La consultation en direct de TCGdex est un choix de conception : un sélecteur limité
aux données locales ne permettrait pas de choisir des extensions jamais collectées.
Une synchronisation persistante supplémentaire n’est pas nécessaire à ce besoin.

## Parcours de l’admin

- Conserver la source Pokémon/TCGdex, les langues cochées et l’option « Actualiser
  aussi les cartes déjà en base ». Retirer le champ « Nombre maximal par langue ».
- Afficher « Bloc » et « Extension ». Avec un bloc choisi, la seconde liste propose
  « Tout le bloc », puis ses extensions. Changer de bloc remet l’extension sur
  « Tout le bloc » ; aucune ancienne extension ne reste sélectionnée par accident.
- Proposer aussi « Tous les blocs » comme filtre de navigation : la liste des
  extensions contient alors toutes les extensions disponibles, y compris celles
  sans bloc. Dans cet état, choisir une extension est obligatoire. « Tous les
  blocs » ne déclenche jamais implicitement une collecte de tout TCGdex.
- Aucun périmètre n’est choisi au premier affichage. Le lancement est désactivé
  sans langue ou sans bloc/extension valide, pendant le chargement nécessaire à
  sa validation, après une erreur de chargement ou pendant l’envoi de la demande.
- Présenter chargement, liste vide, échec et bouton « Réessayer ». Une réponse
  tardive pour l’ancien bloc ne remplace pas les options du bloc courant.
- Garder la saisie actuelle de cartes dans un mode avancé « Cartes précises ».
  Ce mode exige des identifiants et remplace le périmètre bloc/extension ; les deux
  ne se combinent pas. Il collecte la liste complète saisie, au maximum 100 cartes
  comme aujourd’hui, sans champ de limite. Revenir au mode normal exige à nouveau
  un périmètre valide. Ne jamais soumettre les valeurs du mode inactif.
- Afficher dans l’historique et les détails le type de périmètre et son identifiant
  stable, par exemple « Bloc : swsh » ou « Extension : swsh3 », ainsi que les
  langues et l’actualisation. Les anciennes demandes bornées et les réparations
  restent lisibles. Aucun appel distant par ligne d’historique n’est nécessaire.

## Langues, noms et disponibilité

L’identité du choix reste le code fourni par TCGdex. Réunir les résultats des
langues de collecte par ce code ; ne proposer que les éléments présents dans au
moins une langue cochée. Les noms suivent la langue d’interface, puis le repli
français, anglais, premier code de langue disponible trié, enfin identifiant
(ADR 0007). Les métadonnées demandées pour les libellés ne rendent pas admissible
un élément absent de toutes les langues de collecte. Des codes différents ne
deviennent pas équivalents parce que leurs noms se ressemblent.

Chaque option expose les langues dans lesquelles la source la référence. Montrer
clairement si une sélection n’existe pas dans toutes les langues cochées. Après
un changement de langues, conserver le choix par code s’il reste admissible,
sinon l’effacer ; attendre les nouvelles options avant d’autoriser le lancement.
La disponibilité d’un bloc ne garantit pas celle de chacune de ses extensions.

Au lancement, conserver les langues demandées. Le worker reconsulte le périmètre
dans chacune d’elles : la liste de préparation n’est pas une photographie des
cartes à importer. Un périmètre absent dans une langue est signalé dans le journal
et un compteur de langues indisponibles ; les autres langues sont traitées. Si
le périmètre n’existe dans aucune langue demandée, l’exécution échoue explicitement.
Un périmètre trouvé mais vide peut réussir avec zéro carte et un diagnostic clair.

## Contrats et frontières

### Préparer le choix

Ajouter dans le contexte Collectes de core des résultats typés pour les choix
(identifiant, nom, langues disponibles), un petit port de découverte des blocs
et extensions localisés et un cas d’usage de préparation des options. Celui-ci
porte le regroupement, les règles de langue et d’admissibilité, sans connaître HTTP.

L’API expose deux lectures dédiées, distinctes du catalogue déjà enregistré :

- `GET /api/collection-options/tcgdex/blocks?languages=fr,en&locale=fr`
- `GET /api/collection-options/tcgdex/sets?languages=fr,en&locale=fr&block_id=swsh`

`block_id` est facultatif sur la seconde route. Valider langues, locale et
identifiants avant tout appel distant. Les réponses ne contiennent que les champs
utiles au choix, sans prix ni réponse brute de source. Une absence connue renvoie
une liste vide ; une panne, un délai dépassé ou une réponse malformée renvoie une
erreur temporaire explicite, jamais une liste partielle présentée comme complète.

Un adaptateur HTTP dans `apps/api` interroge uniquement l’hôte TCGdex fixé par
l’application : `/v2/{language}/series`, `/sets` et `/series/{block_id}`.
Les 404 de ressources localisées valent absence, les autres erreurs ne valent pas
absence. Les identifiants sont encodés comme segments ; aucune URL fournie par le
frontend n’est utilisée. Borne de concurrence, délais et taille des réponses
empêchent ce formulaire de monopoliser l’API. Les ressources HTTP appartiennent
au point d’entrée de l’API, sans import de Scrapy ou du paquet scraping.

React Query conserve brièvement les résultats, avec des clés incluant bloc,
langues et locale. Aucune table, migration ou tâche de synchronisation n’est
ajoutée pour ces listes ; le choix du client HTTP et les valeurs de ces bornes
restent à l’implémentation, avec tests des délais et des erreurs.

### Enregistrer la demande

Ajouter une variante explicite à `JobRequest`, sans modifier le sens des demandes
déjà enregistrées. Exemple de contrat proposé :

```json
{
  "kind": "collect_scope",
  "spider": "tcgdex",
  "languages": ["fr", "en"],
  "scope": {"kind": "set", "id": "swsh3"},
  "force": false
}
```

`scope.kind` vaut `block` ou `set`. Cette variante refuse `limit`, `card_ids`, les
champs inattendus, les identifiants vides et les séparateurs de chemin. Accepter
les identifiants TCGdex contenant des points, par exemple `swsh12.5` : ne pas
réutiliser à l’identique la validation restrictive des anciens identifiants de
cartes. Utiliser un premier caractère alphanumérique, puis lettres/chiffres,
points, tirets et soulignements, avec une longueur maximale explicite.

La soumission valide et met en file sans contacter TCGdex : le worker possède
l’exécution. Conserver la variante historique `CollectionRequest` avec `limit`
et `card_ids` pour l’API, les demandes déjà en file et les scripts. Le mode avancé
utilise cette variante avec une limite égale au nombre d’identifiants dédupliqués.
Conserver `ImageRepairRequest`. Le JSON de paramètres existant suffit ; aucune
migration ni modification des observations n’est nécessaire.

### Exécuter le périmètre

Le runner transforme la demande en arguments explicites du spider existant
`tcgdex`, sans shell. Ajouter les chemins de découverte suivants :

- **Extension** : lire `/sets/{id}` dans chaque langue, émettre les métadonnées
  d’extension, puis visiter toutes les cartes de sa liste `cards`.
- **Bloc** : lire `/series/{id}`, émettre les métadonnées de bloc, puis lire
  chacun des sets de sa liste `sets` et toutes leurs cartes.

Réutiliser les normalisations, pipelines, règles sans prix, stockage et middleware
qui ignore les cartes déjà au contrat courant. Une collecte ciblée ne passe pas
par la liste générale `/cards` et ne subit pas la valeur historique de dix cartes.
Préserver les parcours CLI/API historiques de découverte bornée et par identifiants.
Ne pas mélanger un périmètre avec des identifiants explicites ou une limite.

Le détail d’un bloc récupéré comme métadonnée d’une extension ne doit pas élargir
la collecte aux autres extensions : séparer explicitement découverte du périmètre
et enrichissement des métadonnées. Dédupliquer par type, code et langue, sans
supposer que les préfixes indiquent une appartenance. Les réponses doivent porter
les identifiants attendus ; un document incohérent ou malformé est une erreur.

Un 404 du périmètre racine vaut indisponibilité dans cette langue. Un 404 pour une
extension ou une carte annoncée dans une liste reçue est une erreur de collecte,
comme un échec persistant de transfert ou de normalisation. Les résultats partiels
restent conservés et le statut final reflète l’erreur selon le contrat existant.
Garder les limites de débit, retries et le délai maximal actuel d’une heure par
exécution ; un bloc volumineux peut dépasser ce délai, échouer partiellement et
être redemandé en ignorant ce qui a déjà été enregistré. Aucun découpage automatique
en sous-demandes n’entre dans cette tranche.

## Critères d’acceptation

1. **Étant donné** un catalogue local vide et un bloc TCGdex comprenant deux
   extensions, **quand** je choisis le bloc et « Tout le bloc », **alors** la demande
   cible ce bloc et le worker visite toutes les cartes des deux extensions,
   y compris au-delà de dix cartes, sans visiter un autre bloc.
2. **Étant donné** ce bloc, **quand** je choisis seulement sa première extension,
   **alors** seules ses cartes sont collectées, même si les métadonnées du bloc
   mentionnent aussi la seconde extension.
3. **Étant donné** une extension sans bloc, **quand** je la choisis dans « Tous
   les blocs », **alors** je peux collecter cette extension ; laisser les deux
   sélections sans cible n’autorise pas une collecte globale implicite.
4. **Étant donné** les langues FR et EN et une extension disponible uniquement
   en EN, **quand** je la sélectionne, **alors** l’admin montre cette disponibilité,
   le worker importe EN, signale FR indisponible et ne crée aucune impression FR.
   Si elle a disparu dans toutes les langues avant exécution, la demande échoue.
5. **Étant donné** des cartes déjà enregistrées, **quand** je collecte leur
   extension sans actualisation, **alors** elles sont ignorées ; cocher
   l’actualisation autorise leur relecture, avec les garanties de médias existantes.
6. **Étant donné** une sélection et un changement de bloc ou de langues,
   **quand** les options se rechargent ou échouent, **alors** aucune sélection
   périmée ne peut être soumise et une action de nouvelle tentative est disponible.
7. **Étant donné** une ancienne demande bornée, une saisie avancée de cartes et
   une réparation d’images, **quand** elles sont lues ou exécutées, **alors** leurs
   comportements respectifs restent disponibles et distincts de la collecte ciblée.
8. **Étant donné** une indisponibilité HTTP, une réponse malformée ou une carte
   listée mais introuvable, **quand** la préparation ou l’exécution la rencontre,
   **alors** elle expose un échec observable au lieu d’annoncer un périmètre complet.

## Vérification et livraison

Avant chaque comportement, faire échouer un test d’acceptation pertinent : core/API
pour demandes et options, React pour choix et états, serveur HTTP local avec le
spider réel pour le résultat et la fermeture du périmètre. Ne pas appeler TCGdex
depuis les tests ordinaires. Couvrir les points dans les codes, déduplication,
langues, anciennes demandes et absence de collecte des autres extensions.

Terminer par `make test`, `make test-installations` pour les frontières Python
touchées et un parcours navigateur isolé. Si la réalisation modifie packaging,
dépendances runtime, stockage ou Docker, ajouter `make docker-build` puis
`make docker-test`. Préserver le travail de réparation des images en cours dans
le checkout, sans commit, collecte réelle ni redémarrage de la pile personnelle.

Mettre à jour CONTEXT, les contrats d’acceptation et API, l’architecture et le guide
utilisateur/exploitation concerné. Un ADR précisera la découverte distante pour
préparer une demande, en complément des ADR 0001, 0005, 0006 et 0007, sans fusionner
les observations du catalogue avec les options proposées par la source.

## Références

- [Langage du domaine](../../../CONTEXT.md)
- [Règles d’ingénierie](../../engineering.md)
- [Blocs localisés](../../adr/0005-localized-blocks.md)
- [Applications séparées](../../adr/0006-separated-applications.md)
- [Navigation multilingue](../../adr/0007-multilingual-navigation.md)
- [Liste des blocs TCGdex](https://tcgdex.dev/rest/series)
- [Détail d’un bloc et ses extensions](https://tcgdex.dev/rest/serie)
- [Liste des extensions](https://tcgdex.dev/rest/sets)
- [Détail d’une extension et ses cartes](https://tcgdex.dev/rest/set)
