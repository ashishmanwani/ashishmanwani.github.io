.PHONY: help up down build logs migrate makemigrations shell test worker beat flower clean

DOCKER_COMPOSE = docker compose
API_SERVICE = api

help:
	@echo "Price Tracker Backend — Available commands:"
	@echo ""
	@echo "  make up           Start all services (detached)"
	@echo "  make down         Stop all services"
	@echo "  make build        Rebuild Docker images"
	@echo "  make logs         Tail logs from all services"
	@echo "  make migrate      Run Alembic migrations inside API container"
	@echo "  make makemigrations msg='description'  Create a new migration"
	@echo "  make shell        Open bash shell in API container"
	@echo "  make test         Run pytest unit tests"
	@echo "  make worker       Start a local Celery worker (no Docker)"
	@echo "  make beat         Start Celery Beat locally (no Docker)"
	@echo "  make flower       Open Flower UI in browser"
	@echo "  make clean        Remove all volumes and containers"
	@echo "  make env          Copy .env.example to .env"
	@echo ""

env:
	@if [ ! -f .env ]; then cp .env.example .env && echo "Created .env from .env.example — edit it before running make up"; else echo ".env already exists"; fi

up: env
	$(DOCKER_COMPOSE) up -d
	@echo ""
	@echo "Services started:"
	@echo "  API:    http://localhost:8000"
	@echo "  Docs:   http://localhost:8000/docs"
	@echo "  Flower: http://localhost:5555"

down:
	$(DOCKER_COMPOSE) down

build:
	$(DOCKER_COMPOSE) build --no-cache

logs:
	$(DOCKER_COMPOSE) logs -f --tail=100

migrate:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) alembic upgrade head

makemigrations:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) alembic revision --autogenerate -m "$(msg)"

shell:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) /bin/bash

test:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) pytest tests/ -v --tb=short

test-unit:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) pytest tests/unit/ -v --tb=short

clean:
	$(DOCKER_COMPOSE) down -v --remove-orphans
	@echo "All containers and volumes removed."

# ── Local dev (no Docker, uses host PostgreSQL + Redis) ───────────────────────
local-api:
	cd api && uvicorn main:app --reload --host 0.0.0.0 --port 8000

local-worker:
	cd worker && celery -A celery_app worker -Q scrape_normal,scrape_critical --concurrency=1 --loglevel=info

local-beat:
	cd worker && celery -A celery_app beat --loglevel=info

local-migrate:
	alembic upgrade head

# ── Utility ───────────────────────────────────────────────────────────────────
add-user:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python /app/scripts/add_user.py

force-scrape:
	$(DOCKER_COMPOSE) exec $(API_SERVICE) python /app/scripts/force_scrape.py $(product_id)

ps:
	$(DOCKER_COMPOSE) ps
