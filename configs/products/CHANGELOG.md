# CHANGELOG — спеки продуктов (FR-14)

## 2026-07-08 — приёмка спек продуктов, v1

**HITL-решение автора: ACCEPT** (правило приёмки распространено на configs/products —
решение автора, зафиксировано в постановке §2.2). Состав:

| Файл | Роль | sha256[:16] |
|---|---|---|
| `search_platform.json` | продукт search_platform: сервис text-search (порт 8000) | `e6e75f8e34f0496a` |

Основание приёмки: живая сборка и запуск продукта — `workshop assemble` →
`docker compose up` → `/normalize?wordform=котами` → `{"lemma":"кот"}` → `down`
(продукт в `projects/search_platform/product/`).

Правило изменений: правка или добавление спеки продукта = новая запись здесь
и повторная HITL-приёмка (методология FR-17/FR-14, `user_docs/task_statement.md` §2.2).
Проверка: `python -m workshop verify-acceptance configs/products`.
