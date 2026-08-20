.PHONY: dev test lint check smoke docker

PORT ?= 8000

dev:
	python -m art_optimizer.app --host 0.0.0.0 --port $(PORT) --reload

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m compileall -q art_optimizer tests scripts
	node --check art_optimizer/static/app.js

check: lint test

smoke:
	python scripts/smoke_test.py http://127.0.0.1:$(PORT)

docker:
	docker compose up --build
