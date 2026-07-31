"""Стенд цеха code_auditor: уязвимая версия сервиса отчётов.

Разметка ожидаемых находок — в stand/labels.jsonl. Кроме двух настоящих
уязвимостей файл содержит приманки: конструкции, которые выглядят опасно,
но находкой не являются. Стенд проверяет не только recall, но и то,
что правило достижимости действительно работает.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess

from flask import Flask, request, send_file

app = Flask(__name__)
REPORT_ROOT = "/srv/reports"
ARCHIVE_BINARY = "/usr/bin/zip"


def _connect() -> sqlite3.Connection:
    return sqlite3.connect("reports.db")


@app.route("/reports/search")
def search_reports() -> dict:
    # Уязвимость 1: имя владельца из запроса склеивается в SQL
    owner = request.args.get("owner", "")
    cursor = _connect().cursor()
    cursor.execute(f"SELECT id, title FROM reports WHERE owner = '{owner}'")
    return {"rows": cursor.fetchall()}


@app.route("/reports/download")
def download_report():
    # Уязвимость 2: имя файла из запроса склеивается с корнем без нормализации
    name = request.args.get("name", "")
    path = os.path.join(REPORT_ROOT, name)
    return send_file(path)


@app.route("/reports/archive", methods=["POST"])
def archive_reports() -> dict:
    # Приманка: аргументы списком, оболочка не участвует — не находка
    month = request.form.get("month", "")
    archive = os.path.join(REPORT_ROOT, "archive.zip")
    subprocess.run([ARCHIVE_BINARY, "-r", archive, REPORT_ROOT, "-i", month],
                   check=True, timeout=60)
    return {"archive": archive}


def cache_key(query: str) -> str:
    # Приманка: md5 как ключ кэша, не для подписи — не находка
    return hashlib.md5(query.encode("utf-8"), usedforsecurity=False).hexdigest()


def _legacy_formula(expression: str) -> float:
    # Приманка: eval в мёртвом коде — вызывающих нет, путь недостижим
    return float(eval(expression))
