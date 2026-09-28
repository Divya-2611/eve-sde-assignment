.PHONY: up dev test lint migrate seed seed-docker down web web-install web-build web-preview

up:
	docker compose up --build

dev:
	uv run uvicorn app.main:app --reload

test:
	uv run pytest -v

lint:
	uv run ruff check app tests

migrate:
	uv run alembic upgrade head

seed:
	uv run python -m app.seed

# Seed through the compose network (use when a local postgres shadows
# localhost:5432 — host-side DATABASE_URL can't reach the db container).
seed-docker:
	docker compose exec api uv run --frozen --no-sync python -m app.seed

down:
	docker compose down

web-install: frontend/node_modules

frontend/node_modules: frontend/package.json frontend/package-lock.json
	npm --prefix frontend ci

web: frontend/node_modules
	npm --prefix frontend run dev

web-build: frontend/node_modules
	npm --prefix frontend run build

web-preview:
	npm --prefix frontend run preview
