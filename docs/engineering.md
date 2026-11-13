# Règles et bonnes pratiques

Ces règles décrivent les choix appliqués au projet. Elles servent aux contributions
humaines et aux agents ; une évolution volontaire se documente et se teste.

## DDD : nommer le métier et délimiter les responsabilités

Le [langage commun](../CONTEXT.md) distingue jeu, source, bloc, extension, impression
localisée, face et observation. Deux contextes : Catalogue et Collectes.

- Le domaine définit contrats et invariants, sans FastAPI, SQLAlchemy ou Scrapy.
  Pydantic valide les données ; les Value Objects refusent les champs inattendus.
- Les cas d’usage orchestrent des ports `Protocol`, sans ouvrir une connexion SQL
  ni construire une commande système.
- Les adaptateurs de source sont purs : une réponse et sa langue produisent une
  observation. Les spiders gèrent HTTP, pagination et découverte.
- L’infrastructure réalise persistance, processus et configuration. Les interfaces
  HTTP/CLI assemblent ces composants et traduisent entrées/sorties.
- Garder une architecture proportionnée : pas de bus d’événements, d’agrégat ou de
  dépôt générique ajouté sans comportement métier qui le justifie.

## BDD, ATDD et TDD

**BDD** : exprimer le comportement dans le vocabulaire du domaine, avec des exemples
concrets Étant donné / Quand / Alors. Le [contrat d’acceptation](acceptance.md) décrit
l’expérience attendue ; les `.feature` exécutables vivent dans `tests/acceptance/`.

**ATDD** : préciser les exemples d’acceptation avant d’implémenter une fonctionnalité.
Faire porter les vérifications sur la réponse API, la navigation ou le résultat
d’une collecte, avec des exemples de données représentatifs.

**TDD** : travailler par petites tranches verticales : un test pertinent qui échoue,
le code minimal qui le fait passer, puis un refactoring sous tests verts. Ne pas
écrire une grande batterie basée sur une implémentation encore imaginée.

Tester les contrats observables et les régressions, pas les méthodes privées.
Utiliser une base temporaire réelle pour les tests SQL ; compléter SQLite par
PostgreSQL lorsque la différence de moteur importe. Simuler les frontières externes,
avec fixtures de source et HTTP local, plutôt que mocker chaque classe interne.
Les modifications de documentation seules n’exigent pas de tests artificiels.

## Invariants du catalogue

| Règle | Conséquence |
|---|---|
| Identité `(game, source, source_id, language)` | Pas de fusion par nom ou numéro seul ; langues et sources distinctes. |
| Bloc facultatif, identité par jeu/source/langue | Ne jamais inférer un bloc du préfixe d’un set ; conserver les jeux sans bloc. |
| Code de set stable, nom localisé séparé | Le renommage/traduction ne change ni identité ni chemin d’image. |
| Numéro de collection sous forme de chaîne | Conserver lettres, suffixes et zéros initiaux. |
| Absence distincte de zéro | Pas de PV, coût ou texte inventé ; symboles et textes source conservés. |
| Contrat commun, spécificités par jeu | Faces/coûts/statistiques communs ; détails dans `game_data.<jeu>`. |
| Aucun prix | Filtrage récursif des champs monétaires reconnus, y compris `raw` et variantes. |
| Observation versionnée | Une réindexation ne change pas provenance, images ou date de collecte. |
| Sauvegarde transactionnelle | Une carte et son extension localisée sont écrites ensemble. |

