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
import glob as glob_module
import json
import sys
from pathlib import Path

# Литеральные двойные скобки уронят сборку промпта (M-03, UNRESOLVED_PLACEHOLDER)
FORBIDDEN = "{" "{"

HEADER = """Аудируемый элемент: {element}
Вид артефакта: {kind}
Режим: {mode}
"""

MANIFEST_KIND = "манифест MCP-сервера (ответ tools/list)"


def render_item(element: str, manifest: str, baseline: str | None,
                kind: str = MANIFEST_KIND, tag: str = "manifest") -> str:
    parts = [HEADER.format(
        element=element,
        kind=kind,
        mode="diff — сравнение с ранее принятой версией" if baseline else "single",
    )]
    if baseline is not None:
        parts.append(
            "<baseline_manifest>\n" + baseline.strip() + "\n</baseline_manifest>\n"
        )
    parts.append(f"<{tag}>\n" + manifest.strip() + f"\n</{tag}>\n")
    return "\n".join(parts)


def prepare_from_files(patterns: list[str], out_dir: Path | None,
                       kind: str | None) -> int:
    """Элементы из произвольных файлов репозитория (TSK-2608, догфудинг).

    Идентификатор строится из пути, а не из имени: одноимённые файлы разных
    цехов (empty.stage.md в пяти конфигах) иначе слились бы в один элемент.
    Литеральные двойные скобки НЕ проверяются: у реальных промптов они
    законны, а развязку делает map-драйвер при нарезке (TSK-2307).
    """
    if out_dir is None:
        print("[ERROR] режим --files требует --out", file=sys.stderr)
        return 1
    paths = sorted({
        Path(p) for pattern in patterns
        for p in glob_module.glob(pattern) if Path(p).is_file()
    })
    if not paths:
        print(f"[ERROR] glob не нашёл файлов: {patterns}", file=sys.stderr)
        return 1

    out_dir.mkdir(parents=True, exist_ok=True)
    for path in paths:
        element = "__".join(path.with_suffix("").parts).removeprefix("configs__")
        # тег element, а не manifest: обёртка корпуса задаёт вид артефакта,
        # и метрики цеха измерены именно на ней — подменять её нельзя
        item = render_item(
            element, path.read_text(encoding="utf-8"), None,
            kind or f"файл репозитория {path.suffix}", tag="element",
        )
        (out_dir / f"{element}.md").write_text(item, encoding="utf-8")
    print(f"элементов записано: {len(paths)} в {out_dir}")
    return 0


def main() -> int:
    ap = argparse.ArgumentParser(description="Нарезка корпуса в элементы map-прогона")
    ap.add_argument("--corpus", type=Path, default=Path("corpus"))
    ap.add_argument("--out", type=Path, default=None,
                    help="каталог элементов (дефолт: <corpus>/items)")
    ap.add_argument("--files", action="append", default=None,
                    help="glob произвольных файлов вместо корпуса (можно повторять): "
                         "аудит реальных артефактов, а не размеченных фикстур")
    ap.add_argument("--kind", default=None,
                    help="вид артефакта для режима --files, например "
                         "«системный промпт узла цеха»")
    args = ap.parse_args()

    if args.files is not None:
        return prepare_from_files(args.files, args.out, args.kind)

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

        item = render_item(row["id"], manifest, baseline, MANIFEST_KIND)
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
