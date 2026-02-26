from __future__ import annotations

import asyncio
import subprocess
import uuid
from pathlib import Path

import httpx

from .models import JobState
from .scaffold import append_log, parse_prompt_to_spec, write_generated_app, write_spec_file


class PipelineRunner:
    def __init__(self, repo_root: Path):
        self.repo_root = repo_root
        self.jobs: dict[str, JobState] = {}

    def create_job(self, prompt: str, app_slug: str | None = None) -> JobState:
        job_id = str(uuid.uuid4())
        slug = app_slug or f"app-{job_id.split('-')[0]}"
        job = JobState(job_id=job_id, prompt=prompt, app_slug=slug)
        self.jobs[job_id] = job
        return job

    async def run_job(self, job: JobState) -> None:
        log_path = self.repo_root / "logs" / f"{job.job_id}.log"

        def log(message: str) -> None:
            job.logs.append(message)
            append_log(log_path, message)

        job.status = "running"
        try:
            log("1) Parsing prompt into structured spec")
            spec = parse_prompt_to_spec(job.prompt)
            log(f"Spec generated: {spec['name']}")

            log("2) Scaffolding generated app")
            app_info = write_generated_app(self.repo_root, job.app_slug, spec)
            write_spec_file(app_info["app_dir"], spec)

            backend_dir = Path(app_info["app_dir"]) / "backend"
            frontend_dir = Path(app_info["app_dir"]) / "frontend"

            log("3) Running backend tests + frontend tests with iterative repair")
            for attempt in range(1, 6):
                log(f"Test attempt {attempt}/5")
                back = self._run_cmd(["pytest", "-q"], cwd=backend_dir)
                log(back["output"])
                front = self._run_cmd(["sh", "-c", "npm install --silent && npx playwright test"], cwd=frontend_dir)
                log(front["output"])

                if back["ok"] and front["ok"]:
                    log("Tests passed")
                    break

                self._auto_patch(backend_dir, front["output"] + "\n" + back["output"], log)
            else:
                raise RuntimeError("Tests failed after 5 attempts")

            log("4) Starting generated app with docker compose")
            compose = self._run_cmd(["docker", "compose", "up", "-d", "--build"], cwd=Path(app_info["app_dir"]))
            log(compose["output"])

            healthy = await self._wait_for_health(app_info["backend_url"] + "/health")
            if not healthy:
                raise RuntimeError("Generated app did not become healthy in time")

            job.result = {
                "frontend_url": app_info["frontend_url"],
                "backend_url": app_info["backend_url"],
                "docs_url": app_info["docs_url"],
                "validation": [
                    f"Open {app_info['frontend_url']} and send a chat message",
                    f"GET {app_info['backend_url']}/health should return 200",
                    f"Open {app_info['docs_url']}",
                ],
            }
            log("5) Pipeline completed successfully")
            job.status = "completed"
        except Exception as exc:  # noqa: BLE001
            job.status = "failed"
            job.error = str(exc)
            log(f"ERROR: {exc}")

    def _auto_patch(self, backend_dir: Path, test_output: str, log) -> None:
        target = backend_dir / "requirements.txt"
        content = target.read_text(encoding="utf-8")
        if "ModuleNotFoundError" in test_output and "fastapi" in test_output and "fastapi==" not in content:
            target.write_text(content + "\nfastapi==0.115.6\n", encoding="utf-8")
            log("Auto-patched backend requirements with fastapi")

    def _run_cmd(self, cmd: list[str], cwd: Path) -> dict:
        proc = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
        output = (proc.stdout or "") + (proc.stderr or "")
        return {"ok": proc.returncode == 0, "output": f"$ {' '.join(cmd)}\n{output}"}

    async def _wait_for_health(self, url: str) -> bool:
        for _ in range(30):
            try:
                async with httpx.AsyncClient(timeout=2) as client:
                    response = await client.get(url)
                    if response.status_code == 200:
                        return True
            except Exception:  # noqa: BLE001
                pass
            await asyncio.sleep(2)
        return False
