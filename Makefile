.PHONY: dev generate test stop

dev:
	docker compose up --build

generate:
	curl -X POST http://localhost:8000/api/generate -H 'Content-Type: application/json' -d '{"prompt":"Build an FAQ chatbot"}'

test:
	cd apps/orchestrator-backend && pytest -q

stop:
	docker compose down
