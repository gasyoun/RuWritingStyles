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

\section{{Аудит методологической предвзятости}}
Результаты анализа беспристрастности Совета:
\begin{{itemize}}
    \item \textbf{{Оценка смещения:}} {bias_score}/10
    \item \textbf{{Тип смещения:}} {bias_type}
    \item \textbf{{Критика:}} {bias_critique}
\end{{itemize}}

\section{{Библиографический конкорданс}}
Ссылки на академические коллекции:
{concordance_items}

\section{{Научная обоснованность (Citations)}}
Результаты проверки цитирований:
\begin{{itemize}}
{citation_items}
\end{{itemize}}

\section{{Литература}}
Список литературы по ГОСТ Р 7.0.100--2018 (кириллица перед латиницей):
\begin{{enumerate}}
{gost_items}
\end{{enumerate}}

\end{{document}}
"""


def _latex_escape(text: str) -> str:
    for char in ("&", "%", "_", "#"):
        text = text.replace(char, "\\" + char)
    return text

def generate_latex_report(run_dir: Path, db_entry: dict[str, Any]) -> str:
    run_id = run_dir.name
    profile = db_entry.get("archetype", "Researcher")
    model = db_entry.get("model", "Gemini 2.0")
    duration = db_entry.get("duration_seconds") or 0.0

    # Compass
    compass = db_entry.get("compass", {})
    if not isinstance(compass, dict):
        compass = {}
    compass_items = "\n".join([f"    \\item \\textbf{{{{{k}}}}}: {(v or 0.0):.2f}" for k, v in compass.items()])

    # Bloom
    bloom = db_entry.get("bloom_stats", {})
    if not isinstance(bloom, dict):
        bloom = {}
    bloom_items = "\n".join([f"    \\item \\textbf{{{{{k}}}}}: {v or 0}" for k, v in bloom.items()])

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

    # Citations
    cite_stats = db_entry.get("citation_stats", {})
    citation_items = (
        f"    \\item \\textbf{{{{Всего цитат:}}}} {cite_stats.get('total', 0)}\n"
        f"    \\item \\textbf{{{{Верифицировано:}}}} {cite_stats.get('verified', 0)}\n"
        f"    \\item \\textbf{{{{Галлюцинаций:}}}} {cite_stats.get('hallucinations', 0)}"
    )

    # Bias
    bias_score = db_entry.get("bias_score", 0)
    bias_path = run_dir / "bias-audit.json"
    bias_type = "none"
    bias_critique = "No audit data."
    if bias_path.exists():
        bias_data = json.loads(bias_path.read_text(encoding="utf-8"))
        bias_type = bias_data.get("primary_bias_detected", "none")
        bias_critique = bias_data.get("methodological_critique", "N/A").replace("_", r"\_")

    # GOST reference list
    from .bibtex import matched_entries
    from .gost import format_gost

    repo_root = run_dir.parent.parent
    revised_path = run_dir / "revised.md"
    revised_text = (
        revised_path.read_text(encoding="utf-8") if revised_path.exists() else ""
    )
    try:
        gost_entries = matched_entries(repo_root, revised_text)
    except Exception:
        gost_entries = []
    gost_items = "\n".join(
        f"    \\item {_latex_escape(format_gost(e))}" for e in gost_entries
    ) or "    \\item Цитирований, сопоставленных с библиографией, нет."

    return LATEX_TEMPLATE.format(
        run_id=run_id,
        profile=profile,
        model=model,
        duration=duration,
        compass_items=compass_items,
        bloom_items=bloom_items,
        council_rows=council_rows,
        concordance_items=concordance_items,
        citation_items=citation_items,
        bias_score=bias_score,
        bias_type=bias_type,
        bias_critique=bias_critique,
        gost_items=gost_items
    )

def write_latex_report(run_dir: Path, db_entry: dict[str, Any]):
    latex_content = generate_latex_report(run_dir, db_entry)
    (run_dir / "report.tex").write_text(latex_content, encoding="utf-8")
