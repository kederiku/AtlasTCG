# Contrat d'acceptation de l'admin

## Catalogue

Étant donné deux impressions d'une même carte dans deux langues,
quand je filtre par nom et langue, alors seule l'impression recherchée apparaît,
avec son image locale. Les filtres jeu/bloc/set se combinent à la recherche. Les résultats
sont paginés (24 par défaut, 100 au maximum) et ordonnés de manière stable.
La fiche présente provenance, numéro, extension, date et données brutes.
Elle s'ouvre dans une page dédiée avec une URL partageable. Un rechargement direct
conserve la fiche ; le retour au catalogue retrouve les filtres et la pagination.
Une identité absente affiche « Carte introuvable ».

Étant donné une carte enrichie, la fiche présente le nom localisé de son extension,
les illustrateurs, les faces, les coûts et les capacités fournis par la source,
y compris les valeurs nulles, le zéro et les dégâts symboliques. Les résumés de
liste n’incluent pas `raw`, `faces` ou `game_data` ; ces champs appartiennent au
détail. Les URLs d’images locales et les URLs fournisseur restent distinctes.

Les prix sont exclus de l'import, y compris dans les variantes et les données
brutes. La migration nettoie également les cartes et extensions déjà en base,
sans changer leurs identités, images ou dates de collecte. Les coûts de jeu restent
disponibles.

## Blocs

Étant donné « Noir et Blanc » / « Negro y Blanco » et « Destinées Futures » /
« Destinos Futuros » collectés avec les mêmes identifiants, quand l’interface est
française et les cartes espagnoles, les blocs/extensions restent proposés une seule
fois avec leurs noms français. Changer la langue des cartes garde l’extension et
revient à la première page. Une langue sans carte affiche un résultat vide.

Étant donné une carte en FR/ES, la grille présente une seule vignette et un lien vers
chaque impression localisée. Le total et la pagination comptent les groupes ; les
statistiques de stockage comptent les impressions. Une recherche avec un nom
traduit de carte/bloc/extension retrouve les cartes en respectant les filtres.
Jeux, sources et identifiants distincts ne sont jamais rapprochés par nom seul.

L’interface est disponible en français, anglais et espagnol. La préférence survit
au rechargement, avec le français par défaut et un fonctionnement en mémoire si
le stockage navigateur est indisponible. Menus, formulaires, états, statuts et
libellés accessibles suivent cette préférence ; les textes et journaux source
gardent leur langue. Le changement d’interface ne modifie ni la fiche ouverte ni
les filtres du catalogue. Une traduction absente suit le repli documenté dans
[l’ADR 0007](adr/0007-multilingual-navigation.md).

Étant donné deux extensions du même bloc et une extension d’un autre bloc, quand je
filtre le catalogue par bloc, jeu, source et langue, seules les cartes des deux
premières apparaissent. Le même code chez un autre jeu/source reste distinct.
Changer de bloc réinitialise le set et la page ; la fiche permet d’ouvrir son bloc.

Étant donné des métadonnées de série déjà stockées, la migration crée les blocs et
leurs relations sans changer cartes, images ni dates. Une extension sans référence
reste sans bloc. Les métadonnées détaillées d’un bloc résistent aux résumés partiels.

## Collecte

Étant donné un admin local, quand je demande une collecte TCGdex avec des langues
et un bloc ou une extension, alors elle entre dans une file persistante et son
périmètre apparaît dans l’historique et le journal. Les choix viennent de TCGdex,
y compris quand le catalogue local est vide. « Tous les blocs » exige une extension
précise ; sélectionner un bloc propose « Tout le bloc » ou une de ses extensions.
La collecte parcourt toutes les cartes du périmètre, y compris au-delà de dix,
sans élargir une extension aux autres extensions du même bloc.

Étant donné une extension disponible seulement en EN et les langues FR/EN cochées,
quand je la choisis, alors FR est indiquée indisponible. Le worker traite EN et
signale l’absence FR ; un périmètre disparu dans toutes les langues échoue.
Une erreur source ou une ressource annoncée mais absente n’est pas un succès silencieux.
Changer de bloc réinitialise l’extension ; changer de langues conserve seulement
un choix admissible et ne transforme jamais une extension disparue en bloc entier.
Les listes en chargement/erreur empêchent l’envoi ; une erreur permet de réessayer.

