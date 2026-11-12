.DEFAULT_GOAL := help

.PHONY: help up down logs logs-follow status docker-build docker-test install db migrate \
        build api admin worker dev lint format-check format test typecheck \
        test-python test-frontend test-installations

help: ## Afficher les commandes ; droits des agents dans AGENTS.md
	@awk 'BEGIN {FS = ":.*## "; print "Commandes disponibles :"} /^[a-zA-Z0-9_-]+:.*## / {printf "  %-20s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

up: ## Construire et démarrer la pile locale (peut recréer les services)
	mkdir -p data/images data/jobs/admin
	docker compose up --build -d --wait

down: ## Arrêter la pile locale en conservant les volumes
	docker compose down

logs: ## Lire les 100 dernières lignes par service applicatif
	docker compose logs --tail 100 api worker migrate

logs-follow: ## Suivre les logs applicatifs en continu (Ctrl+C pour quitter)
	docker compose logs --tail 100 -f api worker migrate

status: ## Afficher l’état des services locaux
	docker compose ps --all

docker-build: ## Construire les trois images sans redémarrer la pile
	docker compose build

docker-test: ## Tester les images déjà construites dans une pile temporaire isolée
	python3 scripts/docker_smoke.py

install: ## Installer les dépendances Python et frontend verrouillées
	uv sync --locked --all-packages
	npm ci --prefix apps/frontend

db: ## Démarrer PostgreSQL local sans lancer les applications
	docker compose up -d --wait postgres

migrate: ## Appliquer les migrations à la base choisie dans .env
	uv run --locked --env-file .env alembic upgrade head

build: ## Compiler le frontend dans apps/frontend/dist
	npm run build --prefix apps/frontend

admin: api ## Alias de api

api: ## Lancer l’API hôte et servir le frontend compilé
	TCG_FRONTEND_DIR=apps/frontend/dist uv run --locked --env-file .env uvicorn tcg_api.app:create_app --factory --host 127.0.0.1 --port 8000

worker: ## Lancer le worker hôte ; exécute les demandes en attente
	uv run --locked --env-file .env tcg-worker

dev: ## Lancer Vite sur 127.0.0.1:5173 avec proxy vers l’API
	npm run dev --prefix apps/frontend

lint: ## Vérifier les règles Ruff sans modifier les sources
	uv run --locked ruff check .

format-check: ## Vérifier le formatage Python et frontend
	uv run --locked ruff format --check .
	npm run format:check --prefix apps/frontend

format: ## Trier les imports Python et formater les sources Python/frontend
	uv run --locked ruff check --select I --fix .
	uv run --locked ruff format .
	npm run format --prefix apps/frontend

typecheck: ## Vérifier le typage strict de core avec mypy
	uv run --locked mypy

test-python: ## Exécuter pytest : tests Python, BDD, intégration et architecture
	uv run --locked pytest

test-frontend: ## Exécuter les tests React avec Vitest
	npm test --prefix apps/frontend

test-installations: ## Vérifier les quatre installations Python indépendantes
	python3 scripts/check_installations.py

# Recettes successives : conserver cet ordre même avec make -j, arrêter au premier échec.
test: ## Exécuter lint, formatage, typage, tests Python/frontend et build
	$(MAKE) --no-print-directory lint
	$(MAKE) --no-print-directory format-check
	$(MAKE) --no-print-directory typecheck
	$(MAKE) --no-print-directory test-python
	$(MAKE) --no-print-directory test-frontend
	$(MAKE) --no-print-directory build
