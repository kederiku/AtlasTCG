# ADR 0008 — Réparer les médias sans remplacer les observations

Statut : accepté pour la réparation globale demandée le 12 novembre 2026.
Précise les ADR 0001 (file), 0003 (provenance et données brutes) et 0006 (frontières).

## Décision

Une demande `{"kind":"repair_images"}` partage la file et le worker unique. Les
collectes historiques sans `kind` restent compatibles. Le JSON des paramètres
permet cette distinction sans modifier le schéma SQL.

La réparation concerne toutes les impressions existantes. Core sélectionne les
médias à compléter derrière des ports typés ; scraping gère les fichiers et HTTP ;
persistence met à jour uniquement les colonnes d’images. Une URL découverte est
conservée même si le téléchargement échoue. La réponse source n’est pas enregistrée
comme nouvelle observation : identité, données brutes hors prix et date restent
préservées.

Un fichier présent est conservé ; un fichier absent est téléchargé depuis l’URL
connue. Sans URL ni fichier, seule la fiche Pokémon/TCGdex de la même identité et
langue est interrogée. Une indisponibilité source est distincte d’une erreur
technique. Une erreur n’empêche pas le traitement des autres impressions, mais fait
échouer le job. Le stockage et la préparation des fichiers suivent les garanties
de la collecte, notamment pour les impressions à plusieurs images.

## Conséquences et validation

L’historique et l’interface distinguent collecte et réparation. Aucun nouvel
ordonnanceur, service ou connecteur n’est ajouté. Une réparation relancée ignore
les fichiers présents ; elle ne vérifie pas leur intégrité et ne redécouvre pas
les URL connues devenues invalides. Le timeout du worker reste applicable.

Tests de soumission/exécution, SQL ciblé, HTTP local, WebP, erreurs, reprise et
parcours admin FR/EN/ES ; vérification des installations séparées et de la pile
PostgreSQL temporaire.
