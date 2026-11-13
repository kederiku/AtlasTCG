# ADR 0009 — Préparer et exécuter une collecte par bloc ou extension

Statut : accepté le 13 novembre 2026. Complète les ADR 0001, 0005, 0006 et 0007.

## Problème

Le nombre maximal de candidats ne permet pas de demander une extension complète.
Les blocs/extensions du catalogue local ne suffisent pas à préparer leur première
collecte. Une liste source peut varier selon les langues et le moment d’exécution.

## Décision

Ajouter `ScopedCollectionRequest(kind="collect_scope")` : langues, `force`, un
`scope` de type `block` ou `set` et son code source. Aucun nombre maximal ni liste
de cartes dans cette variante. Garder les demandes historiques et la réparation
distinctes ; leur JSON enregistré ne nécessite pas de migration.

Dans Collectes, un port de découverte fournit des choix localisés ; un cas d’usage
les groupe et choisit leurs noms selon l’ADR 0007. L’adaptateur HTTP de l’API lit
TCGdex avec concurrence, délais et taille bornés. Ces lectures de préparation ne
créent pas d’observation ni de cache persistant et n’importent jamais le scraping.
L’admin propose deux listes liées et un cache React Query de cinq minutes.

La soumission persiste les paramètres sans réseau. À l’exécution, le spider lit
la liste des extensions d’un bloc et les cartes de chaque extension, dans chaque
langue. L’expansion du périmètre est explicite : lire le bloc pour enrichir une
extension n’implique pas de collecter ses autres extensions. Aucune appartenance
n’est déduite du préfixe d’un code. Les codes à point sont acceptés.

## Conséquences et limites

Un 404 sur le périmètre racine signale une langue indisponible ; aucune langue
disponible fait échouer le job. Une ressource annoncée mais introuvable, une réponse
incohérente ou une erreur technique persistante fait échouer la collecte et conserve
les résultats partiels. La disponibilité affichée n’est pas une garantie future.
Le timeout d’une heure et le débit existant restent inchangés ; aucun découpage
automatique. Réexécuter le périmètre sans actualisation ignore les cartes présentes.

Le formulaire exige une cible et ne peut pas passer implicitement d’une extension
disparue à tout son bloc. « Tous les blocs » filtre les choix, sans demander une
collecte globale. Les identifiants précis restent disponibles en mode avancé.

## Validation

BDD de soumission persistée ; API sur serveur HTTP local (noms, admissibilité,
404, erreurs, délais, tailles) ; spider réel (plus de dix cartes, extension isolée,
langues, cohérence, actualisation) ; React multilingue, changements et réponses
tardives ; parcours navigateur, contrôles complets et installations indépendantes.
