.PHONY: up down restart logs ps test lint fmt migrate seed backup restore openapi clean

COMPOSE = docker compose -f deploy/docker-compose.yml --env-file .env

up:
	$(COMPOSE) --profile core up -d --build

down:
	$(COMPOSE) --profile core down

restart: down up

logs:
	$(COMPOSE) logs -f

ps:
	$(COMPOSE) ps

stats:
	docker stats --no-stream

migrate:
	$(COMPOSE) run --rm migrate alembic upgrade head

seed:
	$(COMPOSE) run --rm migrate python -m app.seed.categories

test:
	@echo "Running backend unit tests..."
	cd api && uv run pytest -v
	@echo "Running worker tests..."
	cd worker && uv run pytest -v
	@echo "Running frontend tests..."
	cd web && pnpm test -- --run

lint:
	@echo "Linting backend & worker..."
	cd api && uv run ruff check .
	cd worker && uv run ruff check .
	@echo "Type checking backend & worker..."
	cd api && uv run mypy app
	cd worker && uv run mypy app
	@echo "Linting frontend..."
	cd web && pnpm lint

fmt:
	cd api && uv run ruff format .
	cd worker && uv run ruff format .
	cd web && pnpm format

openapi:
	cd api && uv run python -m app.scripts.export_openapi > ../docs/openapi.json

backup:
	@mkdir -p backups
	@FILE=backups/mytube_backup_$$(date +%Y%m%d_%H%M%S).sql.gz; \
	docker exec -t mytube-postgres pg_dump -U mytube -d mytube | gzip > $$FILE; \
	echo "Backup written to $$FILE"

clean:
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type d -name ".pytest_cache" -exec rm -rf {} +
	find . -type d -name ".ruff_cache" -exec rm -rf {} +
	find . -type d -name ".mypy_cache" -exec rm -rf {} +
