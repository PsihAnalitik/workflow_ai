# Образ внешнего оракула цеха code_auditor (FR-C2).
# Сканеры запускаются через workshop/sandbox.py (M-10) с --network none:
# анализируемый код в контейнере НЕ исполняется, только разбирается статически.
FROM python:3.12-slim

RUN pip install --no-cache-dir \
    bandit==1.8.6 \
    semgrep==1.139.0 \
    pip-audit==2.9.0

WORKDIR /work
