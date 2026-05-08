import sys
from pathlib import Path
import re

path = Path('src/ruwritingstyles/providers.py')
content = path.read_text(encoding='utf-8')

mock_provider_code = """class MockProvider(BaseProvider):
    \"\"\"Deterministic provider for local development and tests.\"\"\"

    name = "mock"

    def effective_model(self, provider_request: ProviderRequest) -> str:
        return provider_request.model or "mock"

    def generate_json(self, provider_request: ProviderRequest) -> dict[str, Any]:
        self._set_retry_telemetry(ProviderRetryTelemetry())
        task = provider_request.task
        metadata = provider_request.metadata
        if task == "review":
            return self._review(metadata)
        if task == "council":
            return self._council(metadata)
        if task == "revision":
            return self._revision(metadata)
        if task == "verification":
            return self._verification(metadata)
        if task == "assessment":
            return self._assessment(metadata)
        if task == "syntax_assessment":
            return self._syntax(metadata)
        raise ProviderError(f"mock provider does not support task {task!r}")

    def _review(self, metadata: dict[str, Any]) -> dict[str, Any]:
        style_id = str(metadata["style_id"])
        span_id = str(metadata.get("first_paragraph_span_id") or "p001")
        return {
            "style_id": style_id,
            "summary": f"Mock review completed for {style_id}.",
            "findings": [
                {
                    "id": "finding-001",
                    "style_id": style_id,
                    "span_id": span_id,
                    "severity": "note",
                    "type": "mock_observation",
                    "finding": "Mock provider placeholder finding for pipeline validation.",
                    "suggestion": "Replace the mock provider with a real provider to get substantive review findings.",
                    "confidence": 0.1,
                }
            ],
        }

    def _council(self, metadata: dict[str, Any]) -> dict[str, Any]:
        decisions = []
        replies = []
        finding_ids = metadata.get("finding_ids", [])
        if not finding_ids:
            finding_ids = ["finding-001"]
            
        for finding_id in finding_ids:
            replies.append({
                "reply_to": finding_id,
                "style_id": "mock-style",
                "bloom_level": "Analyze",
                "position": "agree",
                "comment": "Mock analysis of finding.",
            })
            decisions.append({
                "finding_id": finding_id,
                "bloom_level": "Evaluate",
                "status": "accepted",
                "primary_school": "ling_iesh",
                "influence": {"ling_iesh": 0.8, "ling_mss": 0.2},
                "reason": "Mock council keeps placeholder findings informational.",
            })
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "replies": replies,
            "decisions": decisions,
            "stylistic_commitments": [
                {"term": "Mock Term", "logic": "Keep it as is."}
            ],
        }

    def _revision(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "revised_document": str(metadata.get("normalized_text") or ""),
            "applied_changes": [],
            "unresolved": [
                {
                    "reason": "Mock provider copied the normalized document without substantive revision."
                }
            ],
        }

    def _verification(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "needs_human_review",
            "passed": ["artifacts_parse"],
            "warnings": [
                {
                    "message": "Mock provider cannot verify factual fidelity; run a real provider for substantive verification."
                }
            ],
        }

    def _assessment(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "status": "completed",
            "assessments": [
                {
                    "span_id": "p001",
                    "tag": "mock-tag",
                    "impact": "positive",
                    "passed": True,
                    "comment": "Mock assessment.",
                }
            ],
        }

    def _syntax(self, metadata: dict[str, Any]) -> dict[str, Any]:
        return {
            "run_id": str(metadata["run_id"]),
            "shifts": [
                {
                    "type": "passive_to_active",
                    "original_span": "The text was written by mock.",
                    "revised_span": "Mock wrote the text.",
                    "comment": "Mock syntax shift.",
                }
            ],
        }
"""

# Replace from 'class MockProvider' until 'class OpenAIProvider'
pattern = re.compile(r"class MockProvider\(BaseProvider\):.*?class OpenAIProvider", re.DOTALL)
new_content = pattern.sub(mock_provider_code + "\n\nclass OpenAIProvider", content)

path.write_text(new_content, encoding='utf-8')
print("MockProvider updated successfully")
