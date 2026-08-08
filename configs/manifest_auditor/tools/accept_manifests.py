#!/usr/bin/env python3
"""
accept_manifests - приёмочная таблица аудированных манифестов (FR-A3).

Берёт артефакты прогона цеха, отбирает элементы с вердиктом READY и печатает
строки приёмочной таблицы CHANGELOG цеха-потребителя в формате M-13
(`| path | роль | sha256[:16] |`). Дальше расхождение хэша ловит штатный
`python -m workshop verify-acceptance <каталог>`: правка манифеста после
аудита обнаруживается чекером, а не дисциплиной.

Элементы с вердиктом NOT_READY в таблицу НЕ попадают и печатаются отдельным
списком: манифест, не прошедший аудит, не может быть принят молча.

  python3 accept_manifests.py --run corpus/runs/shop_2 \\
      --manifests corpus/manifests --changelog ../../projects/consumer/CHANGELOG.md
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

HEADER = ["| Файл | Роль | sha256[:16] |", "|---|---|---|"]


def verdict_of(report_path: Path) -> str:
    """READY / NOT_READY / UNPARSEABLE — вердикт узла audit по артефакту."""
    try:
        root = ET.parse(report_path).getroot()
    except ET.ParseError:
        return "UNPARSEABLE"
    text = (root.findtext("verdict") or "").strip().upper()
    return text if text in ("READY", "NOT_READY") else "UNPARSEABLE"


def main() -> int:
    ap = argparse.ArgumentParser(description="Приёмочная таблица аудированных манифестов")
    ap.add_argument("--run", type=Path, required=True,
                    help="каталог артефактов прогона (выход collect_run.py)")
    ap.add_argument("--manifests", type=Path, required=True,
                    help="каталог самих манифестов — источник sha256")
    ap.add_argument("--changelog", type=Path, default=None,
                    help="дописать запись в этот CHANGELOG вместо печати")
    ap.add_argument("--basis", default="прогон цеха manifest_auditor",
                    help="текст основания приёмки")
    args = ap.parse_args()

    if not args.run.is_dir():
        print(f"[ERROR] нет каталога прогона: {args.run}", file=sys.stderr)
        return 1

    accepted: list[str] = []
    rejected: list[str] = []
    for report in sorted(args.run.glob("*.xml")):
        element = report.stem
        manifest = args.manifests / f"{element}.json"
        if not manifest.is_file():
            print(f"[warn] нет манифеста для {element}", file=sys.stderr)
            continue
        verdict = verdict_of(report)
        if verdict != "READY":
            rejected.append(f"{element}: {verdict}")
            continue
        digest = hashlib.sha256(manifest.read_bytes()).hexdigest()[:16]
        accepted.append(f"| `{manifest.name}` | манифест | `{digest}` |")

    if not accepted:
        print("[ERROR] ни один элемент не принят — таблица пуста", file=sys.stderr)
        for line in rejected:
            print(f"  не принят {line}", file=sys.stderr)
        return 1

    entry = "\n".join([f"\n## Приёмка манифестов — {args.basis}\n", *HEADER, *accepted])
    if args.changelog is not None:
        with args.changelog.open("a", encoding="utf-8") as stream:
            stream.write(entry + "\n")
        print(f"дописано в {args.changelog}: принято {len(accepted)}")
    else:
        print(entry)

    if rejected:
        print(f"\nНЕ приняты ({len(rejected)}) — аудит не пройден:", file=sys.stderr)
        for line in rejected:
            print(f"  {line}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