Le mode avancé « Cartes précises » conserve la saisie de 1 à 100 identifiants,
sans limite supplémentaire ni combinaison avec un périmètre.
L'API n'accepte pas de nom de commande, d'URL arbitraire ni d'options Scrapy libres.
Les anciennes demandes API sans `kind` conservent une limite de 1 à 10 000 candidats
par langue ; `limit=0` reste disponible pour ce parcours uniquement en CLI.
Dans cette variante historique, les identifiants explicites sont optionnels.
La limite s’applique aux premiers candidats avant de filtrer ceux déjà présents,
y compris avec des identifiants explicites. Relancer la même demande ne signifie
pas « prendre les candidats suivants ». Les bornes et les langues acceptées sont
décrites dans [la référence API](api.md#soumettre-et-suivre-une-collecte).

Étant donné le formulaire de collecte, quand ses capacités sont chargées depuis
l’API, alors les 18 langues TCGdex sont sélectionnables et seuls français et
anglais sont cochés par défaut. Une demande peut contenir les 18 codes à la fois ;
les variantes régionales (`es-mx`, `pt-br`, `pt-pt`, `zh-tw`, `zh-cn`) restent
distinctes dans la demande et les impressions. Une langue inconnue est refusée.
Pendant le chargement ou après son échec, aucune demande ne peut être soumise ;
une erreur visible permet de réessayer le chargement.

Étant donné une carte déjà au contrat courant, même sans image, quand la collecte
est relancée sans forcer, alors elle n’est pas retéléchargée et son compteur apparaît
comme ignoré. Une carte d’une ancienne version reste éligible à la recollecte.
Si Scrapy s'arrête sur robots.txt, signale une erreur ou rejette un item, le job ne
s'affiche pas comme réussi, même avec un code processus zéro.

Étant donné une impression avec plusieurs images déjà conservées, quand une
recollecte reçoit une image valide puis une autre absente ou corrompue, alors la
collecte échoue et l’observation précédente, sa date et tous ses fichiers restent
inchangés. Les fichiers de remplacement ne sont publiés qu’une fois tous les
téléchargements et conversions de cette impression réussis.

Étant donné deux demandes en attente, quand le collecteur échoue sur la première,
alors son erreur et ses dates sont conservées et la suivante peut être exécutée.
L’arrêt contrôlé du worker interrompt son enfant et marque la demande active comme
interrompue, sans consommer la demande suivante. Un second worker sur le même
répertoire de jobs est refusé sans modifier la collecte du premier.

## Réparation des images

Étant donné des impressions déjà enregistrées dans plusieurs langues, quand je
clique sur « Réparer les images manquantes » dans Collectes, alors une demande
globale rejoint la file et apparaît dans l’historique. Son envoi ne peut pas être
doublé pendant la requête ; une erreur permet de réessayer. Le parcours et le bilan
sont disponibles en FR/EN/ES.

Étant donné une URL connue et un WebP absent, quand la réparation passe, alors elle
télécharge cette image sans consulter la fiche source. Sans URL ni fichier local,
elle consulte la fiche TCGdex de la même langue et conserve l’URL découverte avant
le téléchargement. Un fichier présent est conservé même ancien, et peut être
rattaché à l’impression si sa référence manque. Les autres données et dates restent
identiques.

Une fiche absente ou toujours sans image est signalée comme indisponible. Une erreur
technique fait échouer la demande, sans empêcher les autres impressions d’être
traitées. Une réponse portant un autre identifiant est refusée. Les chemins restent
dans le stockage configuré, y compris avec des liens symboliques. Pour plusieurs
faces, un échec conserve les fichiers précédents et ne publie pas les autres
nouveaux fichiers de cette impression. Une nouvelle réparation réessaie les
images encore manquantes ; les fichiers présents ne sont pas contrôlés pour corruption.

## Lancement Docker

Étant donné une configuration locale et un dossier de données accessible,
quand je lance `docker compose up --build -d --wait`, alors PostgreSQL est disponible,
les migrations ont réussi, l’admin sert son frontend et le worker exécute les demandes.
Un lien direct vers une fiche fonctionne sans passer par la page d’accueil.

Étant donné une carte déjà enregistrée et son WebP, quand les services redémarrent,
alors la carte, le fichier et l’historique restent présents. Une nouvelle collecte
sans forcer ignore cette carte. Le test de pile n’utilise jamais la base personnelle.

## Séparation des applications

Étant donné l’installation API seule, sans Scrapy, Playwright ni Chromium, quand
je consulte le catalogue et soumets une demande, les routes fonctionnent et la
demande reste en attente sans worker. Quand le worker est disponible, il exécute
la demande et l’API en consulte le résultat via le stockage partagé.

Étant donné l’installation scraping seule, sans FastAPI/Uvicorn, une collecte HTTP
locale produit les observations et images attendues. Un timeout ou une interruption
termine son processus enfant. Le métier reçoit le résultat, sans interpréter les
clés de statistiques Scrapy.

## Vérifications exécutables

- `tests/acceptance/` : scénarios Gherkin et étapes API.
- `tests/integration/` : collectes, normalisation/persistance et réindexation.
  Celle-ci refuse les données invalides et toute modification d’identité,
  d’extension ou de numéro sans altérer l’observation, puis traite la suivante.
- `tests/architecture/` : frontières de dépendance et nommage sans Scrapy.
- `packages/core/tests/` : contrat multijeu, nommage et exécution indépendante.
- `packages/persistence/tests/` : transactions, identités, requêtes, migrations et configuration.
- `apps/api/tests/` : contrats HTTP, journaux, disponibilité, médias et liens directs.
- `apps/scraping/tests/` : mapping, prix, WebP, pipeline HTTP local, processus et CLI.
- `apps/frontend/src/app/App.test.tsx` : soumission, navigation et journal.
- Tests voisins de `features/catalog` et `features/collections` : filtres URL, fiche,
  règles, formulaire et actualisation explicite.
- `scripts/check_installations.py` : quatre installations non éditables indépendantes.
- `scripts/docker_smoke.py` : PostgreSQL réel, images séparées, worker, médias,
  Chromium et persistance après redémarrage, dans une pile temporaire.

Les scénarios Gherkin passent par l’API et les tests React simulent le transport
HTTP. Ils ne remplacent pas un parcours dans un navigateur pour vérifier une
modification visuelle. Le test Docker exerce les services réels avec des données
locales, sans collecter chez TCGdex.

Préciser les exemples d’acceptation avant le code, faire échouer un test observable,
implémenter la tranche minimale puis refactorer. Les tests ne dépendent pas de TCGdex.
