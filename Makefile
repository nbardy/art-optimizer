.PHONY: dev test

dev:
	python -m art_optimizer.app --host 0.0.0.0 --port $${PORT:-8000} --reload

test:
	pytest
