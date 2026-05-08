"""LaTeX report generator for RuWritingStyles (Phase H)."""

from __future__ import annotations
import json
from pathlib import Path
from typing import Any

LATEX_TEMPLATE = r"""
\documentclass{{article}}
\usepackage[utf8]{{inputenc}}
\usepackage[russian]{{babel}}
\usepackage{{geometry}}
\usepackage{{hyperref}}
\usepackage{{booktabs}}
\usepackage{{longtable}}

\title{{Филологический отчет RuWritingStyles}}
\author{{Агентская Лаборатория v2.1}}
\date{{\today}}

\begin{{document}}

\maketitle

\section{{Метаданные}}
\begin{{itemize}}
    \item \textbf{{ID запуска:}} {run_id}
    \item \textbf{{Профиль:}} {profile}
    \item \textbf{{Модель:}} {model}
    \item \textbf{{Длительность:}} {duration:.2f} сек.
\end{{itemize}}

\section{{Методологический Компас}}
Результаты анализа принадлежности к научным школам:
\begin{{itemize}}
{compass_items}
\end{{itemize}}

\section{{Когнитивная разметка (Bloom)}}
Распределение когнитивной нагрузки в решениях Совета:
\begin{{itemize}}
{bloom_items}
\end{{itemize}}

\section{{Результаты аудита (Совет)}}
\begin{{longtable}}{{@{{}}p{{0.2\textwidth}}p{{0.7\textwidth}}@{{}}}}
\toprule
\textbf{{ID находки}} & \textbf{{Решение и Обоснование}} \\
\midrule
{council_rows}
\bottomrule
\end{{longtable}}

\section{{Библиографический конкорданс}}
Ссылки на академические коллекции:
{concordance_items}

\end{{document}}
"""

def generate_latex_report(run_dir: Path, db_entry: dict[str, Any]) -> str:
    run_id = run_dir.name
    profile = db_entry.get("archetype", "Researcher")
    model = db_entry.get("model", "Gemini 2.0")
    duration = db_entry.get("duration_seconds", 0.0)

    # Compass
    compass = db_entry.get("profile", {})
    compass_items = "\n".join([f"    \\item \\textbf{{{k}}}: {v:.2f}" for k, v in compass.items()])

    # Bloom
    bloom = db_entry.get("bloom_stats", {})
    bloom_items = "\n".join([f"    \\item \\textbf{{{k}}}: {v}" for k, v in bloom.items()])

    # Council
    council_path = run_dir / "council.json"
    council_rows = ""
    if council_path.exists():
        council_doc = json.loads(council_path.read_text(encoding="utf-8"))
        for dec in council_doc.get("decisions", []):
            fid = dec.get("finding_id", "N/A")
            reason = dec.get("reason", "No reason provided.").replace("_", r"\_").replace("&", r"\&")
            council_rows += f"{fid} & {reason} \\\\ \\hline\n"

    # Concordance (mock/simple for now)
    concordance_items = "В данном запуске использованы ссылки на коллекции Зализняка и Тронского."

    return LATEX_TEMPLATE.format(
        run_id=run_id,
        profile=profile,
        model=model,
        duration=duration,
        compass_items=compass_items,
        bloom_items=bloom_items,
        council_rows=council_rows,
        concordance_items=concordance_items
    )

def write_latex_report(run_dir: Path, db_entry: dict[str, Any]):
    latex_content = generate_latex_report(run_dir, db_entry)
    (run_dir / "report.tex").write_text(latex_content, encoding="utf-8")