Les observations partielles préservent les champs omis selon les règles de fusion
distinctes des extensions et des blocs, décrites dans [le modèle](catalog-model.md#versions-et-observations).
Les identifiants tiers sont conservés ; ils ne sont pas des évaluations monétaires.
Chaque nouveau connecteur doit tester ses propres champs de prix.

Le catalogue représente les dernières observations, sans historique complet des
règles ni rapprochement canonique automatique entre fournisseurs.

## Images et collecte

Les images sont des WebP locaux dans
`<jeu>/<langue>/<set>/<numéro>-<set>.webp`. Faces suivantes : `-image-2`, etc.
Conversion sans perte à partir du fichier reçu, sans amélioration fictive de qualité.
Les noms sont normalisés de façon stable, avec hash en cas de caractères non sûrs.

Une image absente à la source n’empêche pas de conserver une carte. Un échec de
transfert/conversion d’une image déclarée rejette la nouvelle observation et garde
l’éventuelle version précédente. Pour une impression à plusieurs images, aucune
image de remplacement n’est publiée tant que tous les transferts et conversions
n’ont pas réussi ; un échec conserve aussi les fichiers précédents.
Les cartes déjà au contrat courant sont ignorées
même sans image par la collecte ordinaire. L’action « Réparer les images manquantes »
traite les impressions existantes : URL connue ou recherche dans la fiche TCGdex
si elle manque. Elle conserve les fichiers présents, même anciens, et ne modifie
que les URL et références d’images, sans remplacer l’observation ni sa date. Une
URL découverte reste enregistrée si le téléchargement échoue. Une carte
d’une ancienne version peut être recollectée ; la réindexation permet de remettre
sa projection à jour hors ligne avant de reprendre les collectes.

Les limites de débit, taille, délais et retries sont centralisées. `robots.txt` est
respecté par défaut ; TCGdex possède une exception explicite pour son API documentée.
Activer Playwright seulement lorsque le contenu nécessite JavaScript.

Le frontend soumet des paramètres validés, jamais une commande shell. Un worker
unique exécute les demandes persistées en sous-processus sans shell. Le statut
résulte du code de sortie **et** des statistiques Scrapy, pas du seul code zéro.
Les résultats partiels restent conservés après un échec.
Les consoles Telnet et de contrôle distant Scrapy sont désactivées : l’orchestration
passe par les demandes de collecte, sans serveur d’exécution de code supplémentaire.

## API et frontend

Schémas de réponse explicites : résumé léger en liste, détails à la demande.
Identités encodées dans les URL ; filtres et pagination du catalogue dans la query
string. Une fiche est une page partageable, avec états de chargement et d’erreur.
Les mutations passent par les cas d’usage et les paramètres autorisés.

React + TypeScript, modules par fonctionnalité, React Query pour les données serveur,
React Router pour la navigation, composants shadcn/ui. Préserver labels accessibles,
liens sémantiques, navigation clavier et états vides. Vérifier visuellement les
changements de mise en page en plus des tests de composants.

Les composants UI importent les modules Radix utilisés (`@radix-ui/react-dialog`,
`@radix-ui/react-slot`). Éviter le paquet global `radix-ui` et retirer les composants,
exports, styles et dépendances sans consommateur lors des refactorings.

## Stockage, configuration et exploitation

- Une nouvelle migration par évolution de stockage ; aucune réécriture d’une
  migration déjà appliquée. Ne pas lancer `metadata.create_all` au démarrage réel.
- Migration de données figée, indépendante des adaptateurs applicatifs évolutifs.
  Documenter les suppressions irréversibles et tester les données préexistantes.
- Une fonction de configuration de base partagée entre API, worker, spiders et CLI.
  Aucun secret en code, log, image Docker ou fichier versionné.
- Dépendances verrouillées ; `uv sync --locked`, `npm ci`. Python épinglé et image
  reconstruite lors d’un changement de code. Pas de dépendance téléchargée au démarrage.
- Un seul worker et un stockage de fichiers partagé. Ne pas multiplier les instances
  ni présenter cette architecture locale comme une file distribuée.
- Publication des ports sur `127.0.0.1` uniquement ; pas d’authentification réseau.
  Sauvegarder base et images ensemble avant les changements structurants.

## Définition de terminé

Le comportement demandé est démontré, les tests pertinents passent et les contrôles
Ruff/mypy/Prettier/TypeScript/build sont verts. Pour Docker, exécuter le test de pile
isolée ; pour un changement d’interface, vérifier le parcours navigateur. Actualiser
la documentation et préciser les limites réelles. La CI automatise les contrôles,
mais ne remplace pas une vérification du comportement demandé.

## Frontières vérifiées du dépôt

- `tcg_core` : modèles, règles et cas d’usage, avec Pydantic seulement. Les ports
  métier sont typés ; `mypy --strict` couvre tout le paquet.
- `tcg_persistence` dépend de core et réalise SQL, configuration et maintenance.
- `tcg_api` assemble core/persistence et ses adaptateurs HTTP/fichiers. Ses routes
  appellent les cas d’usage. Il n’importe ni n’installe le paquet scraping.
- `tcg_scraping` assemble core/persistence, Scrapy, médias et processus. Il ne
  dépend pas de FastAPI. Le runner traduit les statistiques techniques en résultat
  métier ; le métier conserve les diagnostics sans interpréter leurs clés.
- Les normalisations de source restent pures. Les requêtes HTTP d’acquisition,
  empreintes Scrapy et pipelines restent dans scraping ; le nommage des images
  reste dans core. La préparation des choix de collecte utilise un adaptateur
  HTTP de l’API derrière un port core, sans enregistrer d’observation (ADR 0009).
- Le frontend compose l’application dans `src/app/`, range types/requêtes/composants
  par fonctionnalité et partage uniquement transport HTTP, formatage et UI générique.

`tests/architecture/` contrôle les imports et les dépendances déclarées.
`make test-installations` vérifie réellement chaque paquet dans un environnement
séparé. Le test Docker contrôle également l’absence des frameworks interdits dans
les images. Une suite verte dans l’environnement complet ne prouve pas l’isolation.
Les versions de migrations vivent dans `packages/persistence/migrations/versions/` ;
un déplacement d’arbre ne justifie pas leur réécriture.
