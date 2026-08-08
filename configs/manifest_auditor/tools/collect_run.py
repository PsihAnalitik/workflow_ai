#!/usr/bin/env python3
"""
collect_run - сборка артефактов map-прогона в каталог, который читает измеритель.

Прогон цеха раскладывает артефакты по элементам:
`projects/<project>/map/<slug>/artifacts/<node>/vN.xml`. Измеритель ждёт
плоский каталог «файл на элемент». Скрипт берёт ПОСЛЕДНЮЮ версию артефакта
каждого элемента и копирует её под именем элемента.

Заодно проверяет то, что измеритель молча простит: непарсящийся XML и
несовпадение атрибута `element` с именем элемента — и то и другое означает
брак прогона, а не низкое качество детектора.

  python3 collect_run.py --project projects/manifest_auditor --node audit \\
      --out corpus/runs/shop_1
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

VERSION_RE = re.compile(r"^v(\d+)\.xml$")


def latest_artifact(node_dir: Path) -> Path | None:
    versions = [
        (int(m.group(1)), path)
        for path in node_dir.iterdir()
        if (m := VERSION_RE.match(path.name)) is not None
    ]
    if not versions:
        return None
    return max(versions)[1]


def main() -> int:
    ap = argparse.ArgumentParser(description="Сборка артефактов map-прогона для измерителя")
    ap.add_argument("--project", type=Path, required=True,
                    help="каталог прогона, например projects/manifest_auditor")
    ap.add_argument("--node", default="audit", help="узел-источник артефакта")
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--elements-from", type=Path, default=None,
                    help="labels.jsonl: собирать ТОЛЬКО размеченные элементы — "
                         "в каталоге прогона рядом лежат элементы других задач "
                         "(догфудинг), и их находки исказили бы метрики корпуса")
    args = ap.parse_args()

    wanted: set[str] | None = None
    if args.elements_from is not None:
        wanted = {
            json.loads(line)["id"]
            for line in args.elements_from.read_text(encoding="utf-8").splitlines()
            if line.strip() and not line.startswith("#")
        }

    map_dir = args.project / "map"
    if not map_dir.is_dir():
        print(f"[ERROR] нет каталога прогона: {map_dir}", file=sys.stderr)
        return 1

    args.out.mkdir(parents=True, exist_ok=True)
    for stale in args.out.glob("*.xml"):
        stale.unlink()

    collected, problems = 0, []
    for item_dir in sorted(map_dir.iterdir()):
        if wanted is not None and item_dir.name not in wanted:
            continue
        node_dir = item_dir / "artifacts" / args.node
        if not node_dir.is_dir():
            continue
        artifact = latest_artifact(node_dir)
        if artifact is None:
            problems.append(f"{item_dir.name}: артефактов узла {args.node} нет")
            continue

        target = args.out / f"{item_dir.name}.xml"
        shutil.copyfile(artifact, target)
        collected += 1

        try:
            root = ET.parse(target).getroot()
        except ET.ParseError as exc:
            problems.append(f"{item_dir.name}: артефакт не парсится как XML ({exc})")
            continue
        declared = root.get("element")
        if declared is not None and declared != item_dir.name:
            problems.append(
                f"{item_dir.name}: element=\"{declared}\" не совпадает с элементом"
            )

    print(f"собрано артефактов: {collected} в {args.out}")
    for problem in problems:
        print(f"[ERROR] {problem}", file=sys.stderr)
    if problems:
        # Непарсящийся артефакт измеритель пропускает молча — вместе со ВСЕМИ
        # находками элемента. Это брак прогона, а не низкое качество цеха,
        # и он обязан быть виден до подсчёта метрик.
        print(f"брак прогона: {len(problems)} элементов, метрики считать нельзя",
              file=sys.stderr)
        return 1
    return 0 if collected else 1


if __name__ == "__main__":
    raise SystemExit(main())
