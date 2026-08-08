#!/usr/bin/env python3
"""
score_audit - измеритель качества цеха manifest_auditor.

Детерминированный. LLM в оценке не участвует (NFR-0.5): сверяет находки цеха
с эталонной разметкой корпуса и считает precision/recall/F1, устойчивость по
N прогонам и долю ложных тревог на негативах.

Вход находок:
  - каталог с XML-артефактами узла (по файлу на элемент), или
  - JSONL, по строке на находку.

Использование:
  python3 score_audit.py --labels corpus/labels.jsonl --run runs/run_1
  python3 score_audit.py --labels corpus/labels.jsonl --run runs/run_1 ... --run runs/run_5
  python3 score_audit.py --labels ... --run runs/shop --baseline runs/regex_baseline
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import sys
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from pathlib import Path

# Пороги из критериев приёмки ТЗ (§2.3)
AC_RECALL = 0.80
AC_PRECISION = 0.70
AC_SPREAD = 0.10
AC_SILENCE = 0.90
LOUD_WEIGHTS = {"p0", "p1"}


# --------------------------------------------------------------------------
# Модели
# --------------------------------------------------------------------------

@dataclass(frozen=True)
class Expected:
    element: str
    cls: str
    locator: str


@dataclass(frozen=True)
class Finding:
    element: str
    cls: str
    locator: str
    weight: str = "p2"


@dataclass
class RunResult:
    name: str
    tp: int = 0
    fp: int = 0
    fn: int = 0
    unlabeled: int = 0
    silent_negatives: int = 0
    total_negatives: int = 0
    per_class: dict = field(default_factory=dict)
    noisy_elements: list = field(default_factory=list)
    missed: list = field(default_factory=list)

    @property
    def precision(self) -> float:
        d = self.tp + self.fp
        return self.tp / d if d else 1.0

    @property
    def recall(self) -> float:
        d = self.tp + self.fn
        return self.tp / d if d else 1.0

    @property
    def f1(self) -> float:
        p, r = self.precision, self.recall
        return 2 * p * r / (p + r) if (p + r) else 0.0

    @property
    def silence(self) -> float:
        return self.silent_negatives / self.total_negatives if self.total_negatives else 1.0


# --------------------------------------------------------------------------
# Загрузка
# --------------------------------------------------------------------------

def load_labels(path: Path):
    elements, expected = {}, []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        elements[row["id"]] = row["kind"]
        for exp in row.get("expected", []):
            expected.append(Expected(row["id"], exp["class"], normalize(exp["locator"])))
    return elements, expected


def normalize(locator: str) -> str:
    """Приводит локатор к сравнимому виду: tools[0].description -> tools.0.description"""
    loc = (locator or "").strip().lower()
    loc = re.sub(r"\[(\d+)\]", r".\1", loc)
    loc = re.sub(r"[/\\]", ".", loc)
    return re.sub(r"\.+", ".", loc).strip(".")


def load_findings(path: Path) -> list[Finding]:
    if path.is_file():
        return _load_jsonl(path)
    if not path.is_dir():
        raise SystemExit(f"[ERROR] не найдено: {path}")

    out: list[Finding] = []
    for xml_file in sorted(path.glob("*.xml")):
        out.extend(_load_xml(xml_file))
    for jsonl in sorted(path.glob("*.jsonl")):
        out.extend(_load_jsonl(jsonl))
    return out


def _load_jsonl(path: Path) -> list[Finding]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        row = json.loads(line)
        out.append(Finding(
            element=row["element"],
            cls=row["class"],
            locator=normalize(row.get("locator", "")),
            weight=str(row.get("weight", "p2")).lower(),
        ))
    return out


def _load_xml(path: Path) -> list[Finding]:
    """Артефакт узла: <audit_report element="..."><finding class= weight= locator=/>"""
    try:
        root = ET.parse(path).getroot()
    except ET.ParseError as exc:
        sys.stderr.write(f"[warn] {path.name}: не разобран как XML ({exc})\n")
        return []

    element = root.get("element") or root.get("id") or path.stem
    out = []
    for node in root.iter("finding"):
        cls = node.get("class") or node.findtext("class") or ""
        if not cls:
            continue
        out.append(Finding(
            element=element,
            cls=cls.strip().lower(),
            locator=normalize(node.get("locator") or node.findtext("locator") or ""),
            weight=(node.get("weight") or node.findtext("weight") or "p2").strip().lower(),
        ))
    return out


# --------------------------------------------------------------------------
# Сопоставление
# --------------------------------------------------------------------------

def locators_match(a: str, b: str) -> bool:
    """Совпадение по границе сегмента: tools.0 матчится с tools.0.description."""
    if not a or not b:
        return True  # локатор не указан ни у одной стороны - не штрафуем
    if a == b:
        return True
    lo, hi = sorted((a, b), key=len)
    return hi.startswith(lo + ".")


def score_run(name: str, findings: list[Finding], elements: dict,
              expected: list[Expected], lenient: bool) -> RunResult:
    res = RunResult(name=name)

    unknown = {f.element for f in findings} - set(elements)
    if unknown:
        sys.stderr.write(f"[warn] {name}: находки для неизвестных элементов: "
                         f"{sorted(unknown)[:5]}\n")

    remaining = list(expected)
    matched_findings = set()

    for idx, f in enumerate(findings):
        for exp in remaining:
            if exp.element == f.element and exp.cls == f.cls and locators_match(exp.locator, f.locator):
                remaining.remove(exp)
                matched_findings.add(idx)
                res.tp += 1
                res.per_class.setdefault(exp.cls, {"tp": 0, "fp": 0, "fn": 0})["tp"] += 1
                break

    for idx, f in enumerate(findings):
        if idx in matched_findings:
            continue
        kind = elements.get(f.element)
        bucket = res.per_class.setdefault(f.cls, {"tp": 0, "fp": 0, "fn": 0})
        if kind == "positive":
            res.unlabeled += 1
            if not lenient:
                res.fp += 1
                bucket["fp"] += 1
        else:
            res.fp += 1
            bucket["fp"] += 1

    for exp in remaining:
        res.fn += 1
        res.per_class.setdefault(exp.cls, {"tp": 0, "fp": 0, "fn": 0})["fn"] += 1
        res.missed.append(f"{exp.element}:{exp.cls}")

    negatives = [e for e, k in elements.items() if k in ("negative", "hard_negative")]
    res.total_negatives = len(negatives)
    loud = {f.element for f in findings if f.weight in LOUD_WEIGHTS}
    for e in negatives:
        if e in loud:
            res.noisy_elements.append(e)
        else:
            res.silent_negatives += 1

    return res


# --------------------------------------------------------------------------
# Отчёт
# --------------------------------------------------------------------------

def mark(ok: bool) -> str:
    return "OK  " if ok else "FAIL"


def report(runs: list[RunResult], elements: dict, expected_ref: list,
           baseline: RunResult | None, verbose: bool) -> bool:
    print("=" * 72)
    print("МЕТРИКИ ЦЕХА manifest_auditor")
    print("=" * 72)

    kinds = {}
    for k in elements.values():
        kinds[k] = kinds.get(k, 0) + 1
    print(f"Корпус: {len(elements)} элементов  {kinds}")
    print(f"Прогонов: {len(runs)}\n")

    print(f"{'прогон':<14}{'precision':>11}{'recall':>9}{'F1':>8}"
          f"{'тишина':>10}{'TP':>5}{'FP':>5}{'FN':>5}")
    print("-" * 72)
    for r in runs:
        print(f"{r.name:<14}{r.precision:>11.3f}{r.recall:>9.3f}{r.f1:>8.3f}"
              f"{r.silence:>10.3f}{r.tp:>5}{r.fp:>5}{r.fn:>5}")

    recalls = [r.recall for r in runs]
    precisions = [r.precision for r in runs]
    silences = [r.silence for r in runs]
    spread = max(recalls) - min(recalls) if len(runs) > 1 else 0.0
    mean_r = statistics.fmean(recalls)
    mean_p = statistics.fmean(precisions)
    mean_s = statistics.fmean(silences)

    n_expected = sum(1 for _ in expected_ref)
    sigma = (mean_r * (1 - mean_r) / n_expected) ** 0.5 if n_expected else 0.0
    stdev = statistics.pstdev(recalls) if len(runs) > 1 else 0.0

    if len(runs) > 1:
        print("-" * 72)
        print(f"{'среднее':<14}{mean_p:>11.3f}{mean_r:>9.3f}"
              f"{'':>8}{mean_s:>10.3f}")
        print(f"\nразброс recall (размах): {spread:.3f}   ст.откл.: {stdev:.3f}")
        print(f"шумовой порог при {n_expected} находках: sigma = {sigma:.3f}, "
              f"ожидаемый размах на {len(runs)} прогонах ~ {2.3 * sigma:.3f}")
        if stdev <= 1.5 * sigma:
            print("  разброс в пределах шума выборки - это НЕ нестабильность цеха;")
            print("  чтобы ужесточить порог, нужен корпус большего размера")
        else:
            print("  разброс превышает шум выборки - цех действительно нестабилен")

    print("\nКРИТЕРИИ ПРИЁМКИ")
    print("-" * 72)
    checks = [
        (f"AC-A2 precision >= {AC_PRECISION:.2f}", mean_p >= AC_PRECISION, f"{mean_p:.3f}"),
        (f"AC-A2 recall    >= {AC_RECALL:.2f}", mean_r >= AC_RECALL, f"{mean_r:.3f}"),
        (f"AC-A4 тишина    >= {AC_SILENCE:.2f}", mean_s >= AC_SILENCE, f"{mean_s:.3f}"),
    ]
    if len(runs) > 1:
        noise_limit = max(AC_SPREAD / 2, 1.5 * sigma)
        checks.append((f"AC-A3 ст.откл. <= {noise_limit:.3f} (шум)",
                       stdev <= noise_limit, f"{stdev:.3f}"))
    else:
        checks.append(("AC-A3 стабильность", None, "нужно >= 2 прогонов"))

    for label, ok, value in checks:
        status = "SKIP" if ok is None else mark(ok)
        print(f"  [{status}] {label:<32} факт: {value}")

    print("\nПО КЛАССАМ (первый прогон)")
    print("-" * 72)
    print(f"{'класс':<28}{'TP':>5}{'FP':>5}{'FN':>5}{'precision':>11}{'recall':>9}")
    for cls, c in sorted(runs[0].per_class.items()):
        pd, rd = c["tp"] + c["fp"], c["tp"] + c["fn"]
        pr = c["tp"] / pd if pd else float("nan")
        rc = c["tp"] / rd if rd else float("nan")
        print(f"{cls:<28}{c['tp']:>5}{c['fp']:>5}{c['fn']:>5}{pr:>11.3f}{rc:>9.3f}")

    r0 = runs[0]
    if r0.unlabeled:
        print(f"\nНеразмеченных находок на позитивах: {r0.unlabeled}")
        print("  Проверь вручную: это либо ложные срабатывания, либо реальные")
        print("  находки, которых нет в разметке - тогда дополни labels.jsonl.")

    if r0.noisy_elements:
        print(f"\nШумные негативы (есть p0/p1): {len(r0.noisy_elements)}")
        for e in r0.noisy_elements[:10]:
            tag = " <- трудный" if elements.get(e) == "hard_negative" else ""
            print(f"  {e}{tag}")

    if verbose and r0.missed:
        print(f"\nПропущено ({len(r0.missed)}):")
        for m in r0.missed[:20]:
            print(f"  {m}")

    if baseline:
        print("\nСРАВНЕНИЕ С BASELINE (AC-C4 по аналогии)")
        print("-" * 72)
        print(f"{'':<14}{'precision':>11}{'recall':>9}{'F1':>8}")
        print(f"{'baseline':<14}{baseline.precision:>11.3f}"
              f"{baseline.recall:>9.3f}{baseline.f1:>8.3f}")
        print(f"{'цех':<14}{mean_p:>11.3f}{mean_r:>9.3f}{runs[0].f1:>8.3f}")
        better = mean_r > baseline.recall and mean_p >= baseline.precision
        print(f"  [{mark(better)}] цех превосходит baseline")
        checks.append(("baseline", better, ""))

    return all(ok for _, ok, _ in checks if ok is not None)


def main() -> int:
    ap = argparse.ArgumentParser(description="Измеритель качества manifest_auditor")
    ap.add_argument("--labels", type=Path, required=True)
    ap.add_argument("--run", type=Path, action="append", required=True,
                    help="каталог с XML-артефактами или JSONL (можно несколько раз)")
    ap.add_argument("--baseline", type=Path, help="прогон эталонного детектора для сравнения")
    ap.add_argument("--lenient-positives", action="store_true",
                    help="не считать неразмеченные находки на позитивах ложными")
    ap.add_argument("--json-out", type=Path)
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args()

    elements, expected = load_labels(args.labels)
    if not expected:
        raise SystemExit("[ERROR] в разметке нет ожидаемых находок")

    runs = []
    for path in args.run:
        findings = load_findings(path)
        runs.append(score_run(path.name, findings, elements, expected,
                              args.lenient_positives))

    baseline = None
    if args.baseline:
        baseline = score_run("baseline", load_findings(args.baseline),
                             elements, expected, args.lenient_positives)

    passed = report(runs, elements, expected, baseline, args.verbose)

    if args.json_out:
        args.json_out.write_text(json.dumps({
            "corpus_size": len(elements),
            "expected_findings": len(expected),
            "runs": [{"name": r.name, "precision": round(r.precision, 4),
                      "recall": round(r.recall, 4), "f1": round(r.f1, 4),
                      "silence": round(r.silence, 4), "tp": r.tp, "fp": r.fp,
                      "fn": r.fn, "unlabeled": r.unlabeled} for r in runs],
            "passed": passed,
        }, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n" + ("ИТОГ: критерии приёмки выполнены"
                  if passed else "ИТОГ: критерии приёмки НЕ выполнены"))
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
