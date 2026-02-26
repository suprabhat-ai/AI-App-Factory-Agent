from __future__ import annotations

import asyncio
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from sse_starlette.sse import EventSourceResponse

from .pipeline import PipelineRunner

app = FastAPI(title="AI App Factory Orchestrator")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

runner = PipelineRunner(Path(__file__).resolve().parents[3])


class GenerateRequest(BaseModel):
    prompt: str
    app_slug: str | None = None


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


@app.post("/api/generate")
async def generate(req: GenerateRequest) -> dict:
    job = runner.create_job(req.prompt, req.app_slug)
    asyncio.create_task(runner.run_job(job))
    return {"job_id": job.job_id, "app_slug": job.app_slug}


@app.get("/api/status/{job_id}")
def status(job_id: str) -> dict:
    job = runner.jobs.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job.to_dict()


@app.get("/api/stream/{job_id}")
async def stream(job_id: str):
    async def event_generator():
        cursor = 0
        while True:
            job = runner.jobs.get(job_id)
            if not job:
                break
            if cursor < len(job.logs):
                for line in job.logs[cursor:]:
                    yield {"event": "log", "data": line}
                cursor = len(job.logs)
            if job.status in {"completed", "failed"}:
                yield {"event": "done", "data": job.status}
                break
            await asyncio.sleep(1)

    return EventSourceResponse(event_generator())
