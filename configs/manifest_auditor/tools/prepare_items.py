#!/usr/bin/env python3
"""
prepare_items - нарезка корпуса в элементы map-прогона цеха manifest_auditor.

Элемент цеха = один файл `items/<element_id>.md`: шапка с идентификатором и
видом артефакта + сам манифест. Для элементов с `"mode": "diff"` в разметку
добавляется ранее принятая версия — diff-режим (FR-A2) не требует отдельного
графа, отличается только составом элемента.

Слаг map-прогона равен имени файла без расширения, поэтому `element` в
артефакте узла совпадает с `id` разметки — измеритель сверяет их напрямую.

  python3 prepare_items.py --corpus ../corpus --out ../corpus/items
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Литеральные двойные скобки уронят сборку промпта (M-03, UNRESOLVED_PLACEHOLDER)
FORBIDDEN = "{" "{"

HEADER = """Аудируемый элемент: {element}
Вид артефакта: манифест MCP-сервера (ответ tools/list)
Режим: {mode}
"""


def render_item(element: str, manifest: str, baseline: str | None) -> str:
    parts = [HEADER.format(
        element=element,
        mode="diff — сравнение с ранее принятой версией" if baseline else "single",
    )]
    if baseline is not None:
        parts.append(
            "<baseline_manifest>\n" + baseline.strip() + "\n</baseline_manifest>\n"
        )
    parts.append("<manifest>\n" + manifest.strip() + "\n</manifest>\n")
    return "\n".join(parts)


def main() -> int:
    ap = argparse.ArgumentParser(description="Нарезка корпуса в элементы map-прогона")
    ap.add_argument("--corpus", type=Path, default=Path("corpus"))
    ap.add_argument("--out", type=Path, default=None,
                    help="каталог элементов (дефолт: <corpus>/items)")
    args = ap.parse_args()

    labels_path = args.corpus / "labels.jsonl"
    out_dir = args.out if args.out is not None else args.corpus / "items"
    if not labels_path.is_file():
        print(f"[ERROR] нет разметки: {labels_path}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    written = 0
    for line in labels_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        manifest_path = args.corpus / row["file"]
        if not manifest_path.is_file():
            print(f"[ERROR] нет манифеста: {manifest_path}", file=sys.stderr)
            return 1
        manifest = manifest_path.read_text(encoding="utf-8")

        baseline = None
        if row.get("mode") == "diff":
            baseline_path = args.corpus / row["baseline"]
            if not baseline_path.is_file():
                print(f"[ERROR] нет базовой версии: {baseline_path}", file=sys.stderr)
                return 1
            baseline = baseline_path.read_text(encoding="utf-8")

        item = render_item(row["id"], manifest, baseline)
        if FORBIDDEN in item:
            print(f"[ERROR] {row['id']}: литеральные двойные скобки в элементе — "
                  f"сборка промпта упадёт", file=sys.stderr)
            return 1
        (out_dir / f"{row['id']}.md").write_text(item, encoding="utf-8")
        written += 1

    print(f"элементов записано: {written} в {out_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
