#!/usr/bin/env python3
"""
prepare_code_items - нарезка исходников в элементы map-прогона цеха code_auditor.

Элемент = один файл исходника + вывод внешних сканеров (FR-C2). Сканеры
гоняются через workshop/sandbox.py (M-10) в контейнере с `--network none`:
анализируемый код НЕ исполняется, разбирается статически (NFR-C1, NFR-C2).

ЕСЛИ образ или docker недоступны — элемент всё равно собирается, а в секции
scanners пишется причина. Молчаливого «сканеры чисты» быть не должно: цех
обязан превзойти baseline сканеров (AC-C4), и подмена их вывода пустотой
превратила бы сравнение в фикцию.

  python3 configs/code_auditor/tools/prepare_code_items.py \\
      --files 'configs/code_auditor/stand/vulnerable/*.py' \\
      --out projects/code_auditor/items
"""

from __future__ import annotations

import argparse
import glob as glob_module
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from workshop.result import Err  # noqa: E402
from workshop.sandbox import ExecLimits, run_in_docker  # noqa: E402

RULES_PATH = Path(__file__).resolve().parent / "semgrep_rules.yml"
DEFAULT_IMAGE = "workshop-audit:latest"

# bandit и semgrep возвращают ненулевой код при находках — это не сбой запуска.
# HOME=/tmp обязателен: песочница запускает контейнер под uid хоста, домашний
# каталог образа этому uid не принадлежит, и semgrep падает на создании
# своего каталога логов раньше, чем начнёт сканировать.
SCAN_COMMAND = (
    "bandit -q -f json -r target.py 2>/dev/null || true; "
    "echo '--- semgrep ---'; "
    "HOME=/tmp semgrep --metrics=off --quiet --json --config rules.yml target.py "
    "2>/dev/null || true"
)


def scan(source: str, image: str, timeout_s: int) -> str:
    """Вывод сканеров по одному файлу; при недоступности песочницы — причина."""
    if not RULES_PATH.is_file():
        return f"сканеры не запускались: нет набора правил {RULES_PATH.name}"
    report = run_in_docker(
        image,
        {"target.py": source, "rules.yml": RULES_PATH.read_text(encoding="utf-8")},
        SCAN_COMMAND,
        ExecLimits(timeout_s=timeout_s, mem_mb=2048),
    )
    if isinstance(report, Err):
        return f"сканеры не запускались: {report.code}: {report.details}"
    return _condense(report.value.stdout)


def _condense(raw: str) -> str:
    """Сжимает JSON сканеров до строк «инструмент правило файл:строка сообщение».

    Полный JSON semgrep на один файл — десятки килобайт служебных полей;
    в элемент идёт только то, что узел judge может сопоставить с гипотезой.
    """
    bandit_raw, _, semgrep_raw = raw.partition("--- semgrep ---")
    lines: list[str] = []

    try:
        for issue in json.loads(bandit_raw or "{}").get("results", []):
            lines.append(
                f"bandit {issue.get('test_id')} {issue.get('issue_severity')} "
                f"target.py:{issue.get('line_number')} {issue.get('issue_text')}"
            )
    except json.JSONDecodeError:
        lines.append("bandit: вывод не разобран как JSON")

    try:
        for issue in json.loads(semgrep_raw or "{}").get("results", []):
            start = issue.get("start", {}).get("line")
            message = issue.get("extra", {}).get("message", "")
            lines.append(f"semgrep {issue.get('check_id')} target.py:{start} {message}")
    except json.JSONDecodeError:
        lines.append("semgrep: вывод не разобран как JSON")

    return "\n".join(lines) if lines else "срабатываний нет"


def main() -> int:
    ap = argparse.ArgumentParser(description="Нарезка исходников в элементы code_auditor")
    ap.add_argument("--files", action="append", required=True,
                    help="glob исходников; можно повторять")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--image", default=DEFAULT_IMAGE)
    ap.add_argument("--timeout-s", type=int, default=300)
    ap.add_argument("--prefix", default="", help="префикс идентификатора элемента")
    args = ap.parse_args()

    paths = sorted({
        Path(p) for pattern in args.files
        for p in glob_module.glob(pattern) if Path(p).is_file()
    })
    if not paths:
        print(f"[ERROR] glob не нашёл файлов: {args.files}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for path in paths:
        source = path.read_text(encoding="utf-8")
        element = f"{args.prefix}{path.stem}"
        scanners = scan(source, args.image, args.timeout_s)
        item = (
            f"Аудируемый элемент: {element}\n"
            f"Файл: {path.as_posix()}\n\n"
            f"<source>\n{source}\n</source>\n\n"
            f"<scanners>\n{scanners}\n</scanners>\n"
        )
        (args.out / f"{element}.md").write_text(item, encoding="utf-8")
        first = scanners.splitlines()[0] if scanners else ""
        print(f"{element}: {len(scanners.splitlines())} строк вывода сканеров ({first})")

    print(f"элементов записано: {len(paths)} в {args.out}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
