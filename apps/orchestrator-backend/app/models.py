from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class JobState:
    job_id: str
    prompt: str
    app_slug: str
    status: str = "queued"
    created_at: str = field(default_factory=lambda: datetime.utcnow().isoformat())
    logs: list[str] = field(default_factory=list)
    result: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "job_id": self.job_id,
            "prompt": self.prompt,
            "app_slug": self.app_slug,
            "status": self.status,
            "created_at": self.created_at,
            "logs": self.logs,
            "result": self.result,
            "error": self.error,
        }
