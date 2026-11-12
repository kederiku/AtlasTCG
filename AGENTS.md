# Instructions du dépôt

## Références

Lire [CONTEXT.md](CONTEXT.md) pour le vocabulaire, [les règles d’ingénierie](docs/engineering.md)
et [l’index des ADR](docs/adr/README.md) pour les décisions du périmètre concerné.
[CONTRIBUTING.md](CONTRIBUTING.md) décrit les environnements et contrôles ;
[l’architecture](docs/architecture.md) indique où placer le changement.
Ces documents sont les références communes. Les instructions ci-dessous rendent
leur application explicite pour un agent ; ne pas créer de conventions divergentes.

## Démarche de craftsmanship

Avant de modifier le code, examiner l’état du dépôt, les tests existants et le
comportement concerné. Préserver le travail déjà présent. Définir le résultat
observable attendu, les invariants à préserver et la plus petite tranche livrable.
Réutiliser les décisions déjà validées ; clarifier seulement les ambiguïtés qui
changent le comportement métier ou le périmètre.

### DDD — partir du métier et protéger ses frontières

- Employer le langage de `CONTEXT.md` dans les noms, exemples et tests. Distinguer
  les contextes Catalogue et Collectes ; ne pas confondre demande et exécution.
- Placer modèles, invariants et cas d’usage dans `packages/core`. Les cas d’usage
  dépendent de ports métier typés, sans HTTP, SQL, Scrapy, fichiers ou processus.
- Placer les adaptateurs SQL dans `packages/persistence`, HTTP dans `apps/api`,
  acquisition et exécution dans `apps/scraping`, interface dans `apps/frontend`.
  L’API et le scraping ne s’importent pas mutuellement et gardent leurs dépendances séparées.
- Garder les règles métier hors des routes et des composants techniques. Les
  points d’entrée assemblent les adaptateurs et possèdent leurs ressources.
  Les normalisations de source restent pures ; aucune logique Pokémon n’est
  imposée aux autres jeux.
- Modéliser identités, valeurs et invariants quand le métier le justifie. Ne pas
  ajouter agrégat, couche, bus d’événements ou abstraction générique par principe.

### BDD — décrire le comportement par des exemples

- Formuler les comportements dans le langage du domaine : **Étant donné / Quand /
  Alors**, avec des données concrètes et des résultats observables.
- Couvrir le parcours nominal et les erreurs ou limites pertinentes. Expliquer
  ce que l’utilisateur ou le système obtient, sans décrire les méthodes privées.
- S’appuyer sur [le contrat d’acceptation](docs/acceptance.md). Utiliser les scénarios
  Gherkin de `tests/acceptance/features/` pour les parcours métier concernés ; ne
  pas transformer chaque test unitaire en scénario Gherkin.

### ATDD — rendre l’acceptation exécutable avant l’implémentation

- Déduire les critères d’acceptation de la demande et des exemples BDD avant de
  coder. Rendre explicites les hypothèses qui influencent ces critères.
- Pour chaque nouveau comportement, écrire ou adapter un test d’acceptation à la
  frontière appropriée : cas d’usage, API, parcours UI ou résultat de collecte.
  Observer son échec attendu avant l’implémentation.
- Garder ce test comme fil conducteur jusqu’à la livraison. Un même test peut
  servir l’acceptation et la boucle TDD ; ne pas dupliquer les assertions par rituel.

### TDD — avancer par cycles rouge, vert, refactoring

1. **Rouge** : écrire le plus petit test du prochain comportement et l’exécuter.
   Vérifier qu’il échoue pour la raison attendue, pas à cause d’un import, d’une
   fixture invalide ou d’un environnement cassé. Pour un bug, reproduire la régression.
2. **Vert** : ajouter uniquement le code nécessaire pour faire passer ce test,
   puis exécuter les tests du périmètre affecté. Ne pas anticiper d’autres fonctionnalités.
3. **Refactoring** : clarifier les noms, responsabilités et duplications sans
   changer le comportement ; conserver les tests verts, puis passer à la tranche suivante.

Ne pas écrire toute l’implémentation puis ajouter les tests après coup. Pour un
refactoring sans changement de comportement, partir des tests verts existants ;
ajouter d’abord des tests de caractérisation si le comportement n’est pas couvert,
sans inventer un échec artificiel. Pour une modification documentaire seule,
vérifier les liens, commandes et exemples concernés, sans tests artificiels.

## Qualité du code et des tests

- Favoriser des responsabilités cohérentes, des noms explicites et des interfaces
  petites. Appliquer simplicité et absence de fonctionnalités spéculatives ; ne
  généraliser que des règles réellement communes, pas une ressemblance de code.
- Tester les contrats publics et effets observables. Ne pas verrouiller la forme
  privée du code, les appels entre helpers ou les détails d’un ORM. Un refactoring
  interne préservant le contrat doit pouvoir garder les mêmes tests.
- Utiliser des données déterministes, des bases temporaires réelles pour SQL,
  des fixtures de source et un serveur HTTP local pour la collecte. Simuler les
  frontières externes, pas chaque classe interne ; ne pas tester les mocks eux-mêmes.
- Choisir le niveau de test le plus simple qui démontre le comportement. Vérifier
  PostgreSQL quand ses différences avec SQLite comptent. Ne pas ajouter des tests
  uniquement pour atteindre un nombre ou un pourcentage de couverture.
- Conserver les contrats typés et la validation aux frontières. Ne pas masquer un
  défaut par un `Any`, un cast, une exception ignorée ou la désactivation d’un contrôle.
