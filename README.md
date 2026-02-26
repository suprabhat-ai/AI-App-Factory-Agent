# AI App Factory Agent

Local-first factory that generates full-stack AI apps (FastAPI + Next.js) from a prompt, tests them, repairs failures (up to 5 loops), documents them, and runs them with docker compose.

## Architecture
- `apps/console-frontend`: Next.js TypeScript chat console.
- `apps/orchestrator-backend`: FastAPI orchestrator with generation pipeline.
- `packages/scaffold`: scaffold/template notes.
- `generated_apps/<app_slug>/`: generated app outputs.
- `logs/`: persistent job logs mirrored to UI stream.

## Prerequisites
- Docker + Docker Compose plugin
- Node.js 20+ (for local non-docker runs)
- Python 3.11+

## Setup
```bash
git clone <repo>
cd ai-app-factory
cp .env.example .env
```
Optional AI settings:
- `OPENAI_API_KEY` for compatible provider.
- `OPENAI_BASE_URL` for non-default endpoints.

Without key, generated apps run in deterministic stub mode.

## Run the factory
```bash
docker compose up --build
```
- Console UI: http://localhost:3000
- Orchestrator API: http://localhost:8000
- Orchestrator health: http://localhost:8000/health

## Generate an app
### Via UI
1. Open http://localhost:3000
2. Enter prompt (e.g., "Build an FAQ chatbot").
3. Click **Generate App**.
4. Watch live logs and final URLs.

### Via curl
```bash
curl -X POST http://localhost:8000/api/generate \
  -H 'Content-Type: application/json' \
  -d '{"prompt":"Build an FAQ chatbot","app_slug":"faq-chatbot"}'
```
Then poll:
```bash
curl http://localhost:8000/api/status/<job_id>
```

## Pipeline behavior
1. Parse prompt into structured spec.
2. Create `generated_apps/<app_slug>/`.
3. Generate backend + frontend code.
4. Generate backend/frontend tests.
5. Run tests (`pytest -q`, `npx playwright test`).
6. Auto-patch and retry up to 5 iterations.
7. Choose free ports automatically and run generated app `docker compose up -d --build`.
8. Poll `/health` until ready.
9. Return frontend/backend/docs URLs + checklist.

## Validation steps
After generation completes:
- Open returned frontend URL and send a message.
- `curl <backend_url>/health` returns `{"status":"ok"}`.
- Open `<backend_url>/docs` and confirm OpenAPI page.

## Stop commands
Stop factory services:
```bash
docker compose down
```
Stop generated app:
```bash
cd generated_apps/<app_slug>
docker compose down
```

## Troubleshooting
- **Port conflicts**: pipeline auto-selects free ports; stop stale containers if host ports are occupied.
- **Docker socket errors**: ensure `/var/run/docker.sock` exists and Docker daemon is running.
- **node_modules issues**: remove `node_modules` and rerun install.
- **Missing browsers for Playwright**: run `npx playwright install` in generated frontend.
- **No OPENAI_API_KEY**: stub response mode is expected and deterministic.

## Make targets
- `make dev`: run factory stack.
- `make generate`: sample generation request.
- `make test`: run orchestrator unit tests.
- `make stop`: stop factory stack.
