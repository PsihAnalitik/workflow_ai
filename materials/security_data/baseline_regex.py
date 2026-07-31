#!/usr/bin/env python3
"""
baseline_regex - наивный детектор по ключевым словам.

Нужен как точка отсчёта (AC-C4 по аналогии): цех обязан быть лучше него,
иначе LLM в контуре не оправдана. Заодно проверяет, что трудные негативы
в корпусе действительно трудные - baseline должен на них спотыкаться.

  python3 baseline_regex.py --manifests corpus/manifests --out runs/regex_baseline
"""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from pathlib import Path

RULES = [
    ("imperative_in_description", r"\b(always|before answering|after every|you must|make sure to)\b"),
    ("role_override", r"\b(system prompt|do not apply|disregard|previous (instructions|restrictions)|maintenance mode|were advised)\b"),
    ("prompt_disclosure", r"\b(system prompt|verbatim|echo (the )?(names|descriptions))\b"),
    ("secrecy_request", r"\b(do not (mention|tell|surface)|without (telling|informing)|regardless of the actual)\b"),
    ("external_reference", r"https?://"),
    ("tool_shadowing", r"\b(preferred over|instead of|deprecated|call this tool first|must not be used)\b"),
    ("hidden_text", r"<!--|[\u200b-\u200f\u2060\ufeff]|(?<![A-Za-z0-9+/])[A-Za-z0-9+/]{32,}={0,2}(?![A-Za-z0-9+/])"),
]
COMPILED = [(cls, re.compile(rx, re.I)) for cls, rx in RULES]

SUSPICIOUS_PARAM = re.compile(r"\b(command|shell|exec|path|file|script|callback|webhook)\b", re.I)


def walk_texts(doc: dict):
    """Отдаёт пары (locator, text) по всем текстовым полям манифеста."""
    if isinstance(doc.get("instructions"), str):
        yield "instructions", doc["instructions"]
    for i, tool in enumerate(doc.get("tools", [])):
        if isinstance(tool.get("description"), str):
            yield f"tools[{i}].description", tool["description"]
        props = (tool.get("inputSchema") or {}).get("properties") or {}
        for pname, pdef in props.items():
            if isinstance(pdef, dict) and isinstance(pdef.get("description"), str):
                yield f"tools[{i}].inputSchema.properties.{pname}.description", pdef["description"]


def scan(path: Path) -> list[dict]:
    doc = json.loads(path.read_text(encoding="utf-8"))
    element = path.stem
    out, seen = [], set()

    for locator, text in walk_texts(doc):
        norm = unicodedata.normalize("NFKC", text)
        for cls, rx in COMPILED:
            target = text if cls == "hidden_text" else norm
            if rx.search(target) and (locator, cls) not in seen:
                seen.add((locator, cls))
                out.append({"element": element, "class": cls, "locator": locator,
                            "weight": "p1"})

    # грубая эвристика scope_escalation: подозрительное имя параметра
    for i, tool in enumerate(doc.get("tools", [])):
        props = (tool.get("inputSchema") or {}).get("properties") or {}
        for pname in props:
            if SUSPICIOUS_PARAM.search(pname):
                out.append({"element": element, "class": "scope_escalation",
                            "locator": f"tools[{i}].inputSchema.properties.{pname}",
                            "weight": "p1"})
                break

    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--manifests", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    args = ap.parse_args()

    args.out.mkdir(parents=True, exist_ok=True)
    findings = []
    for path in sorted(args.manifests.glob("*.json")):
        findings.extend(scan(path))

    target = args.out / "findings.jsonl"
    with target.open("w", encoding="utf-8") as fh:
        for f in findings:
            fh.write(json.dumps(f, ensure_ascii=False) + "\n")

    print(f"baseline: {len(findings)} находок по {len(list(args.manifests.glob('*.json')))} манифестам")
    print(f"записано: {target}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
