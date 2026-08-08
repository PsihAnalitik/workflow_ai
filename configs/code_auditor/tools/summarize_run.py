#!/usr/bin/env python3
"""
summarize_run - сводка находок map-прогона цеха code_auditor.

Артефакт vuln_report на элемент читается плохо, когда элементов десятки:
скрипт сводит их в таблицу «вес → класс → локация» и отдельно показывает,
сколько гипотез узел judge понизил и по какому основанию. Доля понижений —
главный индикатор работы правила достижимости: если она близка к нулю,
опровергающий узел не работает и цех вырождается в поток гипотез.

  python3 summarize_run.py --project projects/code_auditor --prefix self_
"""

from __future__ import annotations

import argparse
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path

VERSION_RE = re.compile(r"^v(\d+)\.xml$")
GROUND_MEANING = {
    "A": "вход не внешний",
    "B": "путь разорван",
    "C": "строка недостижима",
    "D": "защита выше по стеку",
    "E": "опровергнуть не удалось",
}


def latest(node_dir: Path) -> Path | None:
    versions = [
        (int(m.group(1)), p)
        for p in node_dir.iterdir()
        if (m := VERSION_RE.match(p.name)) is not None
    ]
    return max(versions)[1] if versions else None


def main() -> int:
    ap = argparse.ArgumentParser(description="Сводка находок прогона code_auditor")
    ap.add_argument("--project", type=Path, required=True)
    ap.add_argument("--node", default="judge")
    ap.add_argument("--prefix", default="", help="брать только элементы с этим префиксом")
    args = ap.parse_args()

    map_dir = args.project / "map"
    if not map_dir.is_dir():
        print(f"[ERROR] нет каталога прогона: {map_dir}", file=sys.stderr)
        return 1

    weights: Counter = Counter()
    grounds: Counter = Counter()
    loud: list[tuple[str, str, str, str, str]] = []
    unparsed: list[str] = []
    elements = 0

    for item_dir in sorted(map_dir.iterdir()):
        if not item_dir.name.startswith(args.prefix):
            continue
        node_dir = item_dir / "artifacts" / args.node
        if not node_dir.is_dir():
            continue
        artifact = latest(node_dir)
        if artifact is None:
            continue
        elements += 1
        try:
            root = ET.parse(artifact).getroot()
        except ET.ParseError as exc:
            unparsed.append(f"{item_dir.name}: {exc}")
            continue
        for finding in root.iter("finding"):
            weight = (finding.get("weight") or "?").lower()
            weights[weight] += 1
            refutation = finding.find("refutation")
            ground = (refutation.get("ground") if refutation is not None else "?") or "?"
            grounds[ground] += 1
            if weight in ("p0", "p1"):
                loud.append((
                    weight, item_dir.name, finding.get("class") or "?",
                    finding.get("cwe") or "?", finding.get("locator") or "?",
                ))

    total = sum(weights.values())
    print(f"Элементов: {elements}, находок всего: {total}")
    print("\nПо весам (p0 — высший):")
    for weight in ("p0", "p1", "p2", "p3"):
        if weights[weight]:
            print(f"  {weight}: {weights[weight]}")
    print("\nПо основаниям опровержения:")
    for ground, count in sorted(grounds.items()):
        print(f"  {ground} ({GROUND_MEANING.get(ground, '?')}): {count}")
    if total:
        demoted = total - grounds.get("E", 0)
        print(f"\nПонижено опровержением: {demoted}/{total} ({100 * demoted / total:.0f}%)")

    print(f"\nБлокирующие находки (p0/p1): {len(loud)}")
    for weight, element, cls, cwe, locator in sorted(loud):
        print(f"  {weight} {element:28} {cls:5} {cwe:12} {locator}")

    if unparsed:
        print(f"\n[ERROR] непарсящихся отчётов: {len(unparsed)}", file=sys.stderr)
        for line in unparsed:
            print(f"  {line}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
