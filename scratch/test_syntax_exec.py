from pathlib import Path
from ruwritingstyles.execution import execute_syntax_artifact
from ruwritingstyles.providers import MockProvider

# This should NOT fail
execute_syntax_artifact(
    repo_root=Path("."),
    syntax_path=Path("runs/test/syntax.json"),
    provider=MockProvider(),
    model="test-model"
)
print("Success!")
