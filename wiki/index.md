# wiki: карта областей знаний (v1)

Верхний уровень — области знаний; в каждой директории обязателен `index.md`
(точка входа и каталог области). Формат — Markdown + Mermaid (FR-18, решение
автора §10 №11–12). Литеральные двойные фигурные скобки запрещены — ломают
сборку промпта. Проверка целостности: `python -m workshop wiki-check`.

| Область | kind | Что внутри |
|---|---|---|
| [agents](agents/index.md) | knowledge | построение агентов: промпты, прожарка, примеры |
| [python](python/index.md) | tech | каталог технологий экосистемы Python (FR-19) |
| [methodology](methodology/index.md) | knowledge | артефактная цепочка GRACE + примеры стадий |
| [domains](domains/index.md) | knowledge | предметные области (заготовка) |
| [assets](assets/index.md) | assets | изображения для HTML-витрины (FR-20) |

Области с `kind: tech` участвуют в выборе стека: их `index.md` — реестр
доступных технологий, из которого стадия `tech_selection` собирает `tech_stack.xml`.
