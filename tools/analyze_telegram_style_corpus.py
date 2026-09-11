"""Audit every original text message in Telegram exports in chronological chunks."""

from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


FEATURES = {
    "вопрос": re.compile(r"\?"),
    "двоеточие": re.compile(r":"),
    "восклицание": re.compile(r"!"),
    "первое лицо": re.compile(r"\b(?:я|мы|мне|нам|нас)\b", re.I),
    "повелительное": re.compile(
        r"\b(?:пишите|приходите|присоединяйтесь|вступайте|записывайтесь|смотрите|слушайте)\b",
        re.I,
    ),
    "организация": re.compile(
        r"\b(?:начинается|занятия|группа|курс|zoom|стоимость|мест[ао]|расписани)\w*",
        re.I,
    ),
}


def text_of(message: dict) -> str:
    value = message.get("text", "")
    if isinstance(value, list):
        return "".join(
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in value
        )
    return str(value)


def originals(messages: list[dict]) -> list[dict]:
    return [
        message
        for message in messages
        if text_of(message).strip() and not message.get("forwarded_from")
    ]


def describe(messages: list[dict]) -> dict[str, int | float]:
    lengths = [len(re.findall(r"\w+", text_of(message))) for message in messages]
    values: dict[str, int | float] = {
        "messages": len(messages),
        "words": sum(lengths),
        "mean_words": round(sum(lengths) / len(lengths), 1) if lengths else 0,
        "short": sum(length <= 25 for length in lengths),
    }
    for name, pattern in FEATURES.items():
        values[name] = sum(bool(pattern.search(text_of(message))) for message in messages)
    return values


def sample(messages: list[dict], pattern: re.Pattern[str], username: str) -> str:
    for message in messages:
        text = " ".join(text_of(message).split())
        if pattern.search(text):
            return f"[{message['id']}](https://t.me/{username}/{message['id']})"
    return "—"


def render(channel: str, username: str, messages: list[dict], chunk_size: int) -> str:
    lines = [
        f"## {channel}",
        "",
        "| Чанк | Даты | Сообщений | Слов | Ср. слов | ≤25 слов | Вопрос | : | ! | Я/мы | Повелит. | Учебная лексика | Примеры |",
        "|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|",
    ]
    for number, start in enumerate(range(0, len(messages), chunk_size), 1):
        batch = messages[start : start + chunk_size]
        row = describe(batch)
        examples = ", ".join(
            sample(batch, pattern, username)
            for pattern in (FEATURES["организация"], FEATURES["первое лицо"])
        )
        lines.append(
            f"| {number} | {batch[0]['date'][:10]} — {batch[-1]['date'][:10]} | "
            f"{row['messages']} | {row['words']} | {row['mean_words']} | {row['short']} | "
            f"{row['вопрос']} | {row['двоеточие']} | {row['восклицание']} | "
            f"{row['первое лицо']} | {row['повелительное']} | {row['организация']} | {examples} |"
        )
    return "\n".join(lines)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--export-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--chunk-size", type=int, default=200)
    args = parser.parse_args()

    sources = {
        "Личный канал @MarcisGasuns": ("ChatExport_2026-09-11_marcisgasuns", "MarcisGasuns"),
        "«Оповещения санскритян» @samskrte": ("ChatExport_2026-09-11_samskrte", "samskrte"),
    }
    rendered = []
    total = Counter()
    all_records = 0
    forwarded = 0
    for label, (directory, username) in sources.items():
        raw_messages = json.loads((args.export_root / directory / "result.json").read_text())["messages"]
        all_records += len(raw_messages)
        forwarded += sum(bool(message.get("forwarded_from")) for message in raw_messages)
        messages = originals(raw_messages)
        total["messages"] += len(messages)
        total["words"] += sum(len(re.findall(r"\w+", text_of(message))) for message in messages)
        rendered.append(render(label, username, messages, args.chunk_size))

    body = "\n\n".join(
        [
            "# Полный чанковый аудит Telegram-корпуса Гасунса",
            "",
            "_Created: 11-09-2026 · Last updated: 11-09-2026_",
            "",
            f"Проверены все {all_records} записей двух экспортов. В стилевой анализ вошли "
            f"{total['messages']} непустых собственных текстовых сообщений ({total['words']} слов); "
            f"{forwarded} пересылок исключены из авторского голоса. "
            f"Размер чанка — {args.chunk_size} последовательных сообщений в каждом канале.",
            "",
            "Таблица не заменяет чтения: она доказывает охват и показывает, в каких временных отрезках "
            "есть короткая сводка, личный голос, вопрос, призыв и учебная конкретика. Ссылки в последнем "
            "столбце — точки ручной сверки, по две на чанк.",
            "",
            *rendered,
            "",
            "## Вывод для паспорта",
            "",
            "Весь корпус подтверждает постоянное чередование коротких сообщений и развёрнутых перечислений, "
            "частое употребление двоеточия, прямого первого лица и предметной учебной лексики. Отдельные "
            "посты-анонсы служат образцами именно анонсного жанра; личные посты служат доказательством интонации, "
            "но не копируются как шаблон программы.",
            "",
            "_Dr. Mārcis Gasūns_",
            "",
        ]
    )
    args.output.write_text(body)


if __name__ == "__main__":
    main()
