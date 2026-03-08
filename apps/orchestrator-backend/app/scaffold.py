from __future__ import annotations

import json
import os
import socket
from pathlib import Path


def _next_free_port(start: int = 3000, end: int = 9999) -> int:
    for port in range(start, end):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    raise RuntimeError("No free ports available")


def parse_prompt_to_spec(prompt: str) -> dict:
    normalized = prompt.lower()
    features = ["chat interface", "message history", "health and readiness checks"]
    if "faq" in normalized:
        features.append("faq style responses")
    if "multimodal" in normalized:
        features.append("multimodal response planner")
    if "workflow" in normalized or "automation" in normalized:
        features.append("task orchestration workflows")

    objectives = [
        "Deliver trustworthy answers with explicit reasoning steps.",
        "Minimize hallucinations with deterministic fallback behavior.",
        "Provide clear UX states for loading, success, and failure.",
    ]

    guardrails = [
        "Never execute unsafe user instructions.",
        "Request clarification for ambiguous or high-risk tasks.",
        "Fail closed with an explainable fallback response.",
    ]

    return {
        "name": prompt.strip().split("\n", maxsplit=1)[0][:60] or "AI App",
        "description": prompt.strip(),
        "features": features,
        "objectives": objectives,
        "guardrails": guardrails,
        "quality_bar": ["reliable", "observable", "testable", "secure-by-default"],
        "pages": ["/"],
        "endpoints": ["GET /health", "GET /ready", "POST /api/chat"],
    }


