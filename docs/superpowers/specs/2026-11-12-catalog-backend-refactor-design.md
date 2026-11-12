# Refactoring du catalogue backend

> Document historique de la première tranche catalogue. L’organisation et les
> imports ont ensuite été remplacés par la [refonte globale approuvée](../specs/2026-11-12-project-structure-design.md),
> précisée par l’[ADR 0006](../../adr/0006-separated-applications.md).


Statut : approuvé par l’utilisateur le 12 novembre 2026. Périmètre : catalogue backend.

## Intention

Faciliter les évolutions et clarifier le code en séparant présentation HTTP,
consultation SQL et enregistrement des observations. Le comportement public de
l’admin et de la collecte reste identique.

## Approches examinées

- **Catalogue backend — retenu par l’utilisateur.** Retirer les URLs HTTP des cas
  d’usage et isoler les lectures SQL. Ce périmètre corrige un couplage concret et
  permet de faire évoluer les requêtes sans parcourir la logique transactionnelle.
- **Filtres et pagination frontend.** Regrouper la lecture et la modification des
  paramètres d’URL du catalogue. Utile pour la lisibilité de l’interface, mais
  indépendant du périmètre backend retenu.
- **Les deux successivement.** Couverture plus large, avec davantage de changements
  à vérifier ; non retenu pour cette tranche.

## Découpage proposé

Ces choix d’implémentation sont proposés par l’agent.

1. `application/catalog.py` conserve le port de consultation et les cas d’usage.
   Il renvoie les observations sans construire de route `/api/images/` et sans
   modifier les données fournies par le lecteur.
2. `interfaces/catalog_presenter.py` prend en charge la projection des images
   locales vers leurs URLs HTTP encodées, pour la liste et le détail. Les URLs
   source restent disponibles dans le détail. Les schémas de réponse existants
   continuent de définir les champs publics.
3. `infrastructure/catalog_reader.py` regroupe les requêtes de consultation,
   jointures, filtres, pagination, facettes, contrôle de présence et parcours des
   observations. Il utilise le moteur SQL partagé, sans en gérer la fermeture.
4. `infrastructure/catalog.py` conserve `Repository`, la création et la fermeture
   du moteur, ainsi que les écritures transactionnelles. Les méthodes publiques
   de lecture délèguent au lecteur SQL. Les imports de compatibilité, signatures
   et accès à `engine` restent utilisables par les appelants existants.

Le contrôle de disponibilité reste une opération de lecture SQL. Les règles de
fusion des résumés d’extension et de bloc sont conservées telles quelles. Aucun
dépôt générique, nouvelle dépendance, évolution de schéma ou migration n’est prévu.
Cette organisation applique les ADR 0001 et 0002 ; `docs/architecture.md` sera
actualisé avec les responsabilités des modules.

## Exemples d’acceptation

- Étant donné une impression avec plusieurs fichiers locaux et des URLs source,
  quand la liste et le détail sont consultés par HTTP, alors les URLs locales sont
  encodées et ordonnées comme auparavant, et le détail conserve les URLs source.
- Étant donné un chemin d’image comportant espaces, accents ou caractères réservés,
  quand son URL est suivie, alors le fichier local attendu est servi.
- Étant donné un lecteur réutilisant ses observations, quand un cas d’usage puis
  la présentation HTTP les consultent, alors les données d’origine restent intactes.
- Étant donné des impressions de sources et langues différentes, quand recherche,
  filtres et pagination sont appliqués, alors identités, résultats, ordre et totaux
  restent identiques ; une impression absente reste une réponse HTTP 404.
- Étant donné un détail d’extension ou de bloc déjà enregistré, quand un résumé
  partiel arrive, alors les métadonnées conservées le restent après extraction.
- Étant donné une observation à réindexer, quand elle est enregistrée, alors les
  garanties existantes sur provenance, fichiers et date de collecte sont préservées.

## Réalisation et validation

Procéder par petites tranches : caractériser les contrats HTTP, déplacer la
présentation, puis extraire les lectures SQL sous tests verts. Ajouter des tests
de comportement aux frontières publiques, sans tester les méthodes privées.
Pour tout nouveau contrat testé, vérifier d’abord son échec pertinent, puis son
succès ; les comportements déjà couverts servent de garde-fou au déplacement.

Exécuter les tests ciblés, puis `make test`. Vérifier aussi le parcours de
persistance avec `make docker-build` et `make docker-test`, dans le projet
temporaire isolé prévu par le dépôt. Ne pas arrêter les workers de l’installation
personnelle. Aucun commit ni publication n’est prévu.

Point de départ vérifié le 12 novembre 2026 : 39 tests Python, 8 tests frontend,
Ruff, Prettier et build réussis. Le test HTTP local nécessite une exécution
autorisant l’ouverture de son port de boucle locale.
