.PHONY: install run-api run-worker test lint up down logs

install:
	python3 -m venv .venv
	. .venv/bin/activate && pip install --upgrade pip && pip install -r requirements.txt

run-api:
	PYTHONPATH=. uvicorn application.api.main:app --reload --host 0.0.0.0 --port 8000

run-worker:
	PYTHONPATH=. python -m application.worker.main

test:
	PYTHONPATH=. pytest -q

up:
	docker compose up --build

down:
	docker compose down -v

logs:
	docker compose logs -f