def write_generated_app(base_dir: Path, app_slug: str, spec: dict) -> dict:
    app_dir = base_dir / "generated_apps" / app_slug
    backend_port = _next_free_port(8100, 8999)
    frontend_port = _next_free_port(3100, 3999)

    backend_dir = app_dir / "backend"
    frontend_dir = app_dir / "frontend"
    tests_dir = backend_dir / "tests"
    pw_dir = frontend_dir / "tests"

    for directory in [backend_dir / "app", frontend_dir / "app", tests_dir, pw_dir]:
        directory.mkdir(parents=True, exist_ok=True)

    (app_dir / ".env.example").write_text(
        "OPENAI_API_KEY=\nOPENAI_BASE_URL=https://api.openai.com/v1\n",
        encoding="utf-8",
    )

    (backend_dir / "requirements.txt").write_text(
        "fastapi==0.115.6\nuvicorn==0.32.1\nhttpx==0.28.1\npytest==8.3.4\n",
        encoding="utf-8",
    )

    (backend_dir / "app" / "main.py").write_text(
        f'''import os\nfrom fastapi import FastAPI\nfrom pydantic import BaseModel\n\napp = FastAPI(title="{app_slug} backend")\n\n\nclass ChatRequest(BaseModel):\n    message: str\n\n\ndef _deterministic_agent_response(message: str) -> str:\n    strategy = "analyze -> plan -> answer -> validate"\n    return f"agent::{app_slug}::strategy={{strategy}}::message={{message}}"\n\n\n@app.get("/health")\ndef health():\n    return {{"status": "ok"}}\n\n\n@app.get("/ready")\ndef ready():\n    return {{"status": "ready"}}\n\n\n@app.post("/api/chat")\ndef chat(req: ChatRequest):\n    if not os.getenv("OPENAI_API_KEY"):\n        return {{"response": _deterministic_agent_response(req.message), "mode": "stub"}}\n    return {{"response": f"live-mode-not-implemented::{{req.message}}", "mode": "live"}}\n''',
        encoding="utf-8",
    )

    (tests_dir / "test_api.py").write_text(
        '''from fastapi.testclient import TestClient\nfrom app.main import app\n\nclient = TestClient(app)\n\n\ndef test_health():\n    r = client.get("/health")\n    assert r.status_code == 200\n\n\ndef test_chat():\n    r = client.post("/api/chat", json={"message": "hello"})\n    assert r.status_code == 200\n    assert "response" in r.json()\n''',
        encoding="utf-8",
    )

    (frontend_dir / "package.json").write_text(
        json.dumps(
            {
                "name": f"{app_slug}-frontend",
                "private": True,
                "scripts": {
                    "dev": "next dev -p $PORT",
                    "build": "next build",
                    "start": "next start -p $PORT",
                    "test": "playwright test",
                },
                "dependencies": {
                    "next": "15.0.4",
                    "react": "19.0.0",
                    "react-dom": "19.0.0",
                },
                "devDependencies": {
                    "@playwright/test": "1.49.0",
                    "typescript": "5.7.2",
                    "@types/react": "19.0.1",
                    "@types/node": "22.10.1",
                },
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    (frontend_dir / "app" / "page.tsx").write_text(
        f'''"use client";\nimport {{ useState }} from "react";\n\nconst backend = process.env.NEXT_PUBLIC_BACKEND_URL || "http://localhost:{backend_port}";\n\nexport default function Home() {{\n  const [message, setMessage] = useState("");\n  const [response, setResponse] = useState("");\n\n  const send = async () => {{\n    const r = await fetch(`${{backend}}/api/chat`, {{\n      method: "POST",\n      headers: {{ "Content-Type": "application/json" }},\n      body: JSON.stringify({{ message }}),\n    }});\n    const data = await r.json();\n    setResponse(data.response || "");\n  }};\n\n  return (\n    <main style={{{{padding: 20}}}}>\n      <h1>{spec['name']}</h1>\n      <textarea value={{message}} onChange={{(e) => setMessage(e.target.value)}} />\n      <button onClick={{send}}>Send</button>\n      <pre>{{response}}</pre>\n    </main>\n  );\n}}\n''',
        encoding="utf-8",
    )

    (pw_dir / "smoke.spec.ts").write_text(
        '''import { test, expect } from "@playwright/test";\n\ntest("chat ui loads", async ({ page }) => {\n  await page.goto("/");\n  await expect(page.getByRole("button", { name: "Send" })).toBeVisible();\n});\n''',
        encoding="utf-8",
    )

    (frontend_dir / "playwright.config.ts").write_text(
        f'''import {{ defineConfig }} from "@playwright/test";\n\nexport default defineConfig({{\n  testDir: "./tests",\n  use: {{\n    baseURL: "http://127.0.0.1:{frontend_port}",\n    headless: true,\n  }},\n  webServer: {{\n    command: "PORT={frontend_port} npm run dev",\n    url: "http://127.0.0.1:{frontend_port}",\n    reuseExistingServer: true,\n    timeout: 120000,\n  }},\n}});\n''',
        encoding="utf-8",
    )

    (app_dir / "docker-compose.yml").write_text(
        f'''services:\n  backend:\n    image: python:3.11-slim\n    working_dir: /app\n    command: sh -c "pip install -r requirements.txt && uvicorn app.main:app --host 0.0.0.0 --port {backend_port}"\n    volumes:\n      - ./backend:/app\n    ports:\n      - "{backend_port}:{backend_port}"\n\n  frontend:\n    image: node:20-alpine\n    working_dir: /app\n    command: sh -c "npm install && PORT={frontend_port} NEXT_PUBLIC_BACKEND_URL=http://backend:{backend_port} npm run dev"\n    volumes:\n      - ./frontend:/app\n    ports:\n      - "{frontend_port}:{frontend_port}"\n    depends_on:\n      - backend\n''',
        encoding="utf-8",
    )

    (app_dir / "README.md").write_text(
        f"""# {app_slug}\n\n## Setup\n1. Copy `.env.example` to `.env` and set `OPENAI_API_KEY` optionally.\n2. Run `docker compose up --build`.\n\n## Run\n- Frontend: http://localhost:{frontend_port}\n- Backend: http://localhost:{backend_port}\n- Docs: http://localhost:{backend_port}/docs\n\n## Validate\n- `curl http://localhost:{backend_port}/health`\n- Send chat message in UI.\n\n## Stop\n- `docker compose down`\n""",
        encoding="utf-8",
    )

    return {
        "app_dir": str(app_dir),
        "frontend_url": f"http://localhost:{frontend_port}",
        "backend_url": f"http://localhost:{backend_port}",
        "docs_url": f"http://localhost:{backend_port}/docs",
        "backend_port": backend_port,
        "frontend_port": frontend_port,
    }


def write_spec_file(app_dir: str, spec: dict) -> None:
    Path(app_dir, "spec.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")


def append_log(log_path: Path, message: str) -> None:
    log_path.parent.mkdir(parents=True, exist_ok=True)
    with log_path.open("a", encoding="utf-8") as handle:
        handle.write(message + os.linesep)
