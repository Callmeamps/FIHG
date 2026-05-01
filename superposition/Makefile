.PHONY: help run test seed lint clean

help:
	@echo "Superposition — available targets:"
	@echo "  run    — start the FastAPI backend (uvicorn)"
	@echo "  test   — run all tests"
	@echo "  seed   — seed the database with sample data (dry run first)"
	@echo "  lint   — check Python syntax"
	@echo "  clean  — remove sqlite db and __pycache__"

run:
	uv run uvicorn main:app --host 127.0.0.1 --port 8000 --reload

test:
	uv run pytest tests/ -v

seed:
	uv run python scripts/seed.py --dry-run
	@echo "Run 'make seed-apply' to write, or 'make seed-apply SEED_APPLY=1'"

seed-apply:
	uv run python scripts/seed.py --apply

seed-clear:
	uv run python scripts/seed.py --clear

lint:
	uv run python -m py_compile main.py superposition/*.py scripts/*.py

clean:
	rm -f superposition.db
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -type f -name "*.pyc" -delete 2>/dev/null || true