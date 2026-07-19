"""Significant syntax shift detection (Phase F)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from .io_utils import atomic_write_json, atomic_write_text

def create_syntax_bundle(*, repo_root: Path, run_dir: Path) -> dict[str, Any]:
    """Prepare a prompt for the Syntax Shift Assessor."""
    run_dir = run_dir.resolve()
    normalized_path = run_dir / "normalized.md"
    revised_path = run_dir / "revised.md"
    if not normalized_path.exists() or not revised_path.exists():
        return {}

    normalized_text = normalized_path.read_text(encoding="utf-8")
    revised_text = revised_path.read_text(encoding="utf-8")
    
    prompt_path = run_dir / "syntax.prompt.md"
    syntax_path = run_dir / "syntax.json"
    
    atomic_write_text(
        prompt_path,
        f"""# Syntax Shift Assessment Request

You are a RuWritingStyles `syntax_assessor`.

## Ваша задача
Проанализируйте изменения в синтаксисе между исходным (Normalized) и исправленным (Revised) текстом. 
Выделите ТОЛЬКО ЗНАЧИМЫЕ синтаксические сдвиги.

### Что считать значимым:
1. **Замена залога**: Из действительного в страдательный и наоборот (Active vs Passive).
2. **Инверсия**: Существенное изменение порядка слов, меняющее логический акцент или актуальное членение предложения.
3. **Парцелляция или объединение**: Дробление одного предложения на несколько или объединение нескольких в одно.
4. **Смена синтаксической роли**: Например, превращение придаточного предложения в причастный оборот.

## Исходный текст (Normalized)
```markdown
{normalized_text}
```

## Исправленный текст (Revised)
```markdown
{revised_text}
```

## Требуемый выход (JSON)
Верните список значимых сдвигов:

```json
{{
  "run_id": "{run_dir.name}",
  "shifts": [
    {{
      "type": "passive_to_active",
      "original_span": "Текст был написан Зализняком",
      "revised_span": "Зализняк написал текст",
      "comment": "Упрощение структуры, переход к прямому действию."
    }},
    {{
      "type": "inversion",
      "original_span": "В лесу родилась елочка",
      "revised_span": "Елочка родилась в лесу",
      "comment": "Смена логического ударения."
    }}
  ]
}}
```
"""
    )
    
    # Initialize syntax.json
    atomic_write_json(
        syntax_path,
        {
            "run_id": run_dir.name,
            "status": "prompt_ready",
            "prompt_path": str(prompt_path.relative_to(repo_root)),
            "shifts": []
        },
    )
    
    return {"prompt_path": str(prompt_path), "syntax_path": str(syntax_path)}
