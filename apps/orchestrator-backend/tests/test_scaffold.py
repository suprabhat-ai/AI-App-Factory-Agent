from app.scaffold import parse_prompt_to_spec


def test_parse_prompt_enriches_quality_fields() -> None:
    spec = parse_prompt_to_spec("Create a multimodal workflow AI agent")

    assert "multimodal response planner" in spec["features"]
    assert "task orchestration workflows" in spec["features"]
    assert "objectives" in spec and len(spec["objectives"]) >= 3
    assert "guardrails" in spec and len(spec["guardrails"]) >= 3
    assert "secure-by-default" in spec["quality_bar"]
