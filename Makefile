.PHONY: dev test lint browser check smoke docker

PORT ?= 8000

dev:
	python -m art_optimizer.app --host 0.0.0.0 --port $(PORT) --reload

test:
	python -m pytest

lint:
	python -m ruff check .
	python -m compileall -q art_optimizer tests scripts
	for file in art_optimizer/static/*.js; do node --check "$$file"; done

browser:
	node tests/js/test_concept_library.mjs
	node tests/js/test_emergent_tastes.mjs
	node tests/js/test_taste_gallery.mjs
	node tests/js/test_direction_lab.mjs

check: lint browser test

smoke:
	python scripts/smoke_test.py http://127.0.0.1:$(PORT)

docker:
	docker compose up --build
