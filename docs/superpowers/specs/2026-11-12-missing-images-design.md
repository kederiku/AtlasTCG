# Réparation des images manquantes

## Intention et périmètre confirmé

Ajouter dans Collectes une action « Réparer les images manquantes » qui traite
toutes les impressions déjà enregistrées, dans toutes leurs langues. L’utilisateur
a confirmé les deux comportements : télécharger depuis une URL connue lorsque
le WebP manque ; en l’absence d’URL, rechercher l’image chez TCGdex, puis la
télécharger si elle est disponible. Les fichiers déjà présents sont conservés.

La réparation s’exécute en arrière-plan et son résultat apparaît dans l’historique
des collectes. Les données des cartes et leurs dates d’observation restent intactes.

## Approches

- **Demande dédiée dans la file existante, retenue avec l’utilisateur.** Le worker
  unique conserve l’exécution séquentielle, les statuts et les journaux. Un type
  explicite de demande distingue une réparation d’une collecte de données.
- **Actualisation complète des cartes.** Elle réutiliserait la collecte actuelle,
  mais modifierait aussi leurs observations et leurs dates : elle ne respecte pas
  le périmètre demandé.
- **Téléchargements dans la requête HTTP.** Ils lieraient une opération longue à
  la connexion du navigateur et contourneraient la file existante.

## Comportement proposé

Un bouton dans la page Collectes soumet la réparation globale. Un texte explique
sa portée avant le clic. L’envoi désactive le bouton et une erreur de soumission
reste visible. La nouvelle ligne d’historique porte le libellé « Réparation des
images », avec son état et un accès au journal. Les traductions FR/EN/ES suivent
les conventions de l’interface.

Le worker examine les impressions par lots, sans charger tout le catalogue en
mémoire. Pour chaque image, il vérifie le chemin local enregistré ou, à défaut,
le chemin déterministe déjà utilisé par la collecte :

1. Si le WebP existe, il est conservé, même si le cache de collecte l’aurait
   considéré trop ancien. Un fichier existant au chemin attendu peut être
   rattaché à l’impression si sa référence locale manque.
2. Si le WebP manque et qu’une URL fournisseur est connue, cette URL sert au
   téléchargement et à la conversion WebP sans perte.
3. Si aucune URL n’est connue et que l’image locale manque, la réparation
   consulte la fiche TCGdex correspondant exactement à l’identifiant et à la
   langue de l’impression. Elle extrait seulement l’URL d’image et télécharge
   le fichier si une image est disponible.

La recherche d’une URL concerne uniquement Pokémon/TCGdex, seul connecteur réel.
Elle ne découvre pas de nouvelles cartes et ne parcourt pas les listes, extensions
ou blocs du fournisseur. Une URL connue qui échoue produit une erreur de
téléchargement ; la redécouverte des URL devenues invalides est hors périmètre.
La vérification des fichiers déjà présents porte sur leur existence ; la réparation
des fichiers présents mais corrompus n’est pas incluse.

Les URL découvertes sont conservées pour permettre une reprise ultérieure, y compris
si leur téléchargement échoue. Les références locales ne sont ajoutées qu’après
publication réussie des WebP. Pour une impression à plusieurs images, les nouveaux
fichiers sont préparés avant publication ; l’échec d’un transfert ou d’une conversion
conserve tous ses fichiers précédents. Les images d’autres impressions déjà réparées
restent disponibles.

## Résultats et limites proposés

Le bilan distingue impressions examinées, images téléchargées, images déjà présentes,
impressions sans image disponible et erreurs. Le journal précise les identités
concernées par une indisponibilité ou une erreur.

Une fiche TCGdex absente ou toujours sans image est une indisponibilité, pas un
échec technique. Une erreur réseau, HTTP inattendue, de réponse, de conversion ou
de stockage est signalée ; les impressions suivantes peuvent être traitées et le
job termine en échec si au moins une erreur technique s’est produite. Un passage
sans travail à effectuer réussit avec zéro téléchargement.

Une nouvelle demande réexamine le catalogue et ignore les fichiers désormais
présents. Les limites de débit, retries, timeout et arrêt du worker restent celles
du système existant ; une interruption ne prétend pas avoir terminé le parcours.
L’historique conserve les statistiques finales et les journaux sont consultables
pendant l’exécution, sans ajouter de pourcentage de progression en temps réel.

## Frontières et invariants

- `packages/core` porte la demande typée, les règles de réparation et les ports
  nécessaires ; aucun accès SQL, HTTP, fichier ou processus dans le métier.
- `packages/persistence` lit les candidats par lots et modifie uniquement les
  URL et références d’images. Les identités, provenance, données brutes, règles,
  extensions, blocs, versions et dates d’observation sont préservés.
- `apps/scraping` assemble ces ports et possède l’accès fournisseur, les fichiers,
  la conversion et l’exécution. Réutiliser les mécanismes existants lorsque leurs
  contrats conviennent, sans faire passer la réparation par la sauvegarde complète
  d’une observation.
- `apps/api` valide et enregistre la demande ; `apps/frontend` soumet l’action et
  affiche son résultat. Les demandes et historiques de collectes existants restent
  lisibles et exécutables. Le JSON des paramètres permet cette distinction sans
  ajouter de table ni réécrire une migration.
- Les chemins de fichiers restent confinés au stockage configuré ; aucune URL,
  commande ou option technique libre n’est fournie par le bouton.
- Aucun prix n’est conservé depuis les réponses de découverte. Les faces gardent
  leur ordre, les langues leurs identités et les WebP leur convention de nommage.

## Exemples d’acceptation

- **Étant donné** une carte FR avec une URL et aucun WebP, **quand** la réparation
  s’exécute, **alors** son image devient consultable, sans requête de fiche TCGdex
  ni modification de ses données ou de sa date.
- **Étant donné** une carte ES sans URL ni fichier, **quand** sa fiche TCGdex
  fournit désormais une image, **alors** l’URL est conservée et le WebP téléchargé
  est rattaché à cette impression ES uniquement.
- **Étant donné** une image locale déjà présente, **quand** la réparation passe,
  **alors** aucun téléchargement ni remplacement de ce fichier n’a lieu.
- **Étant donné** une carte toujours sans image chez TCGdex, **quand** la réparation
  passe, **alors** elle est comptée comme indisponible et les autres cartes suivent.
- **Étant donné** une image en erreur et une autre impression réparable, **quand**
  le job termine, **alors** la seconde est réparée et l’erreur de la première est
  visible ; ses données et fichiers précédents sont préservés.
- **Étant donné** une réparation terminée, **quand** elle est relancée, **alors**
  les WebP présents sont ignorés et les images encore manquantes sont réessayées.
- **Étant donné** la page Collectes, **quand** l’action est soumise, **alors** une
  demande persistante apparaît dans l’historique et attend son tour si le worker
  est occupé ou arrêté.

## Vérification prévue

Tests d’acceptation à la frontière API, règles métier, mise à jour SQL ciblée,
téléchargements avec serveur HTTP local et fichiers temporaires, puis parcours
React et navigateur. Observer les échecs attendus avant chaque tranche de code.
Terminer par `make test`, `make test-installations`, `make docker-build` et
`make docker-test`, avec bases et fichiers de test isolés.

Mettre à jour le vocabulaire si nécessaire, la référence API, l’acceptation,
l’architecture et les règles de collecte qui prescrivent aujourd’hui une
actualisation complète pour réparer une image. Aucun commit, lancement de collecte
réelle, migration personnelle ou redémarrage de la pile n’est inclus.