- Retirer le code, les exports et les dépendances devenus inutiles après vérification
  de leurs usages, y compris configuration et points d’entrée. Mettre la documentation
  à jour avec le code ; ajouter un ADR pour une décision structurante en précisant
  les décisions antérieures qu’elle complète ou remplace.

## Garde-fous du dépôt

- Préserver identités localisées, provenance, fichiers et dates de collecte.
  Les prix sont exclus de toutes les observations, y compris les données brutes.
- Ajouter une migration plutôt que modifier celles déjà appliquées. Ne pas
  réinitialiser une base ni supprimer de volume pour faire passer un test.
- Consulter l’état des collectes avant un arrêt de worker ; préserver les travaux
  actifs. Ne pas lancer simultanément les workers de l’hôte et de Docker.
- Ne pas versionner `.env`, `data/`, caches ou dépendances installées ; ne pas
  afficher les secrets dans les commandes de diagnostic.
- Ne pas créer de commit, publier ou envoyer de message externe sans demande.

## Commandes Make autorisées pour un agent

Exécuter les commandes depuis la racine. `make` seul et `make help` affichent
l’aide, sans démarrer de service. Lire les recettes avant d’utiliser une cible
nouvelle ou modifiée ; un nom de commande ne suffit pas à connaître ses effets.

Les commandes suivantes sont autorisées sans confirmation supplémentaire quand
elles servent la tâche en cours :

| Commandes | Usage et limites |
|---|---|
| `make help` | Découvrir les commandes disponibles. |
| `make status`, `make logs` | Consulter la pile ; les logs sont limités aux 100 dernières lignes par service. Ne pas exposer de secrets. |
| `make logs-follow` | Suivre un diagnostic en direct, puis terminer le suivi ; cela n’arrête pas les services. |
| `make install` | Installer les dépendances verrouillées ; ne pas mettre les versions à jour implicitement. |
| `make lint`, `make format-check`, `make typecheck` | Contrôler sans réécrire les sources ; mypy strict porte sur core. |
| `make test-python`, `make test-frontend` | Exécuter les suites ciblées sans collecter chez un fournisseur. |
| `make test` | Exécuter tous les contrôles locaux et le build frontend. |
| `make test-installations` | Tester quatre environnements Python temporaires indépendants. |
| `make build` | Générer le build frontend local. |
| `make format` | Trier les imports et formater Python/frontend ; relire le diff et préserver le travail existant. La cible traite toutes les sources. |
| `make docker-build` | Construire les images locales ; ne redémarre aucun service existant. |
| `make docker-test` | Tester les images déjà construites dans un projet temporaire unique ; seul ce projet et ses données sont nettoyés. |

Les commandes suivantes agissent sur l’environnement d’exécution. Les utiliser
si la demande couvre cet effet et l’environnement ciblé ; une autorisation déjà
donnée reste valable et ne doit pas être redemandée. Sinon, demander l’accord
uniquement pour cette action, après avoir terminé les travaux indépendants :

| Commandes | Conditions |
|---|---|
| `make up` | Démarrage ou mise à jour de la pile demandé ; peut migrer la base, recréer des services et lancer des collectes en attente. Vérifier les travaux actifs avant une mise à jour. |
| `make down` | Arrêt de la pile demandé, après vérification des collectes ; conserve les volumes mais interrompt un travail actif. |
| `make db` | Démarrage de PostgreSQL local nécessaire à l’environnement demandé ; vérifier le projet et le port. |
| `make migrate` | Migration autorisée sur la base choisie dans `.env` ; suivre sauvegarde et arrêt des collectes dans le guide d’exploitation. Jamais pour réparer un test sur la base personnelle. |
| `make api`, `make admin`, `make dev` | Serveurs nécessaires au développement ou à la vérification demandée ; vérifier ports et configuration, éviter les doublons avec Docker. |
| `make worker` | Exécution des collectes demandée ; la cible consomme immédiatement les demandes en attente. Aucun worker Docker concurrent. |

Ne pas ajouter ni exécuter de cible de purge, réinitialisation de base, suppression
de volume réel, publication ou commit sans demande explicite. Ne pas contourner
ces conditions avec une commande directe ou une surcharge de variables Make.
Cette liste est une règle de travail pour l’agent, pas un contrôle d’accès technique.

## Vérifications

Pour un changement de code, terminer par `make test` : Ruff, mypy strict sur core,
pytest/BDD, Prettier, Vitest et build frontend. Un test ciblé vert ne suffit pas
à conclure que la suite complète passe.

- Paquets, dépendances ou frontières Python modifiés : `make test-installations`.
- Docker, stockage, packaging ou déploiement modifiés :
  `make docker-build && make docker-test`.
- Présentation ou parcours UI modifié : vérifier aussi le parcours navigateur.

Les tests ordinaires ne dépendent pas de l’API TCGdex. Les tests de pile utilisent
un projet temporaire unique et ne doivent jamais cibler la base personnelle.

## Critères de livraison

- Les exemples d’acceptation du périmètre sont satisfaits et les invariants préservés.
- Les frontières métier et applicatives restent respectées ; les changements
  peuvent être compris sans connaître l’historique de la conversation.
- Les vérifications requises ont été exécutées sur l’état final et leurs résultats
  lus. Ne jamais annoncer un contrôle réussi sans l’avoir exécuté ; signaler les
  échecs, limites et contrôles non réalisés, avec leur raison.
- La réponse de livraison décrit ce qui a changé, pourquoi, et les vérifications
  effectuées. Les documents concernés reflètent le comportement livré.

## État du produit

Admin local sans comptes utilisateurs. PostgreSQL, API/frontend et worker via
Compose ; migration préalable. Un seul connecteur réel : Pokémon/TCGdex. Un contrat
compatible avec un jeu ne signifie pas que son spider ou ses données existent.
