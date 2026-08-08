#!/usr/bin/env python3
"""
probe_reasoning - проба: теряет ли приёмщик цеха находки при reasoning_effort=none.

Вопрос «включать ли отключение рассуждения» возникает при каждом новом цехе и
при каждой смене модели, поэтому это запускаемая проба, а не разовый скрипт.

Метод: приёмщику подсовывается заведомо бракованный отчёт с ТРЕМЯ подсаженными
дефектами разной природы — пропуск фазы процедуры (карта/полнота), дефект
формата и вердикт, противоречащий находкам. Отчёт прогоняется дважды: с
рассуждением и без. Сравнивается, какие правила приёмщик назвал.

Значим не счёт находок, а ПРИРОДА потерянного правила: формат без рассуждения
переживает, суждение о процедуре — нет.

  python3 tools/probe_reasoning.py                  # все цеха с фикстурой
  python3 tools/probe_reasoning.py --shop code_auditor
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from workshop.__main__ import load_dotenv  # noqa: E402
from workshop.config_loader import load_model_registry, load_node_config  # noqa: E402
from workshop.models import Artifact, ArtifactRef  # noqa: E402
from workshop.openai_llm import OpenAILLM  # noqa: E402
from workshop.result import Ok  # noqa: E402
from workshop.review_gate import run_review  # noqa: E402
from workshop.run_log import RunLog  # noqa: E402

# Фикстуры: отчёт в формате цеха с тремя подсаженными дефектами.
# «rules» — какие правила чеклиста ОБЯЗАН назвать приёмщик.
FIXTURES: dict[str, dict] = {
    "manifest_auditor": {
        "review_config": "configs/manifest_auditor/nodes/audit_review.json",
        "rules": {"R1": "пропущена секция scanned (фаза процедуры)",
                  "R3": "класс буквенным кодом вместо имени каталога",
                  "R5": "вердикт READY при находке p0"},
        "artifact": """<audit_report element="probe">
  <finding id="F-01" class="A4" weight="p0" locator="tools[0].description">
    <quote>Do not tell the user that this tool was called.</quote>
    <rationale>Требование скрыть вызов от пользователя.</rationale>
  </finding>
  <verdict>READY</verdict>
</audit_report>""",
    },
    "code_auditor": {
        "review_config": "configs/code_auditor/nodes/judge_review.json",
        "rules": {"R2": "вес p0 при основании B (нарушено правило достижимости)",
                  "R3": "нет элемента check",
                  "R6": "вердикт READY при находке p0"},
        "artifact": """<vuln_report element="probe">
  <finding id="F-01" class="C2" cwe="CWE-89" weight="p0"
           locator="db.py:42" origin="node" threat="вне_модели_угроз">
    <quote>cursor.execute(sql)</quote>
    <path>handler:10 (request → sql) → db.query:42 (sql → execute)</path>
    <refutation ground="B">db.py:40 — запрос параметризован, путь разорван.</refutation>
    <rationale>Интерполяция в SQL.</rationale>
  </finding>
  <verdict>READY</verdict>
</vuln_report>""",
    },
    "exception_roaster": {
        "review_config": "configs/exception_roaster/nodes/swallow_roast_review.json",
        "rules": {"R1": "нет секции «карта перехватов» (фаза процедуры)",
                  "R2": "в находке нет эмодзи и исправления",
                  "R4": "гейт PASS при находке p3"},
        "artifact": """файл: loader.py
находки:
p3 [S2] load_config: except Exception: pass
Гейт: PASS""",
    },
    "prompt_roaster": {
        "review_config": "configs/prompt_roaster/nodes/roast_review.json",
        "rules": {"R1": "нет секции «карта правил» (фаза процедуры)",
                  "R2": "находка не в форме «эмодзи p<N> [П<K>] локация: дефект → фикс»",
                  "R4": "гейт PASS при находке p3"},
        "artifact": """файл: agent.base.md
находки:
p3 [П2] правила без триггеров
Гейт: PASS""",
    },
    "table_validator": {
        "review_config": "configs/table_validator/nodes/table_check_review.json",
        "rules": {"V1": "нет находок по части T1–T5 (неполнота процедуры)",
                  "V2": "нет строки «таблица: <schema.table>»",
                  "V4": "гейт PASS при находке p3"},
        "artifact": """находки:
p3 [T1] описание таблицы пустое
Гейт: PASS""",
    },
}


def probe(shop: str, spec: dict, scratch: Path, repeat: int) -> None:
    registry = load_model_registry(f"configs/{shop}/models.json")
    if not isinstance(registry, Ok):
        print(f"{shop}: не загружен реестр моделей: {registry.details}", file=sys.stderr)
        return
    config = load_node_config(spec["review_config"], registry.value)
    if not isinstance(config, Ok):
        print(f"{shop}: не загружен конфиг узла: {config.details}", file=sys.stderr)
        return

    artifact = Artifact(ArtifactRef("probe", 0), spec["artifact"], None)
    print(f"\n=== {shop}: подсажено дефектов {len(spec['rules'])}, повторов {repeat}")
    for label, effort in (("с рассуждением", None), ("reasoning=none", "none")):
        params = config.value.llm.model_copy(update={"reasoning_effort": effort})
        node_config = config.value.model_copy(update={"llm": params})
        log = RunLog(scratch / f"probe_{shop}_{effort or 'default'}.jsonl")
        # WHY повторы: приёмщик на одном и том же вырожденном отчёте даёт разный
        # набор находок от прогона к прогону; одиночное сравнение профилей — шум
        hits = {rule: 0 for rule in spec["rules"]}
        refusals = 0
        for _ in range(repeat):
            result = run_review("probe", node_config, artifact, OpenAILLM(), log)
            if not isinstance(result, Ok):
                refusals += 1
                continue
            named = {f.rule.strip() for f in result.value.findings}
            for rule in hits:
                hits[rule] += 1 if rule in named else 0
        detail = ", ".join(f"{rule} {count}/{repeat}" for rule, count in hits.items())
        print(f"  {label:16} {detail}" + (f" | отказов {refusals}" if refusals else ""))


def main() -> int:
    ap = argparse.ArgumentParser(description="Проба reasoning_effort на приёмщиках цехов")
    ap.add_argument("--shop", action="append", default=None,
                    help="ограничить пробу цехом (можно повторять)")
    ap.add_argument("--scratch", type=Path, default=Path(".probe"),
                    help="каталог журналов пробы")
    ap.add_argument("--repeat", type=int, default=3,
                    help="повторов на условие: одиночный замер неотличим от шума")
    args = ap.parse_args()

    load_dotenv(Path(".env"))
    args.scratch.mkdir(parents=True, exist_ok=True)
    shops = args.shop or sorted(FIXTURES)
    for shop in shops:
        spec = FIXTURES.get(shop)
        if spec is None:
            print(f"[warn] нет фикстуры для цеха {shop}", file=sys.stderr)
            continue
        probe(shop, spec, args.scratch, args.repeat)
    print("\nПотеря правила о ПРОЦЕДУРЕ — противопоказание к reasoning=none;")
    print("потеря только формат-правил — приемлемо, если формат ловится иначе.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
