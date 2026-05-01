# Selfdroid — Makefile
up:
	docker compose up -d --build

down:
	docker compose down

test:
	cd src && ./virtualenv/bin/python -m pytest tests/ -v --tb=short
