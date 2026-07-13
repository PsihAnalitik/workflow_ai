"""Инструмент цеха data-аналитик: собирает входной материал пайплайна из CSV и постановки.

Использование:
    python configs/data_analyst/make_input.py <dataset.csv> <task.txt> > input.xml

Профиль детерминирован и строится stdlib-средствами: содержимое датасета
в контекст LLM не сваливается целиком — только колонки, типы, пропуски и примеры.
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path

_SAMPLE_ROWS = 5
_TYPE_PROBE_ROWS = 200


def _infer_type(values: list[str]) -> str:
    non_empty = [value for value in values if value.strip()]
    if not non_empty:
        return "empty"
    if all(_is_int(value) for value in non_empty):
        return "int"
    if all(_is_float(value) for value in non_empty):
        return "float"
    return "str"


def _is_int(value: str) -> bool:
    try:
        int(value)
    except ValueError:
        return False
    return True


def _is_float(value: str) -> bool:
    try:
        float(value)
    except ValueError:
        return False
    return True


def build_input(csv_path: Path, task_path: Path) -> str:
    task_text = task_path.read_text(encoding="utf-8").strip()

    with csv_path.open(encoding="utf-8", newline="") as stream:
        reader = csv.reader(stream)
        header = next(reader)
        rows = list(reader)

    columns_of_values: dict[str, list[str]] = {name: [] for name in header}
    for row in rows[:_TYPE_PROBE_ROWS]:
        for name, value in zip(header, row):
            columns_of_values[name].append(value)

    column_lines: list[str] = []
    for name in header:
        values = columns_of_values[name]
        empty_count = sum(1 for value in values if not value.strip())
        column_lines.append(
            f'    <column name="{name}" type="{_infer_type(values)}" '
            f'empty="{empty_count}/{len(values)}"/>'
        )

    sample_lines = [
        "      " + ", ".join(f"{name}={value}" for name, value in zip(header, row))
        for row in rows[:_SAMPLE_ROWS]
    ]

    return "\n".join(
        [
            "<input>",
            "  <request>",
            f"    {task_text}",
            "  </request>",
            f'  <dataset_profile csv="{csv_path.name}" rows="{len(rows)}">',
            *column_lines,
            "    <sample>",
            *sample_lines,
            "    </sample>",
            "  </dataset_profile>",
            "</input>",
        ]
    )


if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("использование: make_input.py <dataset.csv> <task.txt>", file=sys.stderr)
        sys.exit(2)
    print(build_input(Path(sys.argv[1]), Path(sys.argv[2])))
